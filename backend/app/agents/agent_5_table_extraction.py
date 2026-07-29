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

_REG52_SIGNALS = [
    (3, r'regulation\s+52\s*\(\s*4\s*\)'),
    (3, r'additional\s+disclosures\s+as\s+per\s+regulation'),
    (2, r'debt\s+equity\s+ratio'),
    (2, r'current\s+ratio'),
    (2, r'debtors\s+turnover'),
    (1, r'operating\s+margin\s+\(in\s+%\)'),
    (1, r'net\s+profit\s+margin\s+\(in\s+%\)'),
]

_PL_KEYS = [
    "reported_currency_unit", "period_q_current_label", "period_q_prev_label", 
    "period_q_year_ago_label", "period_fy_prev_label", "revenue_q_current", 
    "total_income_q_current", "profit_before_exceptional_q_current", 
    "profit_before_tax_q_current", "pat_q_current", "other_income_q_current", 
    "total_expenses_q_current", "tax_expense_q_current", "finance_costs_q_current", 
    "depreciation_q_current", "basic_eps_q", "revenue_q_prev", 
    "total_income_q_prev", "profit_before_exceptional_q_prev", 
    "profit_before_tax_q_prev", "pat_q_prev", "basic_eps_q_prev", 
    "revenue_q_year_ago", "total_income_q_year_ago", "pat_q_year_ago", 
    "basic_eps_q_year_ago", "revenue_fy_current", "total_income_fy_current", 
    "profit_before_exceptional_fy_current", "profit_before_tax_fy_current", 
    "pat_fy_current", "revenue_fy_prev", "total_income_fy_prev", 
    "profit_before_exceptional_fy_prev", "profit_before_tax_fy_prev", "pat_fy_prev",
    "paid_up_equity_capital"
]

_BS_REG_KEYS = [
    "reported_currency_unit", "reported_current_ratio", "reported_debt_equity", "reported_net_worth", 
    "reported_total_debt", "reported_operating_margin", "reported_net_margin", 
    "non_current_borrowings", "current_borrowings", "cash_equivalents", 
    "bank_balances", "cwip", "trade_receivables", "inventories", 
    "total_current_assets", "total_current_liabilities", 
    "non_current_borrowings_prev", "current_borrowings_prev", "cash_equivalents_prev", 
    "bank_balances_prev", "cwip_prev", "trade_receivables_prev", 
    "inventories_prev", "total_current_assets_prev", "total_current_liabilities_prev"
]

_CF_KEYS = [
    "reported_currency_unit", "operating_cash_flow", "operating_profit_pre_wc", "investing_cash_flow", 
    "capex", "financing_cash_flow", "proceeds_borrowings", "repayment_borrowings", 
    "operating_cash_flow_prev", "operating_profit_pre_wc_prev", 
    "investing_cash_flow_prev", "capex_prev", "financing_cash_flow_prev", 
    "proceeds_borrowings_prev", "repayment_borrowings_prev"
]

