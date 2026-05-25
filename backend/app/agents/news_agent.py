import json
from app.agents.base_agent import BaseResearchAgent
from app.services.fmp_client import get_company_profile, get_company_news
from sqlalchemy.orm import Session
import asyncio

class NewsAgent(BaseResearchAgent):
    
    async def fetch_data(self, symbol: str, db: Session) -> dict:
        profile, news = await asyncio.gather(
            get_company_profile(symbol, db),
            get_company_news(symbol, db)
        )
        return {
            "profile": json.dumps(profile[0] if profile else {}),
            "news": json.dumps(news)
        }

    def get_prompt_template(self) -> str:
        return """Act as a minimal financial news feed. 

Your ONLY job is to output a clean, bulleted list of the top 10 most recent and unique news events for {symbol}. 
Do not provide any analysis, opinions, takeaways, or explanations of what the news means.

Here is the raw data:
Latest News & Headlines: {news}

Structure your exact output as a single list under one header:

### Latest News
* **[Date]:** [Provide a concise 1-2 sentence summary of the news, highlighting the most important fact or number]. ([Source: Publisher Name](link))
* **[Date]:** [Provide a concise 1-2 sentence summary of the news, highlighting the most important fact or number]. ([Source: Publisher Name](link))

**Formatting Rules:**
- Only output the top 10 most recent news events.
- Keep each summary to exactly 1 to 2 sentences max. Keep it punchy but informative.
- Use **bold text** for the date.
- Do NOT include any other headers, introductions, or conclusions.
- Do NOT include sections like "Business Impact" or "The Big Picture".
- If the news array is empty, explicitly state that there is no recent major news coverage.
"""
