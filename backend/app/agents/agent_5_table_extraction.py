import logging
import re
import json
import os
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.schemas.financial import FinancialRawSchema

from app.core.config import settings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

_PL_SIGNALS = [
    (3, r'revenue\s+from\s+op(?:eration)?s?'),
    (3, r'income\s+from\s+op(?:eration)?s?'),
    (3, r'net\s+(?:sales|turnover)'),
    (3, r'net\s+pr\w{2,4}it\s+(?:for|after)'),
    (3, r'pr\w{2,4}it\s+after\s+tax'),
    (2, r'quarter(?:\s+ended)?'),
    (2, r'year(?:\s+ended)?'),
    (2, r'total\s+income'),
    (2, r'total\s+revenue'),
    (2, r'pr\w{2,4}it\s+before\s+(?:tax|exceptional)'),
    (1, r'exceptional\s+items'),
    (1, r'earnings\s+per\s+(?:equity\s+)?share'),
    (1, r'basic\s*(?:[(<])'),
    (1, r'particulars'),
]

_BS_SIGNALS = [
    (3, r'statement\s+of\s+assets\s+and\s+liabilities'),
    (3, r'balance\s+sheet'),
    (2, r'non-current\s+assets'),
    (2, r'equity\s+and\s+liabilities'),
    (1, r'capital\s+work-in-progress'),
    (1, r'trade\s+receivables'),
]

_CF_SIGNALS = [
    (3, r'statement\s+of\s+(?:standalone\s+)?cash\s+flows'),
    (3, r'cash\s+flow\s+statement'),
    (2, r'cash\s+flow\s+from\s+operating\s+activities'),
    (2, r'operating\s+profit\s+before\s+working\s+capital'),
    (1, r'net\s+cash\s+(?:flow\s+)?(?:from|used\s+in)\s+investing'),
    (1, r'net\s+cash\s+(?:flow\s+)?(?:from|used\s+in)\s+financing'),
]

def find_best_page(extracted_text: dict, signals: list) -> int:
    best_page, best_score = -1, -999
    for i, text in extracted_text.items():
        t = text.lower()
        score = sum(w for w, pat in signals if re.search(pat, t))
        
        if 'independent auditor' in t or 'we have audited' in t or 'in our opinion' in t:
            score -= 20
        if 'notes to the' in t and 'statement of' not in t:
            score -= 10

        num_count = len(re.findall(r'\d+', t))
        if num_count > 50:
            score += 2
            
        if score > best_score:
            best_score, best_page = score, int(i)
    return best_page

def sanitize_json_string(raw_json: str) -> str:
    """Sanitizes raw JSON string produced by LLM before parsing to fix common JSON formatting issues like commas in numbers."""
    def fix_unquoted_commas(match):
        prefix = match.group(1)
        num_str = match.group(2).replace(',', '')
        return f"{prefix}{num_str}"
    
    cleaned = re.sub(r'(:\s*)(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?)', fix_unquoted_commas, raw_json)
    cleaned = re.sub(r'(:\s*)\(([0-9,.]+)\)', r'\1-\2', cleaned)
    
    def fix_quoted_commas(match):
        prefix = match.group(1)
        num_str = match.group(2).replace(',', '')
        return f"{prefix}{num_str}"
        
    cleaned = re.sub(r'(:\s*)"(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?)"', fix_quoted_commas, cleaned)
    return cleaned

