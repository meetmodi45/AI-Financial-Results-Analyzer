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
        
        # Pre-calculate FCF Yield if available
        fcf_yield_str = "Unavailable"
        if val_data and val_data.get("freeCashflow") and val_data.get("marketCap"):
            fcf = val_data.get("freeCashflow")
            mcap = val_data.get("marketCap")
            if mcap > 0:
                fcf_yield = round((fcf / mcap) * 100, 2)
                fcf_yield_str = f"{fcf_yield}%"
                val_data["fcfYield"] = fcf_yield_str

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

### 1. Current Valuation Multiples
*(List exactly these metrics as simple bullet points, do not add paragraphs here. If null, say 'Unavailable')*
* **Trailing P/E:** [Value]
* **Forward P/E:** [Value]
* **Price-to-Book (P/B):** [Value]
* **Price-to-Sales (P/S):** [Value]
* **EV/EBITDA:** [Value]
* **PEG Ratio:** [Value]
* **Free Cash Flow (FCF) Yield:** [Value]

### 2. Comprehensive Valuation Summary
*(Provide a short, punchy, bulleted summary of your analysis. Keep each point to exactly 1-2 sentences. You MUST explicitly evaluate the following based on your knowledge of the sector and the numbers provided)*:
* **Historical Context:** Are these current multiples historically high or low for a company of this nature?
* **Industry & Competitors:** How does this compare to direct peers and sector averages? Is it trading at a premium or discount?
* **Premium/Discount Justification:** Does the company actually deserve this valuation based on its business model?
* **Intrinsic Value Assumptions:** What do these multiples imply about the market's assumptions for future cash flows?

**Formatting Rules:**
- Section 1 must be a simple list of the exact numbers.
- Section 2 must be a clean, concise bulleted list. Do not write long, blocky paragraphs.
"""
