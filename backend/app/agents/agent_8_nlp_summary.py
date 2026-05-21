import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus

logger = logging.getLogger(__name__)

def _growth_comment(value: float | None) -> str:
    if value is None: return "data unavailable"
    if value > 15: return "strong growth"
    if value > 5: return "moderate growth"
    if value > 0: return "marginal growth"
    if value > -5: return "slight decline"
    return "significant decline"

def _margin_comment(value: float | None) -> str:
    if value is None: return "data unavailable"
    if value > 25: return "excellent profitability"
    if value > 15: return "healthy profitability"
    if value > 5: return "moderate margins"
    return "thin margins with profitability concerns"


def process_nlp_summary(document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.NLP_SUMMARIZATION
        db.commit()

        res = doc_record.analysis_results or {}
        fd = doc_record.financial_data or {}
        meta = doc_record.metadata_json or {}

        qoq = res.get('qoq_growth')
        yoy = res.get('yoy_growth')
        margin = res.get('net_margin')
        category = meta.get('document_category', 'Financial Report')
        pdf_type = meta.get('pdf_type', 'text_pdf')
        confidence = fd.get('extraction_confidence', 'unknown')

        qoq_str = f"{qoq}%" if qoq is not None else "N/A (could not extract from PDF)"
        yoy_str = f"{yoy}%" if yoy is not None else "N/A (could not extract from PDF)"
        margin_str = f"{margin}%" if margin is not None else "N/A"

        # Executive summary
        if qoq is not None and yoy is not None and margin is not None:
            executive_summary = (
                f"This {category} shows {_growth_comment(qoq)} quarter-on-quarter ({qoq_str}) "
                f"and {_growth_comment(yoy)} year-on-year ({yoy_str}). "
                f"The business demonstrates {_margin_comment(margin)}, with a net profit margin of {margin_str}. "
                f"Metrics were extracted from a {pdf_type.replace('_', ' ')} with {confidence} confidence."
            )
        else:
            executive_summary = (
                f"This document is classified as a {category}. "
                f"Financial metric extraction confidence is low — the PDF may use non-standard table formatting. "
                f"QoQ: {qoq_str} | YoY: {yoy_str} | Net Margin: {margin_str}."
            )

        # Investor context
        investor_explanation = (
            f"For a retail investor: a QoQ growth of {qoq_str} means the company earned "
            f"{'more' if (qoq or 0) >= 0 else 'less'} compared to last quarter. "
            f"The YoY growth of {yoy_str} compares this quarter to the same quarter last year. "
            f"A net margin of {margin_str} means for every ₹100 of revenue, the company keeps ₹{margin:.2f} as profit." 
            if margin is not None else
            f"For a retail investor: this document reports the company's recent financial performance. "
            f"Some financial metrics could not be auto-extracted; please review the original PDF for exact figures."
        )

        # Highlights — only add if data exists
        highlights = []
        if yoy is not None and yoy > 0:
            highlights.append(f"Positive YoY revenue growth of {yoy}%")
        if margin is not None and margin > 15:
            highlights.append(f"Strong net profit margin at {margin}%")
        if qoq is not None and qoq > 0:
            highlights.append(f"Sequential (QoQ) growth of {qoq}% shows business momentum")
        if fd.get('ebitda'):
            highlights.append(f"EBITDA reported at {fd['ebitda']:,.0f} (operating strength indicator)")
        if not highlights:
            highlights.append("Pipeline completed — check source PDF for manually verified figures")

        # Risks
        risks = []
        if yoy is not None and yoy < 0:
            risks.append(f"Negative YoY growth of {yoy}% signals business contraction")
        if margin is not None and margin < 10:
            risks.append(f"Low net margin ({margin}%) indicates cost or pricing pressure")
        if qoq is not None and qoq < 0:
            risks.append(f"QoQ decline of {qoq}% — sequential slowdown detected")
        if confidence == 'low':
            risks.append("Low extraction confidence — figures may be inaccurate; manual verification recommended")
        if not risks:
            risks.append("No major red flags detected in extracted financial metrics")

        doc_record.nlp_summary = {
            'executive_summary': executive_summary,
            'investor_explanation': investor_explanation,
            'highlights': highlights,
            'risks': risks,
        }
        db.commit()
        logger.info(f"[Agent 8] NLP summary generated for doc_id={document_id}")
        logger.info(f"Agent 8 (NLP Summary) completed for {document_id}")
    except Exception as e:
        logger.error(f"[Agent 8] Error: {e}")
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
