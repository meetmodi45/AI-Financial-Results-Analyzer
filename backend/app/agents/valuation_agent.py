import json
from app.agents.base_agent import BaseResearchAgent
from app.services.fmp_client import get_company_profile, get_valuation_data
from sqlalchemy.orm import Session
import asyncio

class ValuationAgent(BaseResearchAgent):
    
    async def fetch_data(self, symbol: str, db: Session) -> dict:
        profile, val_data = await asyncio.gather(
            get_company_profile(symbol, db),
            get_valuation_data(symbol, db)
        )
        
        if val_data:
            # Pre-calculate FCF Yield if available
            fcf = val_data.get("freeCashflow")
            mcap = val_data.get("marketCap")
            if fcf is not None and mcap is not None and mcap > 0:
                fcf_yield = round((fcf / mcap) * 100, 2)
                val_data["fcfYield"] = f"{fcf_yield}%"
            else:
                val_data["fcfYield"] = "Unavailable"

            def format_currency(val):
                if val is None: return "Unavailable"
                try:
                    cr_val = float(val) / 10000000
                    return f"₹ {cr_val:,.2f} Cr."
                except:
                    return "Unavailable"

            def format_number(val):
                if val is None: return "Unavailable"
                try:
                    return f"{float(val):.2f}"
                except:
                    return "Unavailable"
            
            def format_percentage(val):
                if val is None: return "Unavailable"
                try:
                    return f"{float(val) * 100:.2f}%"
                except:
                    return "Unavailable"

            # Format Market Cap and Free Cash Flow as Crores
            val_data['marketCap'] = format_currency(val_data.get('marketCap'))
            val_data['freeCashflow'] = format_currency(val_data.get('freeCashflow'))
            
            # Format Percentages
            for key in ['dividendYield', 'returnOnEquity', 'returnOnAssets', 'promoterHolding']:
                val_data[key] = format_percentage(val_data.get(key))
                
            # Format standard decimals
            for key in ['currentPrice', 'trailingPE', 'forwardPE', 'pegRatio', 'priceToBook', 'priceToSales', 'enterpriseToEbitda', 'debtToEquity', 'trailingEps', 'forwardEps']:
                val_data[key] = format_number(val_data.get(key))

        return {
            "profile": json.dumps(profile[0] if profile else {}),
            "val_data": json.dumps(val_data)
        }

    def get_prompt_template(self) -> str:
        return """Act like a strict quantitative equity analyst evaluating valuation multiples.

Perform a deep valuation analysis of {symbol}. 

Here is the extracted core mathematical data:
Company Profile (for Sector Context): {profile}
Exact Multiples: {val_data}

Structure your exact output strictly as follows:

### 1. Current Valuation Multiples & Key Metrics
*(List exactly these metrics as simple bullet points, do not add paragraphs here. If null, say 'Unavailable')*
* **Current Price:** [Value]
* **Market Cap:** [Value]
* **Trailing P/E:** [Value]
* **Forward P/E:** [Value]
* **Price-to-Book (P/B):** [Value]
* **Price-to-Sales (P/S):** [Value]
* **EV/EBITDA:** [Value]
* **PEG Ratio:** [Value]
* **Free Cash Flow (FCF) Yield:** [Value]
* **Return on Equity (ROE):** [Value]
* **Return on Assets (ROA / ROCE proxy):** [Value]
* **Debt to Equity:** [Value]
* **Trailing EPS:** [Value]
* **Forward EPS:** [Value]
* **Promoter Holding:** [Value]

### 2. Comprehensive Valuation Summary
*(Provide a short, punchy, bulleted summary of your analysis. Keep each point to exactly 1-2 sentences. You MUST explicitly evaluate the following based on your knowledge of the sector and the numbers provided)*:
* **Historical Context:** Are these current multiples historically high or low for a company of this nature?
* **Industry & Competitors:** How does this compare to direct peers and sector averages? Is it trading at a premium or discount?
* **Financial Health & Capital Structure:** What do the debt load and return metrics (ROE/ROCE) suggest about their capital efficiency?
* **Premium/Discount Justification:** Does the company actually deserve this valuation based on its business model and promoter alignment?
* **Intrinsic Value Assumptions:** What do these multiples imply about the market's assumptions for future cash flows?

**Formatting Rules:**
- Section 1 must be a simple list of the exact numbers.
- Section 2 must be a clean, concise bulleted list. Do not write long, blocky paragraphs.
"""
