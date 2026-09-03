import logging
import re
import json
import os
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.schemas.financial import FinancialRawSchema

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

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
            if 'consolidated financial result' in t or 'consolidated unaudited' in t or 'consolidated audited' in t:
                score += 15
            elif 'standalone financial result' in t or 'standalone unaudited' in t or 'standalone audited' in t:
                score -= 10

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
    cleaned = raw_json.strip()
    
    # Strip markdown formatting if present (e.g. ```json ... ```)
    if "{" in cleaned and "}" in cleaned:
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        cleaned = cleaned[start_idx:end_idx+1]
        
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
        
    cleaned = re.sub(r'(:\s*)\"(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?)\"', fix_quoted_commas, cleaned)
    
    if cleaned and not cleaned.strip().endswith('}'):
        cleaned = cleaned.strip() + '}'
        
    if not cleaned or cleaned.isspace():
        cleaned = "{}"
        
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

        # Instead of three passes which trigger Groq 8000 TPM limits sequentially, we do ONE combined pass.
        target_set = set()
        if pl_page != -1:
            target_set.update({pl_page, pl_page + 1})
            if pl_page > 0: target_set.add(pl_page - 1)
        if bs_page != -1:
            target_set.update({bs_page, bs_page + 1})
            if bs_page > 0: target_set.add(bs_page - 1)
        if cf_page != -1:
            target_set.update({cf_page, cf_page + 1})
            if cf_page > 0: target_set.add(cf_page - 1)
        if reg_page != -1:
            target_set.update({reg_page, reg_page + 1})
            if reg_page > 0: target_set.add(reg_page - 1)
            
        passes = [("ALL", target_set)]

        # Invoke LLM Engine
        logger.info("[Agent5] Setting up Groq as primary and Gemini as fallback...")
        from langchain_groq import ChatGroq
        primary_llm = ChatGroq(
            model=settings.GROQ_MODEL,
            temperature=0.0,
            api_key=settings.GROQ_API_KEY
        )
        
        fallback_llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            temperature=0.0,
            max_output_tokens=4000,
            google_api_key=settings.GEMINI_API_KEY,
            model_kwargs={"response_mime_type": "application/json"}
        )

        merged_data = {}

        for pass_name, target_set in passes:
            logger.info(f"[Agent5] Running extraction pass: {pass_name} on pages {target_set}")
            
            # Combine all keys for the single pass
            pass_keys = _PL_KEYS + _BS_REG_KEYS + _CF_KEYS
            
            pass_schema = {}
            for name, field in FinancialRawSchema.model_fields.items():
                if name in pass_keys:
                    if any(s in name for s in ["_q_prev", "_q_year_ago", "_fy_prev", "_fy_current", "_prev"]):
                        pass_schema[name] = "historical comparative value"
                    else:
                        pass_schema[name] = field.description or "financial metric"
            schema_keys_json = json.dumps(pass_schema, separators=(',', ':'))
            
            compiled_text = ""
            # Prepend Header Preview for unit extraction
            for first_p in ['0', '1']:
                if first_p in extracted_text and int(first_p) not in target_set:
                    compiled_text += f"\n--- HEADER PREVIEW (PAGE {first_p}) ---\n{extracted_text[first_p][:400]}\n"
                    break
            
            for p in sorted(list(target_set)):
                if str(p) in extracted_text:
                    compiled_text += f"\n--- PAGE {p} ---\n{extracted_text[str(p)]}\n"
            
            compiled_text = compiled_text[:8000] # Safe token limit for 8000 TPM free tier
            
            if not compiled_text.strip():
                continue
                
            system_prompt = (
                "You are a precise data extraction API. Map the unstructured financial tables into a structured JSON object using exactly these keys:\n\n"
                "{schema_keys}\n\n"
                "STRICT RULES:\n"
                "1. Output all financial amounts as raw numbers (floats/ints).\n"
                "2. If a number is enclosed in brackets like (100.50), extract as a negative float (-100.50).\n"
                "3. DYNAMIC PERIOD COLUMN MAPPING RULE:\n"
                "   - Column 0 (Current Quarter) -> _q_current fields.\n"
                "   - Column 1 (Preceding Quarter) -> _q_prev fields.\n"
                "   - Column 2 (Year-Ago Quarter) -> _q_year_ago fields.\n"
                "4. CONSOLIDATED STATEMENT PRIORITY:\n"
                "   - If you see both Consolidated and Standalone figures, EXTRACT ONLY CONSOLIDATED FIGURES.\n"
                "5. Always output a valid JSON object."
            )
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "Extract the financial profile into JSON. Do NOT wrap it in markdown:\n\n{text}")
            ])

            def attempt_pass(llm_instance):
                chain = prompt | llm_instance
                res = chain.invoke({"schema_keys": schema_keys_json, "text": compiled_text})
                
                raw_text = res.content
                if isinstance(raw_text, list):
                    raw_text = "".join([part.get("text", "") for part in raw_text if isinstance(part, dict) and "text" in part])
                elif not isinstance(raw_text, str):
                    raw_text = str(raw_text)
                    
                logger.info(f"[Agent5 DEBUG] Raw LLM Output (first 1000 chars): {raw_text[:1000]}")
                
                sanitized_text = sanitize_json_string(raw_text)
                return json.loads(sanitized_text)

            parsed_json = {}
            import time
            
            try:
                logger.info(f"[Agent5] Attempting pass {pass_name} with Groq...")
                parsed_json = attempt_pass(primary_llm)
            except Exception as e:
                logger.warning(f"[Agent5] Groq failed: {e}. Falling back to Gemini...")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        parsed_json = attempt_pass(fallback_llm)
                        break
                    except Exception as fallback_e:
                        if attempt < max_retries - 1 and ("429" in str(fallback_e) or "RESOURCE_EXHAUSTED" in str(fallback_e) or "rate_limit" in str(fallback_e)):
                            logger.warning(f"[Agent 5] Gemini API limit hit. Retrying in 60 seconds... (Attempt {attempt+1}/{max_retries})")
                            time.sleep(60)
                        else:
                            logger.error(f"[Agent5] Gemini parsing failed: {fallback_e}")
                            raise fallback_e
            
            # Merge extracted values (ignore nulls to prevent overwriting values extracted in other passes)
            for k, v in parsed_json.items():
                if v is not None and v != "":
                    merged_data[k] = v

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