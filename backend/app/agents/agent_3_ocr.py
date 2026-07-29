import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
import fitz
import traceback

logger = logging.getLogger(__name__)

def get_layout_text(page) -> str:
    """Reconstructs text row-by-row by grouping words by vertical coordinates and sorting horizontally."""
    words = page.get_text("words")
    if not words:
        return page.get_text()
    
    # Group words by their y-coordinates (line centers)
    lines = {}
    for w in words:
        x0, y0, x1, y1, word = w[:5]
        y_center = (y0 + y1) / 2.0
        
        # Find if this center is close to any existing line key (within 5 pixels threshold)
        found = False
        for y_key in lines:
            if abs(y_center - y_key) < 5.0:
                lines[y_key].append((x0, word))
                found = True
                break
        if not found:
            lines[y_center] = [(x0, word)]
            
    # Reassemble lines sorted vertically from top to bottom
    sorted_y_keys = sorted(lines.keys())
    text_lines = []
    for y in sorted_y_keys:
        # Sort words in this line horizontally from left to right
        sorted_words = sorted(lines[y], key=lambda item: item[0])
        line_str = " ".join(item[1] for item in sorted_words)
        text_lines.append(line_str)
        
    return "\n".join(text_lines)

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
            text = get_layout_text(doc[page_num])
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
