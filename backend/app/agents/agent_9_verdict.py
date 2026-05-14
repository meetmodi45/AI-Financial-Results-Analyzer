from celery.utils.log import get_task_logger
from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.agents.agent_10_visualization import process_visualization
import joblib
import pandas as pd

logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def process_verdict(self, document_id: str):
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
        process_visualization.delay(document_id)
    except Exception as e:
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
