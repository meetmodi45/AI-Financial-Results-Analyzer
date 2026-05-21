import logging
import traceback
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus

# Import all agents
from app.agents.agent_2_pdf_type import process_pdf_type
from app.agents.agent_3_ocr import process_ocr
from app.agents.agent_4_classifier import classify_document
from app.agents.agent_5_table_extraction import process_tables
from app.agents.agent_6_normalization import process_normalization
from app.agents.agent_7_analysis import process_financial_analysis
from app.agents.agent_8_nlp_summary import process_nlp_summary
from app.agents.agent_9_verdict import process_verdict
from app.agents.agent_10_visualization import process_visualization

logger = logging.getLogger(__name__)

# List of all agent functions in their execution order
PIPELINE_STAGES = [
    ("PDF_TYPE", process_pdf_type),
    ("OCR", process_ocr),
    ("CLASSIFICATION", classify_document),
    ("TABLE_EXTRACTION", process_tables),
    ("NORMALIZATION", process_normalization),
    ("FINANCIAL_ANALYSIS", process_financial_analysis),
    ("NLP_SUMMARY", process_nlp_summary),
    ("VERDICT", process_verdict),
    ("VISUALIZATION", process_visualization),
]

def run_extraction_pipeline(document_id: str, file_path: str):
    """
    Executes all agents sequentially in a background thread.
    Halts immediately if any agent fails or sets the status to FAILED.
    """
    logger.info(f"Starting extraction pipeline for doc_id={document_id}")
    import os
    
    try:
        for stage_name, agent_func in PIPELINE_STAGES:
            logger.info(f"Pipeline -> Executing stage: {stage_name}")
            
            try:
                # Execute the agent synchronously
                if stage_name in ("PDF_TYPE", "OCR"):
                    agent_func(document_id, file_path)
                else:
                    agent_func(document_id)
                
                # Verify status after execution
                db = SessionLocal()
                try:
                    doc = db.query(Document).filter(Document.id == document_id).first()
                    if not doc:
                        logger.error(f"Pipeline halted: Document {document_id} not found after {stage_name}")
                        break
                    
                    if doc.processing_status == ProcessingStatus.FAILED:
                        logger.error(f"Pipeline halted: Document {document_id} FAILED during {stage_name}")
                        break
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"Pipeline crashed at stage {stage_name} for doc_id={document_id}: {e}")
                logger.error(traceback.format_exc())
                
                # Ensure DB is marked as failed
                db = SessionLocal()
                try:
                    doc = db.query(Document).filter(Document.id == document_id).first()
                    if doc:
                        doc.processing_status = ProcessingStatus.FAILED
                        doc.error_message = f"Pipeline crashed at {stage_name}: {str(e)}"
                        db.commit()
                except Exception as db_err:
                    logger.error(f"Failed to update DB error state: {db_err}")
                finally:
                    db.close()
                break
                
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Ephemeral file destroyed: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete ephemeral file {file_path}: {e}")

    logger.info(f"Finished extraction pipeline for doc_id={document_id}")
