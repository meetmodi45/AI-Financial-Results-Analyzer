import json
from app.agents.base_agent import BaseResearchAgent
from app.services.fmp_client import get_company_profile, get_key_metrics, fetch_indianapi_data
from sqlalchemy.orm import Session
import asyncio

class BusinessAgent(BaseResearchAgent):
    
    async def fetch_data(self, symbol: str, db: Session) -> dict:
        profile, metrics, raw_data = await asyncio.gather(
            get_company_profile(symbol, db),
            get_key_metrics(symbol, db),
            fetch_indianapi_data(symbol, db)
        )
        
        recent_metrics = metrics[0] if metrics and isinstance(metrics, list) else {}
        
        # Extract shareholding and news
        shareholding = []
        news = []
        if raw_data:
            shareholding = raw_data.get("shareholding") or []
            news = raw_data.get("recentNews") or []
            
        return {
            "profile": json.dumps(profile[0] if profile else {}, indent=2),
            "key_metrics": json.dumps(recent_metrics, indent=2),
            "shareholding": json.dumps(shareholding, indent=2),
            "news": json.dumps(news[:5], indent=2)
        }

    def get_prompt_template(self) -> str:
        return """Act like an elite equity research analyst and long-term investor. 

Perform a razor-sharp, highly concise deep dive on the business model of {symbol}. 
Your analysis must be institutional-grade: punchy, zero-fluff, heavily structured, and incredibly specific. 
Do not use generic statements. You must use your internal knowledge base to name specific products, specific regions, specific competitors, and exact business mechanics.

Here is the raw data to assist your analysis:
Company Profile: {profile}
Key Performance Metrics (margins, growth, debt): {key_metrics}
Shareholding Structure: {shareholding}
Recent News: {news}

Structure your exact output using the following Markdown headers and guidelines:

### 1. The Core Engine
* **What they do:** Explain the business in exactly two sentences. Be highly specific about their core offering.
* **Revenue Visibility:** Detail how income is contracted (e.g., multi-year order book, recurring subscriptions, or transactional spot-market sales) and the predictability of their sales pipeline.
* **Backward Integration:** Detail the degree of in-house manufacturing (e.g., self-manufacturing raw components vs. raw outsourcing) and how this controls project margins or timeline risks.
* **Value Chain & Power:** Where do they sit in the industry value chain? Who holds the structural bargaining power (them, their raw material suppliers, or their end customers)?

### 2. Distribution & Go-To-Market (GTM)
* **Channel Strategy:** How does the product actually reach the buyer? Detail their specific reliance on direct enterprise sales teams, channel partners, retail distributors, or direct-to-consumer platforms.
* **Customer Acquisition:** How expensive or difficult is it to acquire a new customer? Detail the friction involved in their sales cycle.

### 3. Business Economics & Cost Anchors
* **Capital Intensity:** Is this asset-light or capital-heavy? Name the exact assets or infrastructure that drive capital expenditure.
* **Cost Anchors & Input Risks:** Identify the top 3 raw inputs or operational expenses that dictate their margins, and state if they have pricing power to pass on cost spikes.
* **Geographic Execution Mix:** Break down the revenue and order book split between domestic Indian projects and international exposure, identifying specific risks (e.g., currency hedging, cross-border logistics, political climates).
* **Working Capital Dynamics:** Explain their cash conversion profile. Is cash heavily locked up in receivables and inventory, or do they operate on upfront customer advances?

### 4. Client Concentration (The Whale Risk)
* **Revenue Fragmentation:** Is the revenue base safely diversified across thousands of buyers, or is it dangerously concentrated among a few massive clients/government entities?
* **Bargaining Leverage:** If they rely on a few "whales," do these key clients have the power to squeeze the company on pricing and payment terms?

### 5. Management & Governance
* **Skin in the Game:** Who runs the company? Is it promoter-driven or professionally managed? 
* **Capital Allocation:** Does management have a history of smart acquisitions and dividends, or do they destroy value? Name specific past moves if known.

### 6. Market Opportunity (TAM)
* **TAM & Headroom:** Is the Total Addressable Market large and growing? 
* **Growth Vectors:** Where will the next leg of growth come from (e.g., exact geographic expansion, specific new product lines)?

### 7. Durability & Risks
* **Operational Choke Point:** What is the primary operational bottleneck or asset constraint (e.g., factory capacity utilization, execution talent, regulatory clearance) limiting rapid scaling?
* **Regulatory & Macro Dependency:** Does this business rely heavily on government subsidies (e.g., PLI schemes), protective import tariffs, specific regulatory clearances, or is it highly sensitive to interest rate cycles?
* **Disruption & Vulnerabilities:** What specific technological shifts or structural threats could permanently damage this business?

### 8. The Institutional View
* **The Bull Case:** The top 2 reasons this business will compound earnings over the next decade.
* **The Bear Case:** The top 2 reasons this business will stagnate or deteriorate.
* **The Ultimate KPI:** What is the single most critical operational metric (e.g., Order-to-Bill ratio, ARPU, Capacity Utilization) investors must track every single quarter to see if the engine is running smoothly?
* **Market Misconception:** What is one thing retail investors completely misunderstand about this company?

**Formatting Rules (STRICTLY ENFORCED):**
- Use bullet points (`*`) for every sub-point.
- Keep paragraphs to an absolute maximum of 3 sentences.
- **LIMITED BOLDING**: You are only allowed to bold a MAXIMUM of 1 or 2 key words per bullet point. DO NOT bold entire phrases, sentences, or multiple concepts. Only bold the absolute most critical term.
- Never use introductory or concluding filler. Start immediately with the first header.
"""
