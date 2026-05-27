import os
import json
import httpx
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.equity_research import APICache

logger = logging.getLogger(__name__)

# Configure a robust session for Yahoo Finance to avoid rate limits / blocks on Render
def get_yf_session():
    session = requests.Session()
    # Retry strategy with exponential backoff
    retry = Retry(
        total=5,
        read=5,
        connect=5,
        backoff_factor=1,  # 1s, 2s, 4s, 8s, 16s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    # Mask as a modern browser to prevent basic 403 Forbidden
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    return session

yf_session = get_yf_session()

async def get_cached_or_fetch(db: Session, cache_key: str, fetch_func, expiry_hours: int = 12):
    cache = db.query(APICache).filter(APICache.cache_key == cache_key).first()
    if cache:
        age = datetime.now(timezone.utc) - cache.created_at
        if age.total_seconds() < expiry_hours * 3600:
            # Only return cache if it's not empty/failed data
            if cache.response_data and str(cache.response_data) not in ("[]", "{}", "{'annual': [], 'quarterly': []}"):
                return cache.response_data
    
    data = await fetch_func()
    
    # Only cache successful data
    if data and str(data) not in ("[]", "{}", "{'annual': [], 'quarterly': []}"):
        if cache:
            cache.response_data = data
            cache.created_at = datetime.now(timezone.utc)
        else:
            cache = APICache(cache_key=cache_key, response_data=data)
            db.add(cache)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving APICache for {cache_key}: {e}")
            
    return data

async def get_company_profile(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    
    yf_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
    
    def fetch_yf():
        try:
            ticker = yf.Ticker(yf_symbol, session=yf_session)
            info = ticker.info
            return [{
                "symbol": symbol,
                "companyName": info.get("longName", symbol),
                "industry": info.get("industry", ""),
                "sector": info.get("sector", ""),
                "description": info.get("longBusinessSummary", ""),
                "website": info.get("website", ""),
                "employees": info.get("fullTimeEmployees", ""),
                "city": info.get("city", ""),
                "country": info.get("country", "")
            }]
        except Exception as e:
            logger.error(f"yfinance error for {yf_symbol} (get_company_profile): {e}")
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
            ticker = yf.Ticker(yf_symbol, session=yf_session)
            keys = ['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income', 'Basic EPS', 'Research And Development', 'Other Income Expense']
            # Using try/except within fetching data to catch yfinance exceptions
            try:
                annual = _extract_yf_data(ticker.financials, keys)
                quarterly = _extract_yf_data(ticker.quarterly_financials, keys)
            except Exception as inner_e:
                logger.error(f"yfinance internal error fetching financials for {yf_symbol}: {inner_e}")
                annual, quarterly = [], []
                
            return {
                "annual": annual,
                "quarterly": quarterly
            }
        except Exception as e:
            logger.error(f"yfinance income error for {yf_symbol}: {e}")
            return {"annual": [], "quarterly": []}
    return await asyncio.to_thread(fetch)

async def get_balance_sheet(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    yf_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
    def fetch():
        try:
            ticker = yf.Ticker(yf_symbol, session=yf_session)
            keys = ['Total Assets', 'Total Liabilities Net Minority Interest', 'Net Debt', 'Cash And Cash Equivalents', 'Stockholders Equity', 'Inventory']
            try:
                annual = _extract_yf_data(ticker.balance_sheet, keys)
                quarterly = _extract_yf_data(ticker.quarterly_balance_sheet, keys)
            except Exception as inner_e:
                logger.error(f"yfinance internal error fetching balance sheet for {yf_symbol}: {inner_e}")
                annual, quarterly = [], []
                
            return {
                "annual": annual,
                "quarterly": quarterly
            }
        except Exception as e:
            logger.error(f"yfinance balance sheet error for {yf_symbol}: {e}")
            return {"annual": [], "quarterly": []}
    return await asyncio.to_thread(fetch)

async def get_cash_flow_statement(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    yf_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
    def fetch():
        try:
            ticker = yf.Ticker(yf_symbol, session=yf_session)
            keys = ['Operating Cash Flow', 'Capital Expenditure', 'Free Cash Flow', 'Cash Dividends Paid']
            try:
                annual = _extract_yf_data(ticker.cashflow, keys)
                quarterly = _extract_yf_data(ticker.quarterly_cashflow, keys)
            except Exception as inner_e:
                logger.error(f"yfinance internal error fetching cash flow for {yf_symbol}: {inner_e}")
                annual, quarterly = [], []
                
            return {
                "annual": annual,
                "quarterly": quarterly
            }
        except Exception as e:
            logger.error(f"yfinance cash flow error for {yf_symbol}: {e}")
            return {"annual": [], "quarterly": []}
    return await asyncio.to_thread(fetch)

async def get_key_metrics(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    
    yf_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
    
    def fetch_yf_metrics():
        try:
            ticker = yf.Ticker(yf_symbol, session=yf_session)
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
            logger.error(f"yfinance metrics error for {yf_symbol}: {e}")
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
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
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
            
            # Remove the temporary timestamp and return top 5 to save tokens
            for item in news_items:
                del item["_timestamp"]
                
            return news_items[:5]
        except Exception as e:
            logger.error(f"Google News RSS error for {symbol}: {e}")
            return []
            
    return await asyncio.to_thread(fetch)

async def get_technical_data(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    
    yf_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
    
    def fetch():
        try:
            ticker = yf.Ticker(yf_symbol, session=yf_session)
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
            logger.error(f"yfinance technical data error for {yf_symbol}: {e}")
            return {}
            
    return await asyncio.to_thread(fetch)

async def get_valuation_data(symbol: str, db: Session):
    import yfinance as yf
    import asyncio
    
    yf_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
    
    def fetch():
        try:
            ticker = yf.Ticker(yf_symbol, session=yf_session)
            info = ticker.info
            return {
                "currentPrice": info.get("currentPrice", info.get("regularMarketPrice")),
                "marketCap": info.get("marketCap"),
                "trailingPE": info.get("trailingPE"),
                "forwardPE": info.get("forwardPE"),
                "pegRatio": info.get("pegRatio"),
                "priceToBook": info.get("priceToBook"),
                "priceToSales": info.get("priceToSalesTrailing12Months"),
                "enterpriseToEbitda": info.get("enterpriseToEbitda"),
                "dividendYield": info.get("dividendYield"),
                "freeCashflow": info.get("freeCashflow"),
                "returnOnEquity": info.get("returnOnEquity"),
                "returnOnAssets": info.get("returnOnAssets"),
                "debtToEquity": info.get("debtToEquity"),
                "trailingEps": info.get("trailingEps"),
                "forwardEps": info.get("forwardEps"),
                "promoterHolding": info.get("heldPercentInsiders")
            }
        except Exception as e:
            logger.error(f"yfinance valuation data error for {yf_symbol}: {e}")
            return {}
            
    return await asyncio.to_thread(fetch)
