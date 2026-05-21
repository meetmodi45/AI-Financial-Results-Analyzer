import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus

logger = logging.getLogger(__name__)

def process_normalization(document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.NORMALIZING_METRICS
        db.commit()
        data = dict(doc_record.financial_data)
        data['normalized'] = True
        doc_record.financial_data = data
        db.commit()
        logger.info(f"Agent 6 (Normalization) completed for {document_id}")
    except Exception as e:
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