def process_tables(document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record:
        return
    try:
        doc_record.processing_status = ProcessingStatus.TABLE_EXTRACTION
        db.commit()

        extracted_text = doc_record.extracted_text or {}
        
        # 1. Identify Target Pages
        pl_page = find_best_page(extracted_text, _PL_SIGNALS)
        bs_page = find_best_page(extracted_text, _BS_SIGNALS)
        cf_page = find_best_page(extracted_text, _CF_SIGNALS)

        # Build a unique set of pages including a 2-page padding window
        target_pages = set()
        for p in [pl_page, bs_page, cf_page]:
            if p != -1:
                target_pages.add(p)
                target_pages.add(p + 1)
                target_pages.add(p + 2)
                if p > 0:
                    target_pages.add(p - 1)

        # Slice the text array & cap at 12,000 chars to fit within TPM limits
        compiled_text = ""
        for p in sorted(list(target_pages)):
            if str(p) in extracted_text:
                compiled_text += f"\n--- PAGE {p} ---\n{extracted_text[str(p)]}\n"
        
        compiled_text = compiled_text[:8000]

        if not compiled_text.strip():
            raise ValueError("No financial data could be extracted; targeted context is empty.")

        # 2. Invoke LLM Engine
        logger.info("[Agent5] Invoking Groq JSON mode for table extraction...")
        llm = ChatGroq(
            model=settings.GROQ_MODEL, 
            temperature=0.0,
            model_kwargs={"response_format": {"type": "json_object"}}
        )

        schema_keys = {
            name: field.description or "financial metric"
            for name, field in FinancialRawSchema.model_fields.items()
        }
        schema_keys_json = json.dumps(schema_keys, indent=2)

        system_prompt = (
            "Your sole mission is to act as a linguistic translator mapping unstructured textual grids into a structured financial JSON object.\n"
            "Extract all financial metrics into a single valid JSON object using the following allowed key definitions:\n\n"
            "{schema_keys}\n\n"
            "STRICT NUMERICAL & EXTRACTION RULES:\n"
            "1. Output all financial amounts as raw numbers (floats/ints) without thousands separators/commas (e.g., convert 2,133.55 to 2133.55).\n"
            "2. If a number is enclosed in brackets or parentheses like (100.50) or (1,234.50), extract it natively as a negative float (-100.50 or -1234.50).\n"
            "3. DO NOT perform any math scaling, currency normalizations, or multi-period conversions yourself.\n"
            "4. Identify and populate the 'reported_currency_unit' field verbatim from the page headers (e.g. Lakhs, Crores, Millions).\n"
            "5. COLUMN MAPPING RULE (CRITICAL):\n"
            "   - Column 0 (1st numeric column) = Current Quarter -> maps to _q_current fields (e.g. basic_eps_q = 3.54)\n"
            "   - Column 1 (2nd numeric column) = Previous Quarter -> maps to _q_prev fields (e.g. basic_eps_q_prev = 3.33)\n"
            "   - Column 2 (3rd numeric column) = Year-Ago Quarter -> maps to _q_year_ago fields (e.g. basic_eps_q_year_ago = 1.93)\n"
            "   - Column 3 (4th numeric column IF present) = Full Year / Annual total -> maps to _fy_current fields (e.g. 10.40 is Full Year, NOT Year-Ago Quarter! NEVER map Column 3 into _q_year_ago!)\n"
            "6. TOTAL INCOME MAPPING RULE (CRITICAL):\n"
            "   - `revenue_q_current` = 'Revenue from operations' line ONLY (line 1 in SEBI format).\n"
            "   - `total_income_q_current` = 'Total income' line ONLY = Revenue from Operations + Other Income (line 3 in SEBI format).\n"
            "   - NEVER map 'Total comprehensive income for the period' into `total_income_q_current`. That is a DIFFERENT line below PAT.\n"
            "7. PAT EXTRACTION RULE (CRITICAL):\n"
            "   - `pat_q_current` = 'Profit/(loss) for the period/year' or 'Profit after tax' line ONLY (e.g. line 9 in SEBI format).\n"
            "   - NEVER map 'Total comprehensive income for the period/year' into `pat_q_current`. TCI appears AFTER PAT and is always larger.\n"
            "   - NEVER map 'Profit before tax' (PBT) into `pat_q_current`. PBT is always LARGER than PAT.\n"
            "8. EXPENSE EXTRACTION:\n"
            "   - Extract 'Finance costs' / Interest into `finance_costs_q_current`.\n"
            "   - Extract 'Depreciation and amortisation expense' into `depreciation_q_current`.\n"
            "9. EPS EXTRACTION RULE:\n"
            "   - `basic_eps_q` MUST ONLY come from the row explicitly labelled 'Earnings per equity share' -> 'Basic' at the VERY BOTTOM of the table (typically a small number like 0.55, 4.22, 11.34).\n"
            "   - NEVER use any large operational number (like 2531.38 or 33124) for EPS. EPS is always a small per-share figure.\n"
            "10. If a metric is missing, absent, or represented as '-' or 'N/A', set it to null."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Extract the financial profile from the following pages and output a single valid JSON object:\n\n{text}")
        ])

        chain = prompt | llm

        try:
            raw_response = chain.invoke({"schema_keys": schema_keys_json, "text": compiled_text})
            raw_text = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
            
            sanitized_text = sanitize_json_string(raw_text)
            parsed_json = json.loads(sanitized_text)
            result = FinancialRawSchema.model_validate(parsed_json)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                logger.error("[Agent5] Groq API Rate Limit Hit (429). Failing gracefully.")
                raise ValueError("Groq API Limit Exhausted. Try again after some time")
            else:
                logger.error(f"[Agent5] Table extraction failed: {e}")
                raise e

        # 3. Serialize and Save
        financial_data = result.model_dump()
        financial_data["source_page_indices"] = list(target_pages)
        
        logger.info(f"[Agent5] Final extracted: {financial_data}")
        doc_record.financial_data = financial_data
        db.commit()
        logger.info(f"Agent 5 (Table Extraction) completed for {document_id}")

    except Exception as e:
        logger.error(f"[Agent5] Error: {e}", exc_info=True)
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = f"Agent 5 Error: {str(e)}"
        db.commit()
    finally:
        db.close()