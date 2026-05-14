from celery.utils.log import get_task_logger
from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus

logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def process_visualization(self, document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.VISUALIZATION_PREP
        db.commit()

        fd  = doc_record.financial_data or {}
        res = doc_record.analysis_results or {}

        # ── Total Income Trend: Q year-ago → Q prev → Q current ─────────────
        # This is the PRIMARY income trend (Revenue from ops + Other income)
        tinc_series = [
            ('Q Mar-25', fd.get('total_income_q_year_ago')),   # col 2: Q 31.03.2025
            ('Q Dec-25', fd.get('total_income_q_prev')),        # col 1: Q 31.12.2025
            ('Q Mar-26', fd.get('total_income_q_current')),    # col 0: Q 31.03.2026
        ]
        tinc_labels = [l for l, v in tinc_series if v is not None]
        tinc_data   = [round(v, 2) for l, v in tinc_series if v is not None]

        # ── PAT Trend: same quarterly progression ────────────────────────────
        pat_series = [
            ('Q Mar-25', fd.get('pat_q_year_ago')),
            ('Q Dec-25', fd.get('pat_q_prev')),
            ('Q Mar-26', fd.get('pat_q_current')),
        ]
        pat_labels = [l for l, v in pat_series if v is not None]
        pat_data   = [round(v, 2) for l, v in pat_series if v is not None]

        # ── Full Year Comparison: FY prev vs FY current ──────────────────────
        fy_series = [
            ('FY Mar-25', fd.get('total_income_fy_prev')),     # col 4: FY 31.03.2025
            ('FY Mar-26', fd.get('total_income_fy_current')),  # col 3: FY 31.03.2026
        ]
        fy_labels = [l for l, v in fy_series if v is not None]
        fy_data   = [round(v, 2) for l, v in fy_series if v is not None]

        # ── Margin Trend chart (quarterly Net Margin %, EBITDA Margin %) ─────
        def qmargin(pat_key, ti_key):
            p = fd.get(pat_key); t = fd.get(ti_key)
            if p and t and t != 0: return round((p / t) * 100, 2)
            return None

        margin_series = [
            {'name': 'Q Mar-25', 'Net Margin': qmargin('pat_q_year_ago', 'total_income_q_year_ago'),
                                  'EBITDA Margin': qmargin('profit_before_exceptional_q_current', 'total_income_q_year_ago')},
            {'name': 'Q Dec-25', 'Net Margin': qmargin('pat_q_prev', 'total_income_q_prev'),
                                  'EBITDA Margin': qmargin('profit_before_exceptional_q_prev', 'total_income_q_prev')},
            {'name': 'Q Mar-26', 'Net Margin': qmargin('pat_q_current', 'total_income_q_current'),
                                  'EBITDA Margin': qmargin('profit_before_exceptional_q_current', 'total_income_q_current')},
        ]
        # Only keep points where at least one value is not None
        margin_series = [p for p in margin_series if any(v is not None for k, v in p.items() if k != 'name')]

        # ── Growth Metrics (kept for backward compat but simplified) ─────────
        growth_map = {
            'Income QoQ %':  res.get('qoq_growth'),
            'Income YoY %':  res.get('yoy_growth'),
            'PAT QoQ %':     res.get('pat_qoq'),
            'PAT YoY %':     res.get('pat_yoy'),
        }
        growth_labels = [k for k, v in growth_map.items() if v is not None]
        growth_data   = [round(v, 2) for k, v in growth_map.items() if v is not None]

        charts_data = {
            'revenue_trend': {   # shows Total Income quarterly trend
                'labels': tinc_labels or ['No Data'],
                'datasets': [{'label': 'Total Income (₹ cr)', 'data': tinc_data or [0]}]
            },
            'pat_trend': {
                'labels': pat_labels or ['No Data'],
                'datasets': [{'label': 'Net Profit (₹ cr)', 'data': pat_data or [0]}]
            },
            'fy_comparison': {
                'labels': fy_labels or ['No Data'],
                'datasets': [{'label': 'Total Income FY (₹ cr)', 'data': fy_data or [0]}]
            },
            'margin_trend': margin_series,   # list of {name, Net Margin, EBITDA Margin}
            'growth_metrics': {
                'labels': growth_labels or ['No Data'],
                'datasets': [{'label': '%', 'data': growth_data or [0]}]
            },
        }

        metadata = dict(doc_record.metadata_json or {})
        metadata['charts_data'] = charts_data
        doc_record.metadata_json = metadata
        db.commit()

        doc_record.processing_status = ProcessingStatus.COMPLETED
        db.commit()

        logger.info(f"[Agent 10] Visualization data prepared and pipeline COMPLETED for doc_id={document_id}")
    except Exception as e:
        logger.error(f"[Agent 10] Error: {e}")
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
