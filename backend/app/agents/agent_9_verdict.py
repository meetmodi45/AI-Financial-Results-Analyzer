import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
import joblib
import pandas as pd

logger = logging.getLogger(__name__)

def process_verdict(document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.VERDICT_PREDICTION
        db.commit()
        model = joblib.load('app/ml_models/verdict_classifier.joblib')
        res = doc_record.analysis_results
        df = pd.DataFrame([{
            'qoq_growth': res.get('qoq_growth', 0),
            'yoy_growth': res.get('yoy_growth', 0),
            'net_margin': res.get('net_margin', 0),
            'earnings_strength': 80
        }])
        pred = model.predict(df)[0]
        doc_record.verdict = {'verdict': pred, 'confidence': 0.95}
        db.commit()
        logger.info(f"Agent 9 (Verdict) completed for {document_id}")
    except Exception as e:
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
