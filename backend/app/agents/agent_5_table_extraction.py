import logging
import re
import json
import os
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.schemas.financial import FinancialRawSchema

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

        # Slice the text array
        compiled_text = ""
        for p in sorted(list(target_pages)):
            if str(p) in extracted_text:
                compiled_text += f"\n--- PAGE {p} ---\n{extracted_text[str(p)]}\n"
        
        if not compiled_text.strip():
            raise ValueError("No financial data could be extracted; targeted context is empty.")



        # 2. Invoke LLM Engine
        logger.info("[Agent5] Invoking Groq with structured output...")
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0)
        structured_llm = llm.with_structured_output(FinancialRawSchema)

        system_prompt = (
            "Your sole mission is to act as a linguistic translator mapping unstructured textual grids into the provided response schema. "
            "Extract all metrics exactly as written on the page face. "
            "DO NOT perform any math scaling, currency normalizations, or multi-period conversions yourself. "
            "If a number is enclosed in brackets like (100.50), extract it natively as a negative float (-100.50). "
            "Identify and populate the 'reported_currency_unit' field verbatim from the page headers. "
            "CRITICAL: Output all numerical values as valid JSON numbers. NEVER include commas in numbers (e.g. use 1500.50, NOT 1,500.50)."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Extract the financial profile from the following pages:\n\n{text}")
        ])

        chain = prompt | structured_llm

        try:
            result = chain.invoke({"text": compiled_text})
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                logger.error("[Agent5] Groq API Rate Limit Hit (429). Failing gracefully.")
                raise ValueError("Groq API Limit Exhausted. Try again after some time")
            else:
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