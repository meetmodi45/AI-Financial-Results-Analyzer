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
Your analysis must be institutional-grade: punchy, zero-fluff, heavily structured, and incredibly specific. 
Do not use generic statements. You must use your internal knowledge base to name specific products, specific regions, specific competitors, and exact business mechanics.

Here is the company profile to assist your analysis (supplement this with your own deep knowledge):
{profile}

Structure your exact output using the following Markdown headers and guidelines:

### 1. The Core Engine
* **What they do:** Explain the business in exactly two sentences. Be highly specific about their core offering.
* **How they make money:** Identify the primary revenue streams, key product lines, and exactly who the core customers are.
* **Value Chain:** Where do they sit in the industry value chain? Who has the power (them, suppliers, or customers)?

### 2. Business Economics
* **Capital Intensity:** Is this asset-light or capital-heavy? Name the exact assets that drive costs.
* **Pricing Power & Margins:** Do they have the ability to raise prices without losing customers? Is revenue recurring or highly cyclical?
* **Scalability:** How strong is their operating leverage as they grow?

### 3. Management & Governance
* **Skin in the Game:** Who runs the company? Is it promoter-driven or professionally managed? 
* **Capital Allocation:** Does management have a history of smart acquisitions and dividends, or do they destroy value? Name specific past moves if known.

### 4. Market Opportunity (TAM)
* **TAM & Headroom:** Is the Total Addressable Market large and growing? 
* **Growth Vectors:** Where will the next leg of growth come from (e.g., exact geographic expansion, specific new product lines)?

### 5. Durability & Risks
* **Vulnerabilities:** What are their biggest dependencies (e.g., single supplier, strict regulations, specific commodity prices)?
* **Disruption:** What technological shifts or specific industry threats could permanently damage this business?

### 6. The Institutional View
* **The Bull Case:** The top 2 reasons this business will compound earnings over the next decade.
* **The Bear Case:** The top 2 reasons this business will stagnate or deteriorate.
* **The KPI:** What is the single most important metric investors must track every quarter?
* **Market Misconception:** What is one thing retail investors completely misunderstand about this company?

**Formatting Rules (STRICTLY ENFORCED):**
- Use bullet points (`*`) for every sub-point.
- Keep paragraphs to an absolute maximum of 3 sentences.
- **LIMITED BOLDING**: You are only allowed to bold a MAXIMUM of 1 or 2 key words per bullet point. DO NOT bold entire phrases, sentences, or multiple concepts. Only bold the absolute most critical term.
- Never use introductory or concluding filler. Start immediately with the first header.
"""
