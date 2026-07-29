import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus

logger = logging.getLogger(__name__)


def process_visualization(document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.VISUALIZATION_PREP
        db.commit()

        fd  = doc_record.financial_data or {}
        res = doc_record.analysis_results or {}

        def safe_round(val):
            if val is None:
                return None
            try:
                return round(float(val), 2)
            except (ValueError, TypeError):
                return None

        lbl_yoy = res.get('period_q_year_ago_label') or fd.get('period_q_year_ago_label') or 'Q Year-Ago'
        lbl_prev = res.get('period_q_prev_label') or fd.get('period_q_prev_label') or 'Q Preceding'
        lbl_curr = res.get('period_q_current_label') or fd.get('period_q_current_label') or 'Q Current'
        lbl_fy_prev = res.get('period_fy_prev_label') or fd.get('period_fy_prev_label') or 'FY Previous'

        # ── Total Income Trend: Q year-ago → Q prev → Q current ─────────────
        tinc_series = [
            (lbl_yoy, fd.get('total_income_q_year_ago') or fd.get('revenue_q_year_ago')),
            (lbl_prev, fd.get('total_income_q_prev') or fd.get('revenue_q_prev')),
            (lbl_curr, fd.get('total_income_q_current') or fd.get('revenue_q_current')),
        ]
        tinc_labels = [l for l, v in tinc_series if safe_round(v) is not None]
        tinc_data   = [safe_round(v) for l, v in tinc_series if safe_round(v) is not None]

        # ── PAT Trend: same quarterly progression ────────────────────────────
        pat_series = [
            (lbl_yoy, fd.get('pat_q_year_ago')),
            (lbl_prev, fd.get('pat_q_prev')),
            (lbl_curr, fd.get('pat_q_current')),
        ]
        pat_labels = [l for l, v in pat_series if safe_round(v) is not None]
        pat_data   = [safe_round(v) for l, v in pat_series if safe_round(v) is not None]

        # ── Full Year Comparison: FY prev vs FY current ──────────────────────
        fy_series = [
            (lbl_fy_prev, fd.get('total_income_fy_prev') or fd.get('revenue_fy_prev')),
            ('FY Current', fd.get('total_income_fy_current') or fd.get('revenue_fy_current')),
        ]
        fy_labels = [l for l, v in fy_series if safe_round(v) is not None]
        fy_data   = [safe_round(v) for l, v in fy_series if safe_round(v) is not None]

        # ── Margin Trend chart (quarterly Net Margin %, Operating Margin %) ─────
        def qmargin(num_key, den_key):
            p = fd.get(num_key); t = fd.get(den_key)
            if p and t and t != 0: return round((p / t) * 100, 2)
            return None

        def opm(pbe, pbt, ti):
            t = fd.get(ti)
            if not t: return None
            p = fd.get(pbe) or fd.get(pbt)
            if p: return round((p / t) * 100, 2)
            return None

        margin_series = [
            {'name': lbl_yoy, 'OPM': None},
            {'name': lbl_prev, 'OPM': opm('profit_before_exceptional_q_prev', 'profit_before_tax_q_prev', 'total_income_q_prev')},
            {'name': lbl_curr, 'OPM': opm('profit_before_exceptional_q_current', 'profit_before_tax_q_current', 'total_income_q_current')},
        ]
        # Only keep points where at least one value is not None
        margin_series = [p for p in margin_series if any(v is not None for k, v in p.items() if k != 'name')]

        # ── EPS Trend ────────────────────────────────────────────────────────
        eps_series = [
            (lbl_yoy, fd.get('basic_eps_q_year_ago')),
            (lbl_prev, fd.get('basic_eps_q_prev')),
            (lbl_curr, fd.get('basic_eps_q')),
        ]
        eps_labels = [l for l, v in eps_series if safe_round(v) is not None]
        eps_data   = [safe_round(v) for l, v in eps_series if safe_round(v) is not None]

        growth_map = {
            'Income QoQ %':  res.get('qoq_growth'),
            'Income YoY %':  res.get('yoy_growth'),
            'PAT QoQ %':     res.get('pat_qoq'),
            'PAT YoY %':     res.get('pat_yoy'),
        }
        growth_labels = [k for k, v in growth_map.items() if safe_round(v) is not None]
        growth_data   = [safe_round(v) for k, v in growth_map.items() if safe_round(v) is not None]

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
            'margin_trend': margin_series,
            'eps_trend': {
                'labels': eps_labels or ['No Data'],
                'datasets': [{'label': 'Basic EPS (₹)', 'data': eps_data or [0]}]
            },
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
