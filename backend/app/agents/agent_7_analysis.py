import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus

logger = logging.getLogger(__name__)
def safe_growth(current, previous):
    """Growth % between two values. Returns None if data is missing or prev is 0."""
    if current is None or previous is None or previous == 0:
        return None
    return round(((current - previous) / abs(previous)) * 100, 2)


def safe_margin(numerator, denominator):
    """Ratio as %. Returns None if data is missing."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round((numerator / denominator) * 100, 2)


def process_financial_analysis(document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record:
        return
    try:
        doc_record.processing_status = ProcessingStatus.FINANCIAL_ANALYSIS
        db.commit()

        fd = doc_record.financial_data or {}

        # ── Total Income (PRIMARY metric — includes Other Income) ─────────────
        # Column layout:  0=Q_curr  1=Q_prev  2=Q_yoy  3=FY_curr  4=FY_prev
        ti_q_curr  = fd.get('total_income_q_current')   # 31.03.2026 quarter
        ti_q_prev  = fd.get('total_income_q_prev')      # 31.12.2025 quarter
        ti_fy_curr = fd.get('total_income_fy_current')  # FY 31.03.2026
        ti_fy_prev = fd.get('total_income_fy_prev')     # FY 31.03.2025  ← YoY base

        # ── Net Profit (PAT) ─────────────────────────────────────────────────
        pat_q_curr  = fd.get('pat_q_current')    # Q 31.03.2026
        pat_q_prev  = fd.get('pat_q_prev')       # Q 31.12.2025
        pat_fy_curr = fd.get('pat_fy_current')   # FY 31.03.2026
        pat_fy_prev = fd.get('pat_fy_prev')      # FY 31.03.2025

        # ── Profit Before Tax & EBITDA proxy ─────────────────────────────────
        pbt_q_curr   = fd.get('profit_before_tax_q_current')
        pbt_fy_curr  = fd.get('profit_before_tax_fy_current')
        pbt_fy_prev  = fd.get('profit_before_tax_fy_prev')
        # EBITDA proxy = Profit before exceptional items & tax (excludes finance costs + depreciation already in expenses)
        ebitda_q     = fd.get('profit_before_exceptional_q_current')
        ebitda_fy    = fd.get('profit_before_exceptional_fy_current')

        # ── Growth Calculations ───────────────────────────────────────────────
        # QoQ  = Current Quarter vs Previous Quarter (col 0 vs col 1)
        # YoY  = Full Year current vs Full Year previous (col 3 vs col 4)
        results = {
            # Total Income growth
            'qoq_growth':      safe_growth(ti_q_curr, ti_q_prev),    # Q current vs Q prev
            'yoy_growth':      safe_growth(ti_fy_curr, ti_fy_prev),   # FY current vs FY prev

            # PAT growth
            'pat_qoq':         safe_growth(pat_q_curr, pat_q_prev),   # Q current vs Q prev
            'pat_yoy':         safe_growth(pat_fy_curr, pat_fy_prev), # FY current vs FY prev

            # PBT growth (full year)
            'pbt_yoy':         safe_growth(pbt_fy_curr, pbt_fy_prev),

            # Margins (as % of Total Income for the quarter)
            'net_margin':      safe_margin(pat_q_curr, ti_q_curr),    # PAT / Total Income (Q)
            'pbt_margin':      safe_margin(pbt_q_curr, ti_q_curr),    # PBT / Total Income (Q)
            'ebitda_margin':   safe_margin(ebitda_q, ti_q_curr),      # EBITDA proxy / Total Income (Q)
            'net_margin_fy':   safe_margin(pat_fy_curr, ti_fy_curr),  # Annual net margin
            'pbt_margin_fy':   safe_margin(pbt_fy_curr, ti_fy_curr),  # Annual PBT margin
            'ebitda_margin_fy': safe_margin(ebitda_fy, ti_fy_curr),   # Annual EBITDA margin

            # Absolute figures (₹ crores) — for display & charts
            'total_income_q_cr':   ti_q_curr,
            'total_income_fy_cr':  ti_fy_curr,
            'pat_q_current_cr':    pat_q_curr,
            'pat_fy_current_cr':   pat_fy_curr,
            'ebitda_q_cr':         ebitda_q,
            'basic_eps':           fd.get('basic_eps_q'),
        }

        # Remove None values
        results = {k: v for k, v in results.items() if v is not None}
        logger.info(f"[Agent 7] Analysis: {results}")

        doc_record.analysis_results = results
        db.commit()
        logger.info(f"Agent 7 (Financial Analysis) completed for {document_id}")

    except Exception as e:
        logger.error(f"[Agent 7] Error: {e}", exc_info=True)
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
