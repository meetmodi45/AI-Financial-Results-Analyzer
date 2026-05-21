import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
import joblib
import re

logger = logging.getLogger(__name__)

# Keyword sets for rule-based fallback classification
CATEGORY_KEYWORDS = {
    'Quarterly Results': ['quarterly results', 'q1', 'q2', 'q3', 'q4', 'quarter', 'qoq', 'revenue from operations'],
    'Annual Report': ['annual report', 'annual results', 'full year', 'fy2', 'financial year'],
    'Press Release': ['press release', 'media release', 'investor update'],
    'Earnings Call': ['earnings call', 'conference call', 'analyst call', 'earnings transcript'],
    'Financial Statement': ['balance sheet', 'profit and loss', 'income statement', 'cash flow statement'],
}

def classify_document(document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.DOCUMENT_CLASSIFICATION
        db.commit()

        # Get the actual extracted text from Agent 3
        extracted_text = doc_record.extracted_text or {}
        full_text = ' '.join(extracted_text.values()).lower()[:3000]  # use first 3000 chars

        # Try ML model first
        category = None
        try:
            model = joblib.load('app/ml_models/doc_classifier.joblib')
            category = model.predict([full_text])[0]
            logger.info(f"ML model classified document as: {category}")
        except Exception as ml_err:
            logger.warning(f"ML model failed ({ml_err}), falling back to keyword matching")

        # Keyword-based fallback if ML fails or returns generic result
        if not category or category == 'Unknown':
            best_match = 'Financial Document'
            best_score = 0
            for cat, keywords in CATEGORY_KEYWORDS.items():
                score = sum(1 for kw in keywords if kw in full_text)
                if score > best_score:
                    best_score = score
                    best_match = cat
            category = best_match

        metadata = dict(doc_record.metadata_json)
        metadata['document_category'] = category
        doc_record.metadata_json = metadata
        db.commit()
        logger.info(f"[Agent 4] Document classified as '{category}' for doc_id={document_id}")
        logger.info(f"Agent 4 (Classification) completed for {document_id}")
    except Exception as e:
        logger.error(f"[Agent 4] Error: {e}")
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
