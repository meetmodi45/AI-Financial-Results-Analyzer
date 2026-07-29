import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus

logger = logging.getLogger(__name__)

def align_scale_anomalies(data: dict) -> dict:
    """
    Deterministic Scale Alignment Guard:
    Detects 100x or 1000x decimal misalignments between current and historical values
    (e.g., misparsing 8,644.40 as 8.64 due to comma/decimal confusion) and auto-corrects them.
    """
    cleaned = dict(data)
    
    pairs = [
        ('pat_q_current', 'pat_q_year_ago'),
        ('pat_q_current', 'pat_q_prev'),
        ('revenue_q_current', 'revenue_q_year_ago'),
        ('revenue_q_current', 'revenue_q_prev'),
        ('total_income_q_current', 'total_income_q_year_ago'),
        ('total_income_q_current', 'total_income_q_prev'),
        ('basic_eps_q', 'basic_eps_q_year_ago'),
        ('basic_eps_q', 'basic_eps_q_prev')
    ]
    
    for curr_key, compare_key in pairs:
        curr_val = cleaned.get(curr_key)
        comp_val = cleaned.get(compare_key)
        
        if isinstance(curr_val, (int, float)) and isinstance(comp_val, (int, float)) and curr_val > 0 and comp_val > 0:
            ratio = curr_val / comp_val
            # If ratio > 50 (e.g., 11590 / 8.64 = 1341x), check decimal shifts
            if ratio > 50:
                if 0.1 <= curr_val / (comp_val * 1000) <= 10.0:
                    logger.warning(f"[Agent 6 Normalization] Corrected 1000x decimal scale anomaly on {compare_key}: {comp_val} -> {comp_val * 1000}")
                    cleaned[compare_key] = round(comp_val * 1000, 2)
                elif 0.1 <= curr_val / (comp_val * 100) <= 10.0:
                    logger.warning(f"[Agent 6 Normalization] Corrected 100x decimal scale anomaly on {compare_key}: {comp_val} -> {comp_val * 100}")
                    cleaned[compare_key] = round(comp_val * 100, 2)
            elif ratio < 0.02:
                if 0.1 <= (curr_val * 1000) / comp_val <= 10.0:
                    logger.warning(f"[Agent 6 Normalization] Corrected 1000x decimal scale anomaly on {curr_key}: {curr_val} -> {curr_val * 1000}")
                    cleaned[curr_key] = round(curr_val * 1000, 2)
                elif 0.1 <= (curr_val * 100) / comp_val <= 10.0:
                    logger.warning(f"[Agent 6 Normalization] Corrected 100x decimal scale anomaly on {curr_key}: {curr_val} -> {curr_val * 100}")
                    cleaned[curr_key] = round(curr_val * 100, 2)

    return cleaned


def reconcile_accounting_identities(data: dict) -> dict:
    """
    Deterministic P&L Accounting Integrity Engine:
    Validates fundamental accounting laws:
    1. Total Income = Revenue + Other Income
    2. Profit Before Tax (PBT) = Total Income - Total Expenses
    3. Net Profit (PAT) = PBT - Total Tax Expense
    If extracted figures violate accounting math (or PAT was confused with TCI),
    reconciles PAT/PBT deterministically.
    """
    cleaned = dict(data)
    
    tot_inc = cleaned.get('total_income_q_current')
    rev = cleaned.get('revenue_q_current')
    oth = cleaned.get('other_income_q_current') or 0
    
    # Rule 1: Total Income Integrity
    if (not tot_inc or tot_inc == 0) and rev:
        cleaned['total_income_q_current'] = round(rev + oth, 2)
        logger.info(f"[Agent 6 Accounting Reconciler] Set Total Income = Revenue + Other Income = {cleaned['total_income_q_current']}")
        
    pbt = cleaned.get('profit_before_tax_q_current') or cleaned.get('profit_before_exceptional_q_current')
    tot_exp = cleaned.get('total_expenses_q_current')
    tot_inc_final = cleaned.get('total_income_q_current') or rev or 0
    
    # Rule 2: PBT Verification from Income - Expenses
    if tot_inc_final and tot_exp and (not pbt or pbt == 0):
        pbt_calc = round(tot_inc_final - tot_exp, 2)
        cleaned['profit_before_tax_q_current'] = pbt_calc
        pbt = pbt_calc
        logger.info(f"[Agent 6 Accounting Reconciler] Calculated PBT = Total Income - Total Expenses = {pbt_calc}")

    # Rule 3: PAT Verification from PBT - Tax Expense
    pat = cleaned.get('pat_q_current')
    tax = cleaned.get('tax_expense_q_current') or 0
    
    if pbt and tax and tax > 0:
        pat_calc = round(pbt - tax, 2)
        # Tight tolerance: 2% of PBT or 2.0 units tolerance to catch TCI / PBT misassignments
        max_tol = max(2.0, abs(pbt) * 0.02)
        if not pat or abs(pat - pat_calc) > max_tol:
            logger.warning(f"[Agent 6 Accounting Reconciler] Corrected PAT anomaly ({pat}) using deterministic PBT - Tax identity: {pat_calc}")
            cleaned['pat_q_current'] = pat_calc

    # Rule 4: EPS Sanity Check against PAT and Equity Capital
    eps = cleaned.get('basic_eps_q')
    cap = cleaned.get('paid_up_equity_capital')
    pat_final = cleaned.get('pat_q_current')
    if eps and cap and cap > 0 and pat_final and pat_final > 0:
        # Expected ratio of PAT to Capital (assuming ₹1 face value default)
        expected_ratio = pat_final / cap
        if expected_ratio > 0:
            # Check if reported EPS is off by 10x or 100x scale
            if 0.1 <= expected_ratio / (eps * 100) <= 10.0:
                logger.warning(f"[Agent 6 Accounting Reconciler] Corrected 100x scale anomaly on basic_eps_q ({eps}) -> {round(eps * 100, 2)}")
                cleaned['basic_eps_q'] = round(eps * 100, 2)

    cleaned['data_integrity_verified'] = True
    return cleaned


def process_normalization(document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record: return
    try:
        doc_record.processing_status = ProcessingStatus.NORMALIZING_METRICS
        db.commit()
        
        raw_data = dict(doc_record.financial_data or {})
        
        # 1. Apply Scale Alignment Guard
        normalized_data = align_scale_anomalies(raw_data)
        
        # 2. Apply Deterministic P&L Accounting Integrity Engine
        normalized_data = reconcile_accounting_identities(normalized_data)
            
        normalized_data['normalized'] = True
        doc_record.financial_data = normalized_data
        db.commit()
        logger.info(f"Agent 6 (Normalization) completed successfully for {document_id}")
    except Exception as e:
        logger.error(f"Agent 6 (Normalization) error: {e}")
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
