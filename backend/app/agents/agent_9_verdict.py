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
        res = doc_record.analysis_results or {}
        
        qoq = float(res.get('qoq_growth', 0) or 0)
        yoy = float(res.get('yoy_growth', 0) or 0)
        margin = float(res.get('net_margin', 0) or 0)
        
        # Calculate algorithmic earnings strength matching the training feature distribution
        earnings_strength = (qoq * 0.4) + (yoy * 0.4) + (margin * 0.2)
        
        df = pd.DataFrame([{
            'qoq_growth': qoq,
            'yoy_growth': yoy,
            'net_margin': margin,
            'earnings_strength': earnings_strength
        }])
        
        # Get actual class prediction
        pred = model.predict(df)[0]
        
        # Get mathematical probability for the predicted class
        proba = model.predict_proba(df)[0]
        class_idx = list(model.classes_).index(pred)
        confidence = float(proba[class_idx])
        
        doc_record.verdict = {'verdict': pred, 'confidence': round(confidence, 2)}
        db.commit()
        logger.info(f"Agent 9 (Verdict) completed for {document_id} with prediction: {pred} ({confidence:.2f})")
    except Exception as e:
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
