from celery.utils.log import get_task_logger
import fitz  # PyMuPDF
import os
from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.agents.agent_3_ocr import process_ocr

logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3)
def process_pdf_type(self, document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.CLASSIFYING_PDF
        db.commit()
        file_path = doc_record.metadata_json.get('file_path')
        doc = fitz.open(file_path)
        total_pages = len(doc)
        text_pages, scanned_pages = 0, 0
        for page_num in range(total_pages):
            if len(doc[page_num].get_text().strip()) > 50: text_pages += 1
            else: scanned_pages += 1
        doc.close()
        pdf_type = 'scanned_pdf' if scanned_pages == total_pages else 'text_pdf' if text_pages == total_pages else 'hybrid_pdf'
        current_metadata = dict(doc_record.metadata_json)
        current_metadata.update({'pdf_type': pdf_type, 'text_pages': text_pages, 'scanned_pages': scanned_pages, 'requires_ocr': pdf_type in ['scanned_pdf', 'hybrid_pdf']})
        doc_record.metadata_json = current_metadata
        db.commit()
        process_ocr.delay(document_id)
    except Exception as e:
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
