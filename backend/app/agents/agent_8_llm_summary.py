import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class LLMSummarySchema(BaseModel):
    executive_summary: list[str] = Field(description="A professional financial executive summary provided as 3-4 distinct bullet points analyzing the report's overarching narrative.")
    investor_explanation: list[str] = Field(description="A simple, retail-investor friendly explanation of the company's quarter provided as 3-4 distinct bullet points.")
    highlights: list[str] = Field(description="List of 3-4 positive highlights, strong metrics, or tailwinds.")
    risks: list[str] = Field(description="List of 3-4 risks, headwinds, or negative metrics (e.g., declining margins).")

def process_llm_summary(document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.NLP_SUMMARIZATION
        db.commit()

        res = doc_record.analysis_results or {}
        
        # Strictly feed ONLY the calculated math to Gemini to eliminate hallucination vectors
        context_payload = (
            f"--- CALCULATED METRICS ---\n"
            f"QoQ Revenue Growth: {res.get('qoq_growth')}% \n"
            f"YoY Revenue Growth: {res.get('yoy_growth')}% \n"
            f"QoQ EPS Growth: {res.get('eps_qoq')}% \n"
            f"YoY EPS Growth: {res.get('eps_yoy')}% \n"
            f"Net Profit Margin: {res.get('net_margin')}%\n"
            f"EBITDA Margin: {res.get('ebitda_margin')}%\n"
        )
        
        logger.info("[Agent 8] Invoking Groq for LLM Summarization...")
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)
        structured_llm = llm.with_structured_output(LLMSummarySchema)
        
        system_prompt = (
            "You are an elite financial analyst. Read the provided calculated metrics and the raw OCR text from the company's earnings report. "
            "Synthesize a highly professional, accurate, and structured NLP summary."
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Analyze this financial data:\n\n{text}")
        ])
        
        chain = prompt | structured_llm

        try:
            result = chain.invoke({"text": context_payload})
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                logger.error("[Agent 8] Groq API Rate Limit Hit (429). Failing gracefully.")
                raise ValueError("Groq API Limit Exhausted. Try again after some time")
            else:
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
    finally:
        db.close()
