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
    revenue_q_current: str | float | None = None
    total_income_q_current: str | float | None = None
    profit_before_exceptional_q_current: str | float | None = None
    profit_before_tax_q_current: str | float | None = None
    pat_q_current: str | float | None = None
    basic_eps_q: str | float | None = None

    # Previous Quarter (Index 1)
    revenue_q_prev: str | float | None = None
    total_income_q_prev: str | float | None = None
    profit_before_exceptional_q_prev: str | float | None = None
    profit_before_tax_q_prev: str | float | None = None
    pat_q_prev: str | float | None = None
    basic_eps_q_prev: str | float | None = None

    # Quarter Year-Ago (Index 2)
    revenue_q_year_ago: str | float | None = None
    total_income_q_year_ago: str | float | None = None
    pat_q_year_ago: str | float | None = None
    basic_eps_q_year_ago: str | float | None = None

    # Full Year Current (Index 3)
    revenue_fy_current: str | float | None = None
    total_income_fy_current: str | float | None = None
    profit_before_exceptional_fy_current: str | float | None = None
    profit_before_tax_fy_current: str | float | None = None
    pat_fy_current: str | float | None = None

    # Full Year Previous (Index 4)
    revenue_fy_prev: str | float | None = None
    total_income_fy_prev: str | float | None = None
    profit_before_exceptional_fy_prev: str | float | None = None
    profit_before_tax_fy_prev: str | float | None = None
    pat_fy_prev: str | float | None = None

    # ---------------------------------------------------------
    # Balance Sheet Group
    # ---------------------------------------------------------
    # Current Period (Index 0)
    non_current_borrowings: str | float | None = None
    current_borrowings: str | float | None = None
    cash_equivalents: str | float | None = None
    bank_balances: str | float | None = None
    cwip: str | float | None = None
    trade_receivables: str | float | None = None
    inventories: str | float | None = None
    total_current_assets: str | float | None = None
    total_current_liabilities: str | float | None = None

    # Previous Period (Index 1)
    non_current_borrowings_prev: str | float | None = None
    current_borrowings_prev: str | float | None = None
    cash_equivalents_prev: str | float | None = None
    bank_balances_prev: str | float | None = None
    cwip_prev: str | float | None = None
    trade_receivables_prev: str | float | None = None
    inventories_prev: str | float | None = None
    total_current_assets_prev: str | float | None = None
    total_current_liabilities_prev: str | float | None = None

    # ---------------------------------------------------------
    # Cash Flow Group
    # ---------------------------------------------------------
    # Current Period (Index 0)
    operating_cash_flow: str | float | None = None
    operating_profit_pre_wc: str | float | None = None
    investing_cash_flow: str | float | None = None
    capex: str | float | None = None
    financing_cash_flow: str | float | None = None
    proceeds_borrowings: str | float | None = None
    repayment_borrowings: str | float | None = None

    # Previous Period (Index 1)
    operating_cash_flow_prev: str | float | None = None
    operating_profit_pre_wc_prev: str | float | None = None
    investing_cash_flow_prev: str | float | None = None
    capex_prev: str | float | None = None
    financing_cash_flow_prev: str | float | None = None
    proceeds_borrowings_prev: str | float | None = None
    repayment_borrowings_prev: str | float | None = None