def find_best_page(extracted_text: dict, signals: list, prefer_consolidated: bool = True) -> int:
    best_page, best_score = -1, -999
    for i, text in extracted_text.items():
        t = text.lower()
        score = sum(w for w, pat in signals if re.search(pat, t))
        
        # Boost Consolidated P&L pages over Standalone
        if prefer_consolidated:
            if 'consolidated' in t:
                score += 8
            elif 'standalone' in t:
                score -= 5

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
        
        pl_page = find_best_page(extracted_text, _PL_SIGNALS, prefer_consolidated=True)
        bs_page = find_best_page(extracted_text, _BS_SIGNALS, prefer_consolidated=True)
        cf_page = find_best_page(extracted_text, _CF_SIGNALS, prefer_consolidated=True)
        reg_page = find_best_page(extracted_text, _REG52_SIGNALS, prefer_consolidated=True)

        # We will do three distinct passes to avoid token caps cutting off BS/CF/Disclosures
        passes = []
        
        # Pass 1: P&L Statement (always run)
        if pl_page != -1:
            pl_pages = {pl_page, pl_page + 1}
            if pl_page > 0: pl_pages.add(pl_page - 1)
            passes.append(("PL", pl_pages))
            
        # Pass 2: Balance Sheet & SEBI Disclosures
        bs_pages = set()
        if bs_page != -1:
            bs_pages.update({bs_page, bs_page + 1})
            if bs_page > 0: bs_pages.add(bs_page - 1)
        if reg_page != -1:
            bs_pages.update({reg_page, reg_page + 1})
            if reg_page > 0: bs_pages.add(reg_page - 1)
        if bs_pages:
            passes.append(("BS_REG", bs_pages))
            
        # Pass 3: Cash Flow Statement
        if cf_page != -1:
            cf_pages = {cf_page, cf_page + 1}
            if cf_page > 0: cf_pages.add(cf_page - 1)
            passes.append(("CF", cf_pages))

        # Invoke LLM Engine
        logger.info("[Agent5] Invoking Groq JSON mode for multi-pass table extraction...")
        llm = ChatGroq(
            model=settings.GROQ_MODEL, 
            temperature=0.0,
            model_kwargs={"response_format": {"type": "json_object"}}
        )

        merged_data = {}

        # Loop through each pass to extract specific blocks sequentially
        for pass_name, target_set in passes:
            logger.info(f"[Agent5] Running extraction pass: {pass_name} on pages {target_set}")
            
            # Determine which keys are allowed in this pass and compile their descriptions
            pass_keys = {
                "PL": _PL_KEYS,
                "BS_REG": _BS_REG_KEYS,
                "CF": _CF_KEYS
            }[pass_name]
            
            pass_schema = {}
            for name, field in FinancialRawSchema.model_fields.items():
                if name in pass_keys:
                    if any(s in name for s in ["_q_prev", "_q_year_ago", "_fy_prev", "_fy_current", "_prev"]):
                        pass_schema[name] = "historical comparative value"
                    else:
                        pass_schema[name] = field.description or "financial metric"
            schema_keys_json = json.dumps(pass_schema, indent=2)
            
            # Compile text for this targeted slice only
            compiled_text = ""
            # Prepend Header Preview for unit extraction
            for first_p in ['0', '1']:
                if first_p in extracted_text and int(first_p) not in target_set:
                    compiled_text += f"\n--- HEADER PREVIEW (PAGE {first_p}) ---\n{extracted_text[first_p][:400]}\n"
                    break
            
            for p in sorted(list(target_set)):
                if str(p) in extracted_text:
                    compiled_text += f"\n--- PAGE {p} ---\n{extracted_text[str(p)]}\n"
            
            compiled_text = compiled_text[:6000] # Safe token limit
            
            if not compiled_text.strip():
                continue
                
            system_prompt = (
                "Your sole mission is to act as a linguistic translator mapping unstructured textual grids into a structured financial JSON object.\n"
                f"You are currently extracting only {pass_name} related metrics. Extract as many metrics as present into a valid JSON object containing keys from this list:\n\n"
                "{schema_keys}\n\n"
                "STRICT NUMERICAL & EXTRACTION RULES:\n"
                "1. Output all financial amounts as raw numbers (floats/ints) without thousands separators/commas.\n"
                "2. If a number is enclosed in brackets or parentheses like (100.50), extract it natively as a negative float (-100.50).\n"
                "3. DO NOT perform any math scaling or currency normalizations yourself.\n"
                "4. NEVER output arithmetic expressions or additions (e.g. do NOT write '7237.22 + 19.11' in any field). Write ONLY a single clean float/integer.\n"
                "5. Identify and populate 'reported_currency_unit' verbatim from the page headers.\n"
                "6. DYNAMIC PERIOD COLUMN MAPPING RULE (CRITICAL):\n"
                "   - Read the column headers at top of table (e.g. '30/06/2026', '31/03/2026', '30/06/2025', '31/03/2026').\n"
                "   - Extract period labels into `period_q_current_label` (e.g., 'Q1 Jun-26'), `period_q_prev_label` (e.g., 'Q4 Mar-26'), `period_q_year_ago_label` (e.g., 'Q1 Jun-25'), `period_fy_prev_label` (e.g., 'FY Mar-26').\n"
                "   - Column 0 (Current Quarter) -> maps to _q_current fields (e.g. revenue_q_current, pat_q_current, basic_eps_q).\n"
                "   - Column 1 (Preceding Quarter) -> maps to _q_prev fields.\n"
                "   - Column 2 (Year-Ago Quarter) -> maps to _q_year_ago fields.\n"
                "   - Column 3 in Q1/Q2/Q3 filings is 'Previous year ended' -> maps to _fy_prev fields! NEVER map Column 3 into _fy_current unless it is a Q4 annual report.\n"
                "7. CONSOLIDATED STATEMENT PRIORITY:\n"
                "   - If both Consolidated and Standalone tables exist, extract ONLY CONSOLIDATED figures.\n"
                "8. If a metric is missing, absent, or represented as '-' or 'N/A', set it to null."
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
                
                # Merge extracted values (ignore nulls to prevent overwriting values extracted in other passes)
                for k, v in parsed_json.items():
                    if v is not None and v != "":
                        merged_data[k] = v
            except Exception as e:
                logger.error(f"[Agent5] Pass {pass_name} extraction failed: {e}")
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    raise ValueError("Groq API Limit Exhausted. Try again after some time")

        # Validate final merged JSON structure using Pydantic
        result = FinancialRawSchema.model_validate(merged_data)

        # 3. Serialize and Save
        financial_data = result.model_dump()
        all_pages = set()
        if pl_page != -1: all_pages.add(pl_page)
        if bs_page != -1: all_pages.add(bs_page)
        if cf_page != -1: all_pages.add(cf_page)
        if reg_page != -1: all_pages.add(reg_page)
        financial_data["source_page_indices"] = sorted(list(all_pages))
        
        logger.info(f"[Agent5] Final extracted merged data: {financial_data}")
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