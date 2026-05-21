from pydantic import BaseModel, Field

class FinancialRawSchema(BaseModel):
    # Metadata
    reported_currency_unit: str = Field(
        description="The exact scaling metric written on the page text header (e.g., 'Lakhs', 'Millions', 'Crores'). Extract verbatim."
    )
    source_page_indices: list[int] = Field(
        default_factory=list, 
        description="List of page indices where the data was found."
    )
    extraction_confidence: str = Field(
        description="Your confidence in the extraction quality: 'High', 'Medium', or 'Low'."
    )

    # ---------------------------------------------------------
    # P&L Group
    # ---------------------------------------------------------
    # Current Quarter (Index 0)
    revenue_q_current: float | None = None
    total_income_q_current: float | None = None
    profit_before_exceptional_q_current: float | None = None
    profit_before_tax_q_current: float | None = None
    pat_q_current: float | None = None
    basic_eps_q: float | None = None

    # Previous Quarter (Index 1)
    revenue_q_prev: float | None = None
    total_income_q_prev: float | None = None
    profit_before_exceptional_q_prev: float | None = None
    profit_before_tax_q_prev: float | None = None
    pat_q_prev: float | None = None

    # Quarter Year-Ago (Index 2)
    revenue_q_year_ago: float | None = None
    total_income_q_year_ago: float | None = None
    pat_q_year_ago: float | None = None

    # Full Year Current (Index 3)
    revenue_fy_current: float | None = None
    total_income_fy_current: float | None = None
    profit_before_exceptional_fy_current: float | None = None
    profit_before_tax_fy_current: float | None = None
    pat_fy_current: float | None = None

    # Full Year Previous (Index 4)
    revenue_fy_prev: float | None = None
    total_income_fy_prev: float | None = None
    profit_before_exceptional_fy_prev: float | None = None
    profit_before_tax_fy_prev: float | None = None
    pat_fy_prev: float | None = None

    # ---------------------------------------------------------
    # Balance Sheet Group
    # ---------------------------------------------------------
    # Current Period (Index 0)
    non_current_borrowings: float | None = None
    current_borrowings: float | None = None
    cash_equivalents: float | None = None
    bank_balances: float | None = None
    cwip: float | None = None
    trade_receivables: float | None = None
    inventories: float | None = None
    total_current_assets: float | None = None
    total_current_liabilities: float | None = None

    # Previous Period (Index 1)
    non_current_borrowings_prev: float | None = None
    current_borrowings_prev: float | None = None
    cash_equivalents_prev: float | None = None
    bank_balances_prev: float | None = None
    cwip_prev: float | None = None
    trade_receivables_prev: float | None = None
    inventories_prev: float | None = None
    total_current_assets_prev: float | None = None
    total_current_liabilities_prev: float | None = None

    # ---------------------------------------------------------
    # Cash Flow Group
    # ---------------------------------------------------------
    # Current Period (Index 0)
    operating_cash_flow: float | None = None
    operating_profit_pre_wc: float | None = None
    investing_cash_flow: float | None = None
    capex: float | None = None
    financing_cash_flow: float | None = None
    proceeds_borrowings: float | None = None
    repayment_borrowings: float | None = None

    # Previous Period (Index 1)
    operating_cash_flow_prev: float | None = None
    operating_profit_pre_wc_prev: float | None = None
    investing_cash_flow_prev: float | None = None
    capex_prev: float | None = None
    financing_cash_flow_prev: float | None = None
    proceeds_borrowings_prev: float | None = None
    repayment_borrowings_prev: float | None = None
