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

        raw_fd = doc_record.financial_data or {}
        
        # ── Deterministic Python Scaling Matrix ──────────────────────────────
        unit = raw_fd.get('reported_currency_unit') or ""
        unit = unit.lower()
        
        # Fallback: If unit not extracted natively, scan the raw text
        if not unit:
            extracted_text_dict = doc_record.extracted_text or {}
            full_text = " ".join(extracted_text_dict.values()).lower()
            if 'in lakh' in full_text or 'in lac' in full_text:
                unit = 'lakh'
            elif 'in million' in full_text:
                unit = 'million'
            elif 'in thousand' in full_text:
                unit = 'thousand'

        scale_factor = 1.0
        if 'lakh' in unit or 'lac' in unit:
            scale_factor = 0.01
        elif 'million' in unit:
            scale_factor = 0.1
        elif 'thousand' in unit:
            scale_factor = 0.0001

        fd = {}
        for k, v in raw_fd.items():
            if v is not None and isinstance(v, str):
                clean_v = v.replace(',', '').replace(' ', '').strip()
                if clean_v.startswith('(') and clean_v.endswith(')'):
                    clean_v = '-' + clean_v[1:-1]
                try:
                    v = float(clean_v)
                except ValueError:
                    pass

            if v is not None and isinstance(v, (int, float)):
                if k in ['basic_eps_q', 'source_page'] or k.startswith('source_page'):
                    fd[k] = v
                else:
                    fd[k] = v * scale_factor
            else:
                fd[k] = v

        # ── Profit & Loss Metrics ─────────────────────────────────────────────
        ti_q_curr = fd.get('total_income_q_current') or 0
        ti_q_prev = fd.get('total_income_q_prev') or 0
        ti_q_yoy  = fd.get('total_income_q_year_ago') or 0

        pat_q_curr = fd.get('pat_q_current') or 0
        pat_q_prev = fd.get('pat_q_prev') or 0
        pat_q_yoy  = fd.get('pat_q_year_ago') or 0

        ti_fy_curr = fd.get('total_income_fy_current') or 0
        pat_fy_curr = fd.get('pat_fy_current') or 0

        pbt_q_curr  = fd.get('profit_before_tax_q_current') or 0
        pbt_fy_curr = fd.get('profit_before_tax_fy_current') or 0

        # Proxy EBITDA: PBT + simple assumption if D&A/Interest not explicitly mapped
        # In a deep model, we'd extract Depreciation & Interest explicitly
        ebitda_q  = pbt_q_curr * 1.15
        ebitda_fy = pbt_fy_curr * 1.15
        
        # EPS Extraction
        eps_curr = fd.get('basic_eps_q')
        eps_prev = fd.get('basic_eps_q_prev')
        eps_yoy = fd.get('basic_eps_q_year_ago')

        results = {
            # Growth %
            'qoq_growth':      safe_growth(ti_q_curr, ti_q_prev),
            'yoy_growth':      safe_growth(ti_q_curr, ti_q_yoy),
            'pat_qoq':         safe_growth(pat_q_curr, pat_q_prev),
            'pat_yoy':         safe_growth(pat_q_curr, pat_q_yoy),
            'eps_qoq':         safe_growth(eps_curr, eps_prev),
            'eps_yoy':         safe_growth(eps_curr, eps_yoy),

            # Margins
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
            'basic_eps':           eps_curr,
        }
        
        # ── Balance Sheet Metrics ─────────────────────────────────────────────
        # Current Year
        nc_borrow = fd.get('non_current_borrowings') or 0
        c_borrow  = fd.get('current_borrowings') or 0
        total_borrowings = nc_borrow + c_borrow

        cash_eq   = fd.get('cash_equivalents') or 0
        bank_bal  = fd.get('bank_balances') or 0
        cash_and_bank = cash_eq + bank_bal

        net_debt = total_borrowings - cash_and_bank

        tc_assets      = fd.get('total_current_assets')
        tc_liabilities = fd.get('total_current_liabilities')
        current_ratio  = None
        if tc_assets is not None and tc_liabilities is not None and tc_liabilities != 0:
            current_ratio = round(tc_assets / tc_liabilities, 2)

        # Previous Year
        nc_borrow_prev = fd.get('non_current_borrowings_prev') or 0
        c_borrow_prev  = fd.get('current_borrowings_prev') or 0
        total_borrowings_prev = nc_borrow_prev + c_borrow_prev

        cash_eq_prev   = fd.get('cash_equivalents_prev') or 0
        bank_bal_prev  = fd.get('bank_balances_prev') or 0
        cash_and_bank_prev = cash_eq_prev + bank_bal_prev

        net_debt_prev = total_borrowings_prev - cash_and_bank_prev

        tc_assets_prev      = fd.get('total_current_assets_prev')
        tc_liabilities_prev = fd.get('total_current_liabilities_prev')
        current_ratio_prev  = None
        if tc_assets_prev is not None and tc_liabilities_prev is not None and tc_liabilities_prev != 0:
            current_ratio_prev = round(tc_assets_prev / tc_liabilities_prev, 2)

        if fd.get('non_current_borrowings') is not None or fd.get('current_borrowings') is not None:
            results['total_borrowings_cr'] = total_borrowings
            results['net_debt_cr'] = net_debt
            if fd.get('non_current_borrowings_prev') is not None or fd.get('current_borrowings_prev') is not None:
                results['total_borrowings_cr_prev'] = total_borrowings_prev
                results['net_debt_cr_prev'] = net_debt_prev

        results['current_ratio'] = current_ratio
        results['current_ratio_prev'] = current_ratio_prev
        
        results['cwip_cr'] = fd.get('cwip')
        results['cwip_cr_prev'] = fd.get('cwip_prev')
        
        results['trade_receivables_cr'] = fd.get('trade_receivables')
        results['trade_receivables_cr_prev'] = fd.get('trade_receivables_prev')
        
        results['inventories_cr'] = fd.get('inventories')
        results['inventories_cr_prev'] = fd.get('inventories_prev')

        # ── Operational Cash Flow Speeds (Days) ───────────────────────────────
        rev_curr = fd.get('revenue_fy_current') or fd.get('total_income_fy_current') or ((fd.get('revenue_q_current') or fd.get('total_income_q_current') or 0) * 4)
        rev_prev = fd.get('revenue_fy_prev') or fd.get('total_income_fy_prev') or ((fd.get('revenue_q_prev') or fd.get('total_income_q_prev') or 0) * 4)

        if rev_curr and rev_curr > 0:
            if fd.get('inventories') is not None:
                results['inventory_days'] = (fd.get('inventories') / rev_curr) * 365
            if fd.get('trade_receivables') is not None:
                results['debtor_days'] = (fd.get('trade_receivables') / rev_curr) * 365
                
        if rev_prev and rev_prev > 0:
            if fd.get('inventories_prev') is not None:
                results['inventory_days_ly'] = (fd.get('inventories_prev') / rev_prev) * 365
            if fd.get('trade_receivables_prev') is not None:
                results['debtor_days_ly'] = (fd.get('trade_receivables_prev') / rev_prev) * 365

        # ── Cash Flow Statement Metrics ───────────────────────────────────────
        ocf = fd.get('operating_cash_flow')
        capex = fd.get('capex')
        fcf = None
        if ocf is not None and capex is not None:
            fcf = ocf - abs(capex)

        ocf_prev = fd.get('operating_cash_flow_prev')
        capex_prev = fd.get('capex_prev')
        fcf_prev = None
        if ocf_prev is not None and capex_prev is not None:
            fcf_prev = ocf_prev - abs(capex_prev)

        results['operating_cash_flow_cr'] = ocf
        results['operating_profit_pre_wc_cr'] = fd.get('operating_profit_pre_wc')
        results['investing_cash_flow_cr'] = fd.get('investing_cash_flow')
        results['capex_cr'] = capex
        results['financing_cash_flow_cr'] = fd.get('financing_cash_flow')
        results['proceeds_borrowings_cr'] = fd.get('proceeds_borrowings')
        results['repayment_borrowings_cr'] = fd.get('repayment_borrowings')
        results['free_cash_flow_cr'] = fcf

        results['operating_cash_flow_cr_prev'] = ocf_prev
        results['operating_profit_pre_wc_cr_prev'] = fd.get('operating_profit_pre_wc_prev')
        results['investing_cash_flow_cr_prev'] = fd.get('investing_cash_flow_prev')
        results['capex_cr_prev'] = capex_prev
        results['financing_cash_flow_cr_prev'] = fd.get('financing_cash_flow_prev')
        results['proceeds_borrowings_cr_prev'] = fd.get('proceeds_borrowings_prev')
        results['repayment_borrowings_cr_prev'] = fd.get('repayment_borrowings_prev')
        results['free_cash_flow_cr_prev'] = fcf_prev

        # Remove None values
        results = {k: v for k, v in results.items() if v is not None}
        logger.info(f"[Agent 7] Analysis: {results}")

        doc_record.analysis_results = results
        doc_record.financial_data = fd
        db.commit()
        logger.info(f"Agent 7 (Financial Analysis) completed for {document_id}")

    except Exception as e:
        logger.error(f"[Agent 7] Error: {e}", exc_info=True)
        doc_record.processing_status = ProcessingStatus.FAILED
        doc_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
