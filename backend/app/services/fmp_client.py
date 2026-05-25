import os
import json
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.equity_research import APICache

async def get_company_profile(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    
    # Ensure Indian stocks have .NS suffix for Yahoo Finance
    yf_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
    
    def fetch_yf():
        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            # Format to match the old FMP response structure expected by agents
            return [{
                "symbol": symbol,
                "companyName": info.get("longName", symbol),
                "industry": info.get("industry", ""),
                "sector": info.get("sector", ""),
                "description": info.get("longBusinessSummary", "")
            }]
        except Exception as e:
            print(f"yfinance error for {yf_symbol}: {e}")
            return []
            
    return await asyncio.to_thread(fetch_yf)

def _extract_yf_data(df, keys):
    if df is None or df.empty: return []
    extracted = {}
    for k in keys:
        if k in df.index:
            extracted[k] = df.loc[k].head(4).fillna(0).to_dict()
    formatted = []
    for date_col in df.columns[:4]:
        try:
            year_data = {"date": date_col.strftime('%Y-%m-%d')}
        except:
            year_data = {"date": str(date_col)}
        for k in extracted:
            year_data[k] = extracted[k].get(date_col, 0)
        formatted.append(year_data)
    return formatted

async def get_income_statement(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    yf_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
    def fetch():
        try:
            ticker = yf.Ticker(yf_symbol)
            keys = ['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income', 'Basic EPS', 'Research And Development', 'Other Income Expense']
            return {
                "annual": _extract_yf_data(ticker.financials, keys),
                "quarterly": _extract_yf_data(ticker.quarterly_financials, keys)
            }
        except Exception as e:
            print(f"yfinance income error for {yf_symbol}: {e}")
            return {"annual": [], "quarterly": []}
    return await asyncio.to_thread(fetch)

async def get_balance_sheet(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    yf_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
    def fetch():
        try:
            ticker = yf.Ticker(yf_symbol)
            keys = ['Total Assets', 'Total Liabilities Net Minority Interest', 'Net Debt', 'Cash And Cash Equivalents', 'Stockholders Equity', 'Inventory']
            return {
                "annual": _extract_yf_data(ticker.balance_sheet, keys),
                "quarterly": _extract_yf_data(ticker.quarterly_balance_sheet, keys)
            }
        except Exception as e:
            print(f"yfinance balance sheet error for {yf_symbol}: {e}")
            return {"annual": [], "quarterly": []}
    return await asyncio.to_thread(fetch)

async def get_cash_flow_statement(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    yf_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
    def fetch():
        try:
            ticker = yf.Ticker(yf_symbol)
            keys = ['Operating Cash Flow', 'Capital Expenditure', 'Free Cash Flow', 'Cash Dividends Paid']
            return {
                "annual": _extract_yf_data(ticker.cashflow, keys),
                "quarterly": _extract_yf_data(ticker.quarterly_cashflow, keys)
            }
        except Exception as e:
            print(f"yfinance cash flow error for {yf_symbol}: {e}")
            return {"annual": [], "quarterly": []}
    return await asyncio.to_thread(fetch)

async def get_key_metrics(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    
    yf_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
    
    def fetch_yf_metrics():
        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            return [{
                "symbol": symbol,
                "revenueGrowth": info.get("revenueGrowth", None),
                "earningsGrowth": info.get("earningsGrowth", None),
                "profitMargin": info.get("profitMargins", None),
                "operatingMargin": info.get("operatingMargins", None),
                "returnOnEquity": info.get("returnOnEquity", None),
                "returnOnAssets": info.get("returnOnAssets", None),
                "trailingPE": info.get("trailingPE", None),
                "priceToBook": info.get("priceToBook", None)
            }]
        except Exception as e:
            print(f"yfinance metrics error for {yf_symbol}: {e}")
            return []
            
    return await asyncio.to_thread(fetch_yf_metrics)

async def get_company_news(symbol: str, db: Session):
    import urllib.request
    import xml.etree.ElementTree as ET
    import urllib.parse
    import asyncio
    from email.utils import parsedate_to_datetime
    from app.models.equity_research import Company
    
    clean_symbol = symbol.replace(".NS", "")
    
    # Use the actual company name for better Google News results instead of just the ticker
    company = db.query(Company).filter(Company.symbol == clean_symbol).first()
    search_name = company.name if company else clean_symbol
    search_name = search_name.replace(" Ltd.", "").replace(" Limited", "").replace(" Ltd", "").strip()
    
    query = urllib.parse.quote(f"{search_name}")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    def fetch():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_data = response.read()
                
            root = ET.fromstring(xml_data)
            news_items = []
            
            for item in root.findall('.//item')[:25]:  # Fetch top 25 to sort and keep top 15
                title = item.find('title').text if item.find('title') is not None else ""
                pubDate_str = item.find('pubDate').text if item.find('pubDate') is not None else ""
                source = item.find('source').text if item.find('source') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                
                # Parse the date for sorting
                try:
                    dt = parsedate_to_datetime(pubDate_str)
                    timestamp = dt.timestamp()
                except:
                    timestamp = 0
                    
                news_items.append({
                    "title": title,
                    "date": pubDate_str,
                    "source": source,
                    "link": link,
                    "_timestamp": timestamp
                })
                
            # Sort explicitly by timestamp descending (newest first)
            news_items.sort(key=lambda x: x["_timestamp"], reverse=True)
            
            # Remove the temporary timestamp and return top 15
            for item in news_items:
                del item["_timestamp"]
                
            return news_items[:15]
        except Exception as e:
            print(f"Google News RSS error for {symbol}: {e}")
            return []
            
    return await asyncio.to_thread(fetch)

async def get_technical_data(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    
    yf_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
    
    def fetch():
        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            return {
                "currentPrice": info.get("currentPrice", info.get("regularMarketPrice")),
                "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
                "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
                "fiftyDayAverage": info.get("fiftyDayAverage"),
                "twoHundredDayAverage": info.get("twoHundredDayAverage"),
                "regularMarketVolume": info.get("regularMarketVolume"),
                "averageVolume": info.get("averageVolume")
            }
        except Exception as e:
            print(f"yfinance technical data error for {yf_symbol}: {e}")
            return {}
            
    return await asyncio.to_thread(fetch)

async def get_valuation_data(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    
    yf_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
    
    def fetch():
        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            return {
                "trailingPE": info.get("trailingPE"),
                "forwardPE": info.get("forwardPE"),
                "pegRatio": info.get("pegRatio"),
                "priceToBook": info.get("priceToBook"),
                "priceToSales": info.get("priceToSalesTrailing12Months"),
                "enterpriseToEbitda": info.get("enterpriseToEbitda"),
                "dividendYield": info.get("dividendYield"),
                "marketCap": info.get("marketCap"),
                "freeCashflow": info.get("freeCashflow")
            }
        except Exception as e:
            print(f"yfinance valuation data error for {yf_symbol}: {e}")
            return {}
            
    return await asyncio.to_thread(fetch)
