import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
import fitz
import traceback

logger = logging.getLogger(__name__)

def process_ocr(document_id: str, file_path: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.OCR_EXTRACTION
        db.commit()
        requires_ocr = (doc_record.metadata_json or {}).get('requires_ocr', False)
        doc = fitz.open(file_path)
        extracted_text = {}
        for page_num in range(len(doc)):
            text = doc[page_num].get_text()
            if len(text.strip()) <= 50 and requires_ocr: text = '[OCR Extracted Text Placeholder]'
            extracted_text[str(page_num)] = text
        doc.close()
        doc_record.extracted_text = extracted_text
        db.commit()
        logger.info(f"Agent 3 (OCR) completed for {document_id}")
    except Exception as e:
        logger.error(f"[Agent 3] FAILED for doc_id={document_id}: {e}")
        logger.error(traceback.format_exc())
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = f"[Agent 3 OCR] {str(e)}"
        db.commit()
    finally:
        db.close()
