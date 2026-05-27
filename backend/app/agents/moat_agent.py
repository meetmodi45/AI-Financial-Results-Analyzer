import json
from app.agents.base_agent import BaseResearchAgent
from app.services.fmp_client import get_company_profile, get_key_metrics, fetch_indianapi_data
from sqlalchemy.orm import Session
import asyncio

class MoatAgent(BaseResearchAgent):
    
    async def fetch_data(self, symbol: str, db: Session) -> dict:
        profile, metrics, raw_data = await asyncio.gather(
            get_company_profile(symbol, db),
            get_key_metrics(symbol, db),
            fetch_indianapi_data(symbol, db)
        )
        
        recent_metrics = metrics[:1] if metrics and isinstance(metrics, list) else []
        
        # Extract peers list
        peers = []
        if raw_data:
            reusable = raw_data.get("stockDetailsReusableData") or {}
            profile_data = raw_data.get("companyProfile") or {}
            peers = profile_data.get("peerCompanyList") or reusable.get("peerCompanyList") or []
            
        return {
            "profile": json.dumps(profile[0] if profile else {}),
            "key_metrics": json.dumps(recent_metrics),
            "peers": json.dumps(peers, indent=2)
        }

    def get_prompt_template(self) -> str:
        return """Act like an elite equity research analyst specializing in competitive strategy, economic moats, industry structure, and long-term business durability.

Perform a deep moat and competition analysis of {symbol}. Go beyond superficial explanations and think like a long-term institutional investor evaluating whether this company can sustainably outperform competitors over the next decade.

Here is the raw data to assist your analysis:
Company Profile: {profile}
Key Performance Metrics (ROE, Margins, Growth): {key_metrics}
Peer Competitor List & Metrics: {peers}

Structure your exact output using the following Markdown headers and guidelines:

### 1. The Economic Moat
* **Core Competitive Advantages:** What is the true source of their moat? (Analyze brand strength, switching costs, network/ecosystem effects, cost advantages, patents, and distribution/supply chain superiority).
* **Moat Durability:** Is the moat real, weakening, or strengthening? Does it expand or weaken with scale?
* **Pricing Power & Replicability:** Do they have the power to raise prices? How difficult is it for competitors to replicate this business?

### 2. Industry Structure & Dynamics
* **The Arena:** Is the industry fragmented or consolidated? What is the intensity of competition?
* **Five Forces Analysis:** Evaluate the threat of new entrants, threat of substitutes, and the bargaining power of customers and suppliers.
* **Commoditization Risk:** Are their products/services at risk of becoming commodities? Are current margins sustainable long-term?

### 3. Competitor Comparison
* **The Rivals:** Identify the top competitors from the provided list. What are their moats, how do they do business, and why do customers choose this company over competitors (or vice versa)?
* **Execution Superiority & Uniqueness:** What makes this company unique compared to these peers? Based on the ROE, Margin, and Growth metrics provided, does this company mathematically execute better than industry norms? 
* **The Biggest Threat:** Which company in the peer list is the biggest long-term threat to this company, and why?

### 4. The Long-Term Verdict
* **Disruption Risk:** Can AI, automation, or technology shifts disrupt this moat?
* **Market Dominance:** Which company is most likely to dominate the industry over the next decade?
* **Market Mispricing:** Does the market overestimate or underestimate this company's moat?

**Formatting Rules:**
- Use bullet points (`*`) for every sub-point.
- Explain your reasoning deeply but clearly.
- Use **bold text** to highlight key terms.
- Never use introductory or concluding filler. Start immediately with the first header.
"""
