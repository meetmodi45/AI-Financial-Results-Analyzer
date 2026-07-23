import logging
import re
import json
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.core.config import settings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class LLMSummarySchema(BaseModel):
    executive_summary: list[str] = Field(
        default_factory=list,
        description="A list of 4-6 distinct, non-repetitive, institutional-grade summary bullet points covering financial performance, growth drivers, key margins, and risks."
    )
    investor_explanation: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

def sanitize_summary_json(raw_json: str) -> str:
    """Sanitizes raw JSON produced by LLM to fix invalid escaping (like \\' inside strings)."""
    # Remove invalid single-quote escapes \' -> '
    cleaned = raw_json.replace(r"\'", "'")
    # Clean any illegal escape backslashes not followed by valid JSON escape chars
    cleaned = re.sub(r'\\(?![/u"\\bfnrt])', '', cleaned)
    return cleaned

def process_llm_summary(document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.NLP_SUMMARIZATION
        db.commit()

        res = doc_record.analysis_results or {}
        
        # Strictly feed ONLY the calculated math to Gemini/Groq to eliminate hallucination vectors
        context_payload = (
            f"--- CALCULATED METRICS ---\n"
            f"QoQ Revenue Growth: {res.get('qoq_growth')}% \n"
            f"YoY Revenue Growth: {res.get('yoy_growth')}% \n"
            f"QoQ EPS Growth: {res.get('eps_qoq')}% \n"
            f"YoY EPS Growth: {res.get('eps_yoy')}% \n"
            f"Net Profit Margin: {res.get('net_margin')}%\n"
            f"EBITDA Margin: {res.get('ebitda_margin')}%\n"
        )
        
        logger.info("[Agent 8] Invoking Groq JSON mode for LLM Summarization...")
        llm = ChatGroq(
            model=settings.GROQ_MODEL, 
            temperature=0.2,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        
        system_prompt = (
            "You are a Senior Institutional Financial Analyst.\n"
            "Synthesize a clean, highly organized, and non-repetitive analyst summary based on the provided metrics.\n"
            "STRICT RULES:\n"
            "1. Output ONLY a single JSON object with key 'executive_summary' containing a list of 4-6 distinct, high-value bullet point strings.\n"
            "2. DO NOT repeat the same metric or stat across multiple bullet points. Mention each metric (e.g., revenue growth, EPS, net margin) AT MOST ONCE.\n"
            "3. Structure the points logically in sequence:\n"
            "   - Point 1: Revenue & Top-line Performance (QoQ / YoY)\n"
            "   - Point 2: Earnings & EPS Strength\n"
            "   - Point 3: Profitability & Operational Margins (Net Margin / EBITDA)\n"
            "   - Point 4: Key Growth Driver or Strategic Conclusion\n"
            "   - Point 5: Key Risk or Area of Caution\n"
            "4. Write apostrophes as standard unescaped characters ' inside double-quoted JSON strings (e.g. write \"company's\", NOT \"company\\'s\")."
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Analyze this financial data and output a single valid JSON object:\n\n{text}")
        ])
        
        chain = prompt | llm

        try:
            raw_response = chain.invoke({"text": context_payload})
            raw_text = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
            
            cleaned_text = sanitize_summary_json(raw_text)
            parsed_json = json.loads(cleaned_text)
            result = LLMSummarySchema.model_validate(parsed_json)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                logger.error("[Agent 8] Groq API Rate Limit Hit (429). Failing gracefully.")
                raise ValueError("Groq API Limit Exhausted. Try again after some time")
            else:
                logger.error(f"[Agent 8] Parsing LLM Summary failed: {e}")
                raise e
        
        doc_record.nlp_summary = result.model_dump()
        db.commit()
        logger.info(f"[Agent 8] NLP summary generated for doc_id={document_id}")
        logger.info(f"Agent 8 (NLP Summary) completed for {document_id}")
    except Exception as e:
        logger.error(f"[Agent 8] Error: {e}")
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
        raise e
    finally:
        db.close()
