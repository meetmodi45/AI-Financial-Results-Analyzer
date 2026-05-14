from celery.utils.log import get_task_logger
from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.agents.agent_7_analysis import process_financial_analysis

logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def process_normalization(self, document_id: str):
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
        process_financial_analysis.delay(document_id)
    except Exception as e:
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
