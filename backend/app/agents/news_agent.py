import json
from app.agents.base_agent import BaseResearchAgent
from app.services.fmp_client import get_company_profile, get_company_news
from sqlalchemy.orm import Session
import asyncio

class NewsAgent(BaseResearchAgent):
    
    async def fetch_data(self, symbol: str, db: Session) -> dict:
        news = await get_company_news(symbol, db)
        
        # Format compactly as plain text to save tokens instead of JSON
        news_text = ""
        for i, n in enumerate(news):
            news_text += f"{i+1}. Title: {n['title']}\n   Date: {n['date']}\n   Source: {n['source']}\n   Link: {n['link']}\n\n"
            
        return {
            "news": news_text.strip()
        }

    def get_prompt_template(self) -> str:
        return """Act as a minimal financial news feed. 

Your ONLY job is to output a clean, bulleted list of the top 5 most recent and unique news events for {symbol}. 
Do not provide any analysis, opinions, takeaways, or explanations of what the news means.

Here is the raw data:
Latest News & Headlines: {news}

Structure your exact output as a single list under one header:

### Latest News
* **[Date]:** [Provide a concise 1-2 sentence summary of the news, highlighting the most important fact or number]. (<a href="[link]" target="_blank" style="color: blue; text-decoration: underline;">Source: [Publisher Name]</a>)
* **[Date]:** [Provide a concise 1-2 sentence summary of the news, highlighting the most important fact or number]. (<a href="[link]" target="_blank" style="color: blue; text-decoration: underline;">Source: [Publisher Name]</a>)

**Formatting Rules:**
- Only output the top 5 most recent news events.
- Keep each summary to exactly 1 to 2 sentences max. Keep it punchy but informative.
- Use **bold text** for the date.
- You MUST format the source as a raw HTML anchor tag exactly like the template above, using `target="_blank"` and the provided inline style so it appears blue and underlined.
- Do NOT include any other headers, introductions, or conclusions.
- Do NOT include sections like "Business Impact" or "The Big Picture".
- If the news array is empty, explicitly state that there is no recent major news coverage.
"""
