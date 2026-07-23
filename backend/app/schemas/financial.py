import re
import json
from pydantic import BaseModel, Field, field_validator

class FinancialRawSchema(BaseModel):
    # Metadata
    reported_currency_unit: str = Field(
        default="Not specified",
        description="The exact scaling metric written on the page text header (e.g., 'Lakhs', 'Millions', 'Crores'). Extract verbatim."
    )
    source_page_indices: list[int] = Field(
        default_factory=list, 
        description="List of page indices where the data was found."
    )
    extraction_confidence: str = Field(
        default="High",
        description="Your confidence in the extraction quality: 'High', 'Medium', or 'Low'."
    )

    @field_validator("*", mode="before")
    def clean_numeric(cls, v, info):
        if info.field_name in ("reported_currency_unit", "extraction_confidence"):
            return str(v) if isinstance(v, (int, float)) else v
        if info.field_name == "source_page_indices":
            if isinstance(v, str):
                try:
                    parsed_list = json.loads(v)
                    if isinstance(parsed_list, list):
                        return [int(x) for x in parsed_list if str(x).strip().lstrip('-').isdigit()]
                except Exception:
                    pass
                return [int(x) for x in re.findall(r'\d+', v)]
            if isinstance(v, (int, float)):
                return [int(v)]
            return v if isinstance(v, list) else []
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str or v_str.lower() in ("n/a", "none", "null", "-", "nil", "--", "nan"):
                return None
            if v_str.startswith("(") and v_str.endswith(")"):
                v_str = "-" + v_str[1:-1]
            v_str = v_str.replace(",", "").replace(" ", "").replace("\u200b", "")
            try:
                return float(v_str)
            except ValueError:
                return None
        return v

    # ---------------------------------------------------------
    # P&L Group
    # ---------------------------------------------------------
    # Current Quarter (Index 0)
    revenue_q_current: str | float | None = Field(default=None, description="Revenue from Operations / Net Sales for current quarter.")
    total_income_q_current: str | float | None = Field(default=None, description="Total Income / Total Revenue for current quarter.")
    profit_before_exceptional_q_current: str | float | None = Field(default=None, description="Profit before exceptional items and tax for current quarter.")
    profit_before_tax_q_current: str | float | None = Field(default=None, description="Profit Before Tax (PBT) for current quarter. Extract 'Profit before tax' or 'Profit before exceptional items and tax'.")
    pat_q_current: str | float | None = Field(default=None, description="Profit After Tax (PAT) / Net Profit for current quarter. Extract 'Profit after tax' or 'Profit for the period/year' or 'Net profit for the period'. DO NOT extract Profit Before Tax here.")
    other_income_q_current: str | float | None = Field(default=None, description="Other Income for current quarter.")
    total_expenses_q_current: str | float | None = Field(default=None, description="Total Expenses for current quarter.")
    tax_expense_q_current: str | float | None = Field(default=None, description="Total Tax Expense for current quarter.")
    finance_costs_q_current: str | float | None = Field(default=None, description="Finance costs / Interest expense for current quarter.")
    depreciation_q_current: str | float | None = Field(default=None, description="Depreciation and amortisation expense for current quarter.")
    basic_eps_q: str | float | None = Field(default=None, description="Basic Earnings Per Share (EPS) for current quarter.")

    # Previous Quarter (Index 1)
    revenue_q_prev: str | float | None = Field(default=None, description="Revenue from Operations for previous quarter.")
    total_income_q_prev: str | float | None = Field(default=None, description="Total Income for previous quarter.")
    profit_before_exceptional_q_prev: str | float | None = Field(default=None, description="Profit before exceptional items and tax for previous quarter.")
    profit_before_tax_q_prev: str | float | None = Field(default=None, description="Profit Before Tax (PBT) for previous quarter.")
    pat_q_prev: str | float | None = Field(default=None, description="Profit After Tax (PAT) / Net Profit for previous quarter.")
    basic_eps_q_prev: str | float | None = Field(default=None, description="Basic EPS for previous quarter.")

    # Quarter Year-Ago (Index 2)
    revenue_q_year_ago: str | float | None = Field(default=None, description="Revenue from Operations for year-ago quarter.")
    total_income_q_year_ago: str | float | None = Field(default=None, description="Total Income for year-ago quarter.")
    pat_q_year_ago: str | float | None = Field(default=None, description="Profit After Tax (PAT) for year-ago quarter.")
    basic_eps_q_year_ago: str | float | None = Field(default=None, description="Basic EPS for year-ago quarter.")

    # Full Year Current (Index 3)
    revenue_fy_current: str | float | None = Field(default=None, description="Revenue from Operations for full current FY.")
    total_income_fy_current: str | float | None = Field(default=None, description="Total Income for full current FY.")
    profit_before_exceptional_fy_current: str | float | None = Field(default=None, description="Profit before exceptional items and tax for full current FY.")
    profit_before_tax_fy_current: str | float | None = Field(default=None, description="Profit Before Tax (PBT) for full current FY.")
    pat_fy_current: str | float | None = Field(default=None, description="Profit After Tax (PAT) / Net Profit for full current FY.")

    # Full Year Previous (Index 4)
    revenue_fy_prev: str | float | None = Field(default=None, description="Revenue from Operations for full previous FY.")
    total_income_fy_prev: str | float | None = Field(default=None, description="Total Income for full previous FY.")
    profit_before_exceptional_fy_prev: str | float | None = Field(default=None, description="Profit before exceptional items and tax for full previous FY.")
    profit_before_tax_fy_prev: str | float | None = Field(default=None, description="Profit Before Tax (PBT) for full previous FY.")
    pat_fy_prev: str | float | None = Field(default=None, description="Profit After Tax (PAT) / Net Profit for full previous FY.")

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
