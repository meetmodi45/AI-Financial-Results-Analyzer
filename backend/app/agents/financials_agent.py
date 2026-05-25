import json
from app.agents.base_agent import BaseResearchAgent
from app.services.fmp_client import get_company_profile, get_income_statement, get_balance_sheet, get_cash_flow_statement
from sqlalchemy.orm import Session
import asyncio

class FinancialsAgent(BaseResearchAgent):
    
    async def fetch_data(self, symbol: str, db: Session) -> dict:
        profile, income_stmt, balance_sheet, cash_flow = await asyncio.gather(
            get_company_profile(symbol, db),
            get_income_statement(symbol, db),
            get_balance_sheet(symbol, db),
            get_cash_flow_statement(symbol, db)
        )
        
        # Pre-calculate YoY and QoQ so the LLM doesn't hallucinate math
        pre_calc = []
        try:
            if income_stmt.get("annual") and len(income_stmt["annual"]) >= 2:
                curr_rev = income_stmt["annual"][0].get("Total Revenue", 0)
                prev_rev = income_stmt["annual"][1].get("Total Revenue", 0)
                if prev_rev:
                    yoy = round(((curr_rev - prev_rev) / abs(prev_rev)) * 100, 2)
                    pre_calc.append(f"- Annual YoY Revenue Growth: {yoy}%")
                    
                curr_ni = income_stmt["annual"][0].get("Net Income", 0)
                prev_ni = income_stmt["annual"][1].get("Net Income", 0)
                if prev_ni:
                    yoy_ni = round(((curr_ni - prev_ni) / abs(prev_ni)) * 100, 2)
                    pre_calc.append(f"- Annual YoY Net Income Growth: {yoy_ni}%")

            if income_stmt.get("quarterly") and len(income_stmt["quarterly"]) >= 2:
                curr_rev_q = income_stmt["quarterly"][0].get("Total Revenue", 0)
                prev_rev_q = income_stmt["quarterly"][1].get("Total Revenue", 0)
                if prev_rev_q:
                    qoq = round(((curr_rev_q - prev_rev_q) / abs(prev_rev_q)) * 100, 2)
                    pre_calc.append(f"- Quarterly QoQ Revenue Growth: {qoq}%")
                    
                curr_ni_q = income_stmt["quarterly"][0].get("Net Income", 0)
                prev_ni_q = income_stmt["quarterly"][1].get("Net Income", 0)
                if prev_ni_q:
                    qoq_ni = round(((curr_ni_q - prev_ni_q) / abs(prev_ni_q)) * 100, 2)
                    pre_calc.append(f"- Quarterly QoQ Net Income Growth: {qoq_ni}%")
        except:
            pass
            
        pre_calc_str = "\n".join(pre_calc) if pre_calc else "Pre-calculated metrics unavailable."
        
        return {
            "profile": json.dumps(profile[0] if profile else {}),
            "income_statement": json.dumps(income_stmt),
            "balance_sheet": json.dumps(balance_sheet),
            "cash_flow": json.dumps(cash_flow),
            "pre_calc_str": pre_calc_str
        }

    def get_prompt_template(self) -> str:
        return """Act like a top-tier forensic equity analyst and institutional investor specializing in financial statement analysis, earnings quality, and forensic accounting.

Perform a deep financial and fundamental analysis of {symbol} using both Annual and Quarterly data. 
You are hunting for both compounding strengths and hidden red flags. Look beyond headline growth.

Here is the extracted core financial data:
Company Profile: {profile}
**PRE-CALCULATED FACTS (DO NOT CALCULATE GROWTH YOURSELF. USE THESE EXACT NUMBERS):**
{pre_calc_str}

Income Statement: {income_statement}
Balance Sheet: {balance_sheet}
Cash Flow Statement: {cash_flow}

Structure your exact output using the following Markdown headers and guidelines:

### 1. Growth & Profitability Trends
* **YoY & QoQ Growth:** Explicitly state the YoY and QoQ revenue and profit growth using the PRE-CALCULATED FACTS provided above. Based on those precise numbers, is growth accelerating or decelerating?
* **Margin Trajectory:** Are Gross and Operating margins stable, expanding, or compressing over the quarters? Is the core business actually profitable?
* **R&D & Reinvestment:** Is the company investing heavily in Research & Development to fuel future growth, or starving the business?

### 2. Balance Sheet & Solvency
* **Debt Load:** What is their Net Debt position? Are they over-leveraged compared to their equity base?
* **Liquidity:** Do they have enough cash on hand to survive a severe recession?
* **Inventory & Working Capital:** Is inventory piling up faster than revenue growth (a major red flag for demand issues)?

### 3. Cash Flow Quality & Capital Allocation
* **Earnings vs Cash:** Do their Reported Profits actually match their Operating Cash Flow, or is it an accounting illusion?
* **Free Cash Flow:** Are they generating consistent Free Cash Flow after Capex?
* **Shareholder Returns:** What is their track record on paying Dividends? Is the dividend safely covered by Free Cash Flow?

### 4. The Forensic Verdict
* **Suspicious Flags:** Are there massive spikes in "Other Income" hiding a declining core business? Are there any worrying accounting trends?
* **The Bottom Line:** Is this company becoming more financially efficient or structurally weaker over time?
* **Valuation Justification:** Does the fundamental financial quality justify holding this stock long-term?

**Formatting Rules:**
- Use bullet points (`*`) for every sub-point.
- Keep paragraphs to an absolute maximum of 3 sentences. 
- Use **bold text** to highlight key terms and metric names.
- Never use introductory or concluding filler. Start immediately with the first header.
"""
