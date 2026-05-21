import logging
import fitz  # PyMuPDF
import os
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus

logger = logging.getLogger(__name__)

def process_pdf_type(document_id: str, file_path: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.CLASSIFYING_PDF
        db.commit()
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

        if pdf_type in ['scanned_pdf', 'hybrid_pdf']:
            # Cleanup the temporary PDF file to save space
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as cleanup_err:
                    logger.error(f"Failed to cleanup file {file_path}: {cleanup_err}")
            
            # Raise custom exception to abort the pipeline
            class ScannedDocumentError(Exception):
                pass
            raise ScannedDocumentError("Scanned copy detected. Current model works for standard text robustly only.")

        # Proactively advance the status so the UI knows Agent 2 is complete
        doc_record.processing_status = ProcessingStatus.OCR_EXTRACTION
        db.commit()

        try:
            logger.info(f"Agent 2 (PDF Type) completed for {document_id}")
        except Exception as queue_err:
            logger.error(f"Silent queue failure for Agent 3: {queue_err}")
            doc_record.processing_status = ProcessingStatus.FAILED
            doc_record.error_message = f"Failed to transition to Agent 3: {str(queue_err)}"
            db.commit()
            return
    except Exception as e:
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
