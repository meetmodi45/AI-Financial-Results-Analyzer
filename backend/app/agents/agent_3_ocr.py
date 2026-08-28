import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
import pdfplumber
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
        
        extracted_text = {}
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # 1. Extract contextual text (without layout=True to save characters)
                page_text = page.extract_text() or ""
                
                page_text = page.extract_text() or ""
                
                if len(page_text.strip()) <= 50 and requires_ocr: 
                    page_text = '[OCR Extracted Text Placeholder]'
                    
                extracted_text[str(page_num)] = page_text
                
        doc_record.extracted_text = extracted_text
        db.commit()
        logger.info(f"Agent 3 (OCR - pdfplumber hybrid) completed for {document_id}")
    except Exception as e:
        logger.error(f"[Agent 3] FAILED for doc_id={document_id}: {e}")
        logger.error(traceback.format_exc())
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = f"[Agent 3 OCR] {str(e)}"
        db.commit()
    finally:
        db.close()
