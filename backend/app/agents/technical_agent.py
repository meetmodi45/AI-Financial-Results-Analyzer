import json
from app.agents.base_agent import BaseResearchAgent
from app.services.fmp_client import get_company_profile, get_technical_data
from sqlalchemy.orm import Session
import asyncio

class TechnicalAgent(BaseResearchAgent):
    
    async def fetch_data(self, symbol: str, db: Session) -> dict:
        profile, tech_data = await asyncio.gather(
            get_company_profile(symbol, db),
            get_technical_data(symbol, db)
        )
        
        # Pre-calculate mathematical relationships
        pre_calc = []
        try:
            if tech_data:
                price = tech_data.get("currentPrice", 0)
                if price:
                    dma50 = tech_data.get("fiftyDayAverage")
                    if dma50:
                        dist_50 = round(((price - dma50) / dma50) * 100, 2)
                        pre_calc.append(f"- Price vs 50-Day Moving Average: {dist_50}%")
                        
                    dma200 = tech_data.get("twoHundredDayAverage")
                    if dma200:
                        dist_200 = round(((price - dma200) / dma200) * 100, 2)
                        pre_calc.append(f"- Price vs 200-Day Moving Average: {dist_200}%")
                        
                    high52 = tech_data.get("fiftyTwoWeekHigh")
                    if high52:
                        dist_high = round(((price - high52) / high52) * 100, 2)
                        pre_calc.append(f"- Distance from 52-Week High: {dist_high}%")
                        
                vol_today = tech_data.get("regularMarketVolume", 0)
                vol_avg = tech_data.get("averageVolume", 0)
                if vol_avg and vol_today:
                    vol_surge = round((vol_today / vol_avg), 2)
                    pre_calc.append(f"- Today's Volume vs Average Volume: {vol_surge}x normal volume")
        except:
            pass
            
        pre_calc_str = "\n".join(pre_calc) if pre_calc else "Pre-calculated metrics unavailable."

        return {
            "profile": json.dumps(profile[0] if profile else {}),
            "tech_data": json.dumps(tech_data),
            "pre_calc_str": pre_calc_str
        }

    def get_prompt_template(self) -> str:
        return """Act like a professional quantitative flow analyst and institutional trader specializing in price action, trend structure, and momentum.

Perform a deep technical analysis of {symbol}. 

Here is the extracted core mathematical data:
Company Profile: {profile}
Raw Technical Data: {tech_data}

**PRE-CALCULATED FACTS (USE THESE EXACT NUMBERS TO ANALYZE TREND):**
{pre_calc_str}

Structure your exact output using the following Markdown headers and guidelines:

### 1. Trend Structure & Moving Averages
* **Long-Term Trend:** Analyze the Price vs 200-Day Moving Average. Is the stock in a long-term bull or bear phase?
* **Short-Term Momentum:** Analyze the Price vs 50-Day Moving Average. Is the current momentum accelerating or breaking down?

### 2. Extremes & Flow
* **52-Week Positioning:** Based on the distance from the 52-Week High/Low, is the stock pushing new boundaries, deeply discounted, or stuck in a range?
* **Volume Activity:** Based on "Today's Volume vs Average Volume", is there a sudden surge in institutional buying/selling, or is trading quiet?

### 3. The Trade Setup
* **Technical Verdict:** Based strictly on these moving averages and volume data, what is the most logical technical bias right now (Bullish, Bearish, or Neutral)?
* **Actionable Plan:** Should a trader be accumulating, holding, or stepping aside right now?

**Formatting Rules:**
- DO NOT hallucinate visual chart patterns (e.g., Cup and Handle, Head and Shoulders). You are a quantitative analyst relying purely on the math provided.
- Keep paragraphs punchy (max 3 sentences).
- Use **bold text** to highlight key percentages.
"""
