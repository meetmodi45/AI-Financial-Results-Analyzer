from celery.utils.log import get_task_logger
from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.agents.agent_4_classifier import classify_document
import fitz

logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def process_ocr(self, document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.OCR_EXTRACTION
        db.commit()
        file_path = doc_record.metadata_json.get('file_path')
        requires_ocr = doc_record.metadata_json.get('requires_ocr', False)
        doc = fitz.open(file_path)
        extracted_text = {}
        for page_num in range(len(doc)):
            text = doc[page_num].get_text()
            if len(text.strip()) <= 50 and requires_ocr: text = '[OCR Extracted Text Placeholder]'
            extracted_text[str(page_num)] = text
        doc.close()
        doc_record.extracted_text = extracted_text
        db.commit()
        classify_document.delay(document_id)
    except Exception as e:
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
