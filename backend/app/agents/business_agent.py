import json
from app.agents.base_agent import BaseResearchAgent
from app.services.fmp_client import get_company_profile, get_income_statement
from sqlalchemy.orm import Session
import asyncio

class BusinessAgent(BaseResearchAgent):
    
    async def fetch_data(self, symbol: str, db: Session) -> dict:
        profile = await get_company_profile(symbol, db)
        
        return {
            "profile": json.dumps(profile[0] if profile else {})
        }

    def get_prompt_template(self) -> str:
        return """Act like an elite equity research analyst and long-term investor. 

Perform a razor-sharp, highly concise deep dive on the business model of {symbol}. 
Your analysis must be institutional-grade: punchy, zero-fluff, and heavily structured. 
Do not repeat yourself. If a concept is covered in one section, do not bring it up again.

Here is the company profile to assist your analysis:
{profile}

Structure your exact output using the following Markdown headers and guidelines:

### 1. The Core Engine
* **What they do:** Explain the business in exactly two sentences.
* **How they make money:** Identify the primary revenue streams and who the core customers are.
* **Value Chain:** Where do they sit in the industry value chain? Who has the power (them, suppliers, or customers)?

### 2. Business Economics
* **Capital Intensity:** Is this asset-light (software, services) or capital-heavy (manufacturing, infrastructure)? 
* **Pricing Power & Margins:** Do they have the ability to raise prices without losing customers? Is revenue recurring or highly cyclical?
* **Scalability:** How strong is their operating leverage as they grow?

### 3. Management & Governance
* **Skin in the Game:** Who runs the company? Is it promoter-driven or professionally managed? Do they have strong alignment with minority shareholders?
* **Capital Allocation:** Does management have a history of smart acquisitions and dividends, or do they destroy value with poor investments?

### 4. Market Opportunity (TAM)
* **TAM & Headroom:** Is the Total Addressable Market large and growing? Is the company's current market penetration high (saturated) or low (massive runway)?
* **Growth Vectors:** Where will the next leg of growth come from (e.g., geographic expansion, new product lines, premiumization)?

### 5. Durability & Risks
* **Vulnerabilities:** What are their biggest dependencies (e.g., single supplier, strict regulations, commodity prices)?
* **Disruption:** What technological shifts (AI, automation) or industry threats could permanently damage this business?

### 6. The Institutional View
* **The Bull Case:** The top 2 reasons this business will compound earnings over the next decade.
* **The Bear Case:** The top 2 reasons this business will stagnate or deteriorate.
* **The KPI:** What is the single most important metric investors must track every quarter to know if the thesis is intact?
* **Market Misconception:** What is one thing retail investors completely misunderstand about this company?

**Formatting Rules:**
- Use bullet points (`*`) for every sub-point.
- Keep paragraphs to an absolute maximum of 3 sentences. 
- Use **bold text** to highlight key terms.
- Never use introductory or concluding filler (e.g., "Here is the analysis of...", "In conclusion..."). Start immediately with the first header.
"""
