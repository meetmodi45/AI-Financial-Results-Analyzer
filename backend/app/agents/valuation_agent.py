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
            fcf = val_data.get("freeCashflow")
            mcap = val_data.get("marketCap")
            if fcf is not None and mcap is not None and mcap > 0:
                fcf_yield = round((fcf / mcap) * 100, 2)
                val_data["fcfYield"] = f"{fcf_yield}%"
            else:
                val_data["fcfYield"] = None

            def format_currency(val):
                if val is None: return None
                try:
                    cr_val = float(val) / 10000000
                    return f"₹ {cr_val:,.2f} Cr."
                except: return None

            def format_number(val):
                if val is None: return None
                try: return f"{float(val):.2f}"
                except: return None
            
            def format_percentage(val):
                if val is None: return None
                try: return f"{float(val) * 100:.2f}%"
                except: return None

            val_data['marketCap'] = format_currency(val_data.get('marketCap'))
            val_data['freeCashflow'] = format_currency(val_data.get('freeCashflow'))
            
            for key in ['dividendYield', 'returnOnEquity', 'returnOnAssets', 'promoterHolding']:
                val_data[key] = format_percentage(val_data.get(key))
                
            for key in ['currentPrice', 'trailingPE', 'peersPE', 'pegRatio', 'priceToBook', 'priceToSales', 'enterpriseToEbitda', 'debtToEquity', 'trailingEps']:
                val_data[key] = format_number(val_data.get(key))

        return val_data


    def _generate_report(self, val_data: dict) -> str:
        if not val_data:
            return "Valuation data unavailable."
            
        report = "### Current Valuation Multiples & Key Metrics\n\n"
        
        metrics_mapping = [
            ("Current Price", "currentPrice"),
            ("Market Cap", "marketCap"),
            ("Trailing P/E", "trailingPE"),
            ("Peers Avg P/E", "peersPE"),
            ("Price-to-Book (P/B)", "priceToBook"),
            ("Price-to-Sales (P/S)", "priceToSales"),
            ("EV/EBITDA", "enterpriseToEbitda"),
            ("PEG Ratio", "pegRatio"),
            ("Free Cash Flow (FCF) Yield", "fcfYield"),
            ("Dividend Yield", "dividendYield"),
            ("Return on Equity (ROE)", "returnOnEquity"),
            ("Return on Assets (ROCE proxy)", "returnOnAssets"),
            ("Debt to Equity", "debtToEquity"),
            ("Trailing EPS", "trailingEps"),
            ("Promoter Holding", "promoterHolding")
        ]
        
        for label, key in metrics_mapping:
            val = val_data.get(key)
            # Skip metrics with no data
            if val is None or val == "Unavailable":
                continue
            report += f"* **{label}:** {val}\n"
            
        return report

    async def analyze_stream(self, symbol: str, module_name: str, db: Session):
        import json
        yield f"data: {json.dumps({'clear': True})}\n\n"
        
        val_data = await self.fetch_data(symbol, db)
        report = self._generate_report(val_data)
        
        # Stream it chunk by chunk to simulate AI typing so frontend doesn't break
        chunk_size = 30
        for i in range(0, len(report), chunk_size):
            chunk = report[i:i+chunk_size]
            yield f"data: {json.dumps({'content': chunk})}\n\n"
            await asyncio.sleep(0.01)
            
        yield "data: [DONE]\n\n"
        
    async def analyze(self, symbol: str, module_name: str, db: Session) -> str:
        val_data = await self.fetch_data(symbol, db)
        return self._generate_report(val_data)
