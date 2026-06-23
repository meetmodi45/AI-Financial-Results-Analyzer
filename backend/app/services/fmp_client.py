import os
import json
import httpx
import logging
import asyncio
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.equity_research import APICache

logger = logging.getLogger(__name__)

INDIAN_API_KEY = os.getenv("INDIAN_API_KEY", "")

async def get_cached_or_fetch(db: Session, cache_key: str, fetch_func, expiry_hours: int = 12):
    cache = db.query(APICache).filter(APICache.cache_key == cache_key).first()
    if cache:
        cache_time = cache.created_at.replace(tzinfo=timezone.utc) if cache.created_at.tzinfo is None else cache.created_at
        age = datetime.now(timezone.utc) - cache_time
        if age.total_seconds() < expiry_hours * 3600:
            if cache.response_data and str(cache.response_data) not in ("[]", "{}", "None"):
                return cache.response_data
    
    data = await fetch_func()
    
    if data and str(data) not in ("[]", "{}", "None"):
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

async def fetch_indianapi_data(symbol: str, db: Session):
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    cache_key = f"indianapi_{clean_symbol}"
    
    async def fetch():
        url = "https://stock.indianapi.in/stock"
        params = {"name": clean_symbol}
        headers = {"X-API-Key": INDIAN_API_KEY}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params, timeout=15)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"IndianAPI error for {clean_symbol}: {response.status_code}")
                    return {}
        except Exception as e:
            logger.error(f"IndianAPI exception for {clean_symbol}: {e}")
            return {}
            
    return await get_cached_or_fetch(db, cache_key, fetch, expiry_hours=12)

async def fetch_indianapi_historical_stats(symbol: str, stats_type: str, db: Session):
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    cache_key = f"indianapi_stats_{stats_type}_{clean_symbol}"
    
    async def fetch():
        url = "https://stock.indianapi.in/historical_stats"
        params = {"stock_name": clean_symbol, "stats": stats_type}
        headers = {"X-API-Key": INDIAN_API_KEY}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params, timeout=15)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"IndianAPI historical_stats error for {clean_symbol} ({stats_type}): {response.status_code}")
                    return {}
        except Exception as e:
            logger.error(f"IndianAPI historical_stats exception for {clean_symbol} ({stats_type}): {e}")
            return {}
            
    return await get_cached_or_fetch(db, cache_key, fetch, expiry_hours=24)

def extract_indianapi_fundamentals(raw_data: dict, company_name: str = ""):
    profile = raw_data.get("companyProfile", {})
    peer_list = profile.get("peerCompanyList", [])
    
    market_cap, pe_ratio, eps_val, div_yield = "N/A", "N/A", "N/A", "N/A"
    
    # Check primary keyMetrics
    metrics = raw_data.get("keyMetrics") or {}
    if metrics:
        market_cap = metrics.get("marketCap") or metrics.get("market_cap", "N/A")
        pe_ratio = metrics.get("peRatio") or metrics.get("priceToEarningsValueRatio", "N/A")
        eps_val = metrics.get("eps", "N/A")
        div_yield = metrics.get("dividendYield", "N/A")
        
    # Check stockDetailsReusableData as secondary source
    reusable = raw_data.get("stockDetailsReusableData") or {}
    if market_cap == "N/A" and reusable:
        market_cap = reusable.get("marketCap", "N/A")
        pe_ratio = reusable.get("pPerEBasicExcludingExtraordinaryItemsTTM", "N/A")
        div_yield = reusable.get("currentDividendYieldCommonStockPrimaryIssueLTM", "N/A")
        
    if market_cap == "N/A" and peer_list and company_name:
        for peer in peer_list:
            if company_name.lower() in peer.get("companyName", "").lower() or company_name.lower() in peer.get("languageSupport", "").lower():
                market_cap = peer.get("marketCap", "N/A")
                pe_ratio = peer.get("priceToEarningsValueRatio", "N/A")
                div_yield = peer.get("dividendYieldIndicatedAnnualDividend", "N/A")
                
    return {
        "marketCap": market_cap,
        "peRatio": pe_ratio,
        "eps": eps_val,
        "dividendYield": div_yield
    }

async def get_company_profile(symbol: str, db: Session):
    data = await fetch_indianapi_data(symbol, db)
    if not data: return []
    
    profile = data.get("companyProfile", {})
    
    return [{
        "symbol": symbol,
        "companyName": data.get("companyName", symbol),
        "industry": data.get("industry", ""),
        "sector": profile.get("mgIndustry", ""),
        "description": profile.get("companyDescription", ""),
        "website": "",
        "employees": "",
        "city": "",
        "country": "India"
    }]

async def get_income_statement(symbol: str, db: Session):
    data = await fetch_indianapi_data(symbol, db)
    if not data:
        return {"annual": [], "quarterly": []}
    
    financials = data.get("financials", [])
    
    INC_FIELDS = {
        "Revenue": "Revenue",
        "TotalRevenue": "Total Revenue",
        "GrossProfit": "Gross Profit",
        "OperatingIncome": "Operating Income",
        "NetIncome": "Net Income",
        "TotalOperatingExpense": "Total Operating Expense",
        "Depreciation/Amortization": "D&A",
        "DilutedEPSExcludingExtraOrdItems": "Diluted EPS",
        "DilutedNormalizedEPS": "Diluted Normalized EPS",
        "DPS-CommonStockPrimaryIssue": "Dividend Per Share",
    }
    
    def parse_period(entry):
        sfm = entry.get("stockFinancialMap", {})
        inc = sfm.get("INC", [])
        row = {"Period": entry.get("EndDate", "")[:7], "FiscalYear": entry.get("FiscalYear", "")}
        for key, label in INC_FIELDS.items():
            val = next((i.get("value") for i in inc if i.get("key") == key), None)
            row[label] = val
        return row
    
    annual = sorted(
        [parse_period(f) for f in financials if f.get("Type") == "Annual"],
        key=lambda x: x["Period"]
    )
    quarterly = sorted(
        [parse_period(f) for f in financials if f.get("Type") == "Interim"],
        key=lambda x: x["Period"]
    )
    return {"annual": annual[-7:], "quarterly": quarterly[-8:]}


async def get_balance_sheet(symbol: str, db: Session):
    data = await fetch_indianapi_data(symbol, db)
    if not data:
        return {"annual": [], "quarterly": []}
    
    financials = data.get("financials", [])
    
    BAL_FIELDS = {
        "TotalAssets": "Total Assets",
        "TotalCurrentAssets": "Total Current Assets",
        "CashandShortTermInvestments": "Cash & ST Investments",
        "TotalReceivablesNet": "Total Receivables",
        "TotalCurrentLiabilities": "Total Current Liabilities",
        "TotalLiabilities": "Total Liabilities",
        "TotalDebt": "Total Debt",
        "TotalLongTermDebt": "Long Term Debt",
        "TotalEquity": "Total Equity",
        "CommonStockTotal": "Common Stock",
        "RetainedEarnings(AccumulatedDeficit)": "Retained Earnings",
    }
    
    def parse_period(entry):
        sfm = entry.get("stockFinancialMap", {})
        bal = sfm.get("BAL", [])
        row = {"Period": entry.get("EndDate", "")[:7], "FiscalYear": entry.get("FiscalYear", "")}
        for key, label in BAL_FIELDS.items():
            val = next((i.get("value") for i in bal if i.get("key") == key), None)
            row[label] = val
        return row
    
    annual = sorted(
        [parse_period(f) for f in financials if f.get("Type") == "Annual"],
        key=lambda x: x["Period"]
    )
    return {"annual": annual[-7:], "quarterly": []}


async def get_cash_flow_statement(symbol: str, db: Session):
    data = await fetch_indianapi_data(symbol, db)
    if not data:
        return {"annual": [], "quarterly": []}
    
    financials = data.get("financials", [])
    
    CAS_FIELDS = {
        "NetIncome/StartingLine": "Net Income (CF Start)",
        "Depreciation/Depletion": "Depreciation",
        "TotalCashFromOperatingActivities": "Operating Cash Flow",
        "CapitalExpenditures": "Capital Expenditures",
        "TotalCashFromInvestingActivities": "Investing Cash Flow",
        "TotalCashDividendsPaid": "Dividends Paid",
        "TotalCashFromFinancingActivities": "Financing Cash Flow",
        "NetChangeinCash": "Net Change in Cash",
        "CashTaxesPaid": "Cash Taxes Paid",
        "Issuance(Retirement)ofDebtNet": "Debt Issuance/Retirement",
    }
    
    def parse_period(entry):
        sfm = entry.get("stockFinancialMap", {})
        cas = sfm.get("CAS", [])
        row = {"Period": entry.get("EndDate", "")[:7], "FiscalYear": entry.get("FiscalYear", "")}
        for key, label in CAS_FIELDS.items():
            val = next((i.get("value") for i in cas if i.get("key") == key), None)
            row[label] = val
        return row
    
    annual = sorted(
        [parse_period(f) for f in financials if f.get("Type") == "Annual"],
        key=lambda x: x["Period"]
    )
    return {"annual": annual[-7:], "quarterly": []}



async def get_key_metrics(symbol: str, db: Session):
    val_data = await get_valuation_data(symbol, db)
    if not val_data: return []
    
    return [{
        "symbol": symbol,
        "revenueGrowth": val_data.get("_revenueGrowth"),
        "earningsGrowth": val_data.get("_earningsGrowth"),
        "profitMargin": val_data.get("_profitMargin"),
        "operatingMargin": val_data.get("_operatingMargin"),
        "returnOnEquity": val_data.get("returnOnEquity"),
        "returnOnAssets": val_data.get("returnOnAssets"),
        "trailingPE": val_data.get("trailingPE"),
        "priceToBook": val_data.get("priceToBook"),
        "marketCap": val_data.get("marketCap") / 10000000.0 if val_data.get("marketCap") else None
    }]

async def _fetch_google_news_rss(query: str, days: int = 7) -> list:
    """
    Fetch latest news via Google News RSS — no API key, always live.
    Restricts to `days` recent days and sorts results by pubDate descending
    so the freshest articles always appear first.
    """
    # `when:Nd` tells Google News to only return articles from the last N days
    full_query = f"{query} when:{days}d"
    encoded_query = quote_plus(full_query)
    rss_url = (
        f"https://news.google.com/rss/search"
        f"?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
            timeout=15,
        ) as client:
            resp = await client.get(rss_url)
            if resp.status_code != 200:
                logger.warning(f"[News/GNews] RSS returned {resp.status_code} for query '{query}'")
                return []

        root = ET.fromstring(resp.text)
        channel = root.find("channel")
        if channel is None:
            return []

        items = []
        for item in channel.findall("item"):
            title  = (item.findtext("title") or "").strip()
            link   = (item.findtext("link")  or "").strip()
            pub    = (item.findtext("pubDate") or "").strip()
            src_el = item.find("source")
            source = src_el.text.strip() if src_el is not None and src_el.text else "Google News"

            if not title:
                continue

            # Parse pubDate so we can sort by it
            pub_dt = None
            for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
                try:
                    pub_dt = datetime.strptime(pub, fmt)
                    break
                except ValueError:
                    pass

            items.append({
                "title": title,
                "link": link,
                "date": pub,
                "_pub_dt": pub_dt or datetime.min,
                "source": source,
            })

        # Sort newest first
        items.sort(key=lambda x: x["_pub_dt"], reverse=True)
        # Remove internal sort key before returning
        for item in items:
            item.pop("_pub_dt", None)

        return items
    except Exception as e:
        logger.warning(f"[News/GNews] Failed for query '{query}': {e}")
        return []



async def _fetch_indianapi_news_fallback(symbol: str) -> list:
    """
    Fallback: extract recentNews from IndianAPI /stock endpoint.
    Only used when Google News returns nothing.
    """
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    headers = {"X-API-Key": INDIAN_API_KEY}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://stock.indianapi.in/stock",
                params={"name": clean_symbol},
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                raw = resp.json().get("recentNews") or []
                items = []
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("headline") or item.get("title") or ""
                    pub   = item.get("lastPublishedDate") or item.get("date") or ""
                    source = item.get("source") or "LiveMint"
                    url_path = item.get("metadata", {}).get("url") if isinstance(item.get("metadata"), dict) else ""
                    url_direct = item.get("url") or item.get("link") or ""
                    if url_path and url_path.startswith("/"):
                        link = f"https://www.livemint.com{url_path}"
                    else:
                        link = url_direct
                    if title:
                        items.append({"title": title, "date": pub, "source": source, "link": link})
                return items
    except Exception as e:
        logger.warning(f"[News/IndianAPI fallback] Failed for {symbol}: {e}")
    return []


async def _build_news_items(company_name: str, symbol: str, db: Session) -> list:
    """Core news-fetching logic (no cache). Called by get_company_news after cache miss."""
    # Start tight (7 days), widen automatically if results are sparse
    query = f'"{company_name}" NSE'
    news_items = await _fetch_google_news_rss(query, days=7)

    # Too few in 7 days → widen to 30 days (handles niche/small-cap stocks)
    if len(news_items) < 3:
        news_items = await _fetch_google_news_rss(query, days=30)

    # Still too few → try unquoted broader query (catches alternate name spellings)
    if len(news_items) < 3:
        query_broad = f"{company_name} NSE stock India"
        extra = await _fetch_google_news_rss(query_broad, days=30)
        seen = {n["title"] for n in news_items}
        for item in extra:
            if item["title"] not in seen:
                news_items.append(item)
                seen.add(item["title"])

    # Last resort: IndianAPI recentNews (may be stale but never crashes)
    if not news_items:
        logger.info(f"[News] Google News returned nothing for '{company_name}', trying IndianAPI fallback")
        news_items = await _fetch_indianapi_news_fallback(symbol)

    return news_items[:10]


async def get_company_news(symbol: str, db: Session):
    """
    Fetch the latest stock-specific news.

    Cache strategy: 15-minute SQLite cache (existing APICache table).
    - Prevents hammering Google RSS when multiple users search the same stock
    - Still fresh enough for financial news (articles don't change in 15 min)
    - On cache miss → Google News RSS (7d → 30d → broad) → IndianAPI fallback
    """
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")

    # Get real company name from cached IndianAPI data so the RSS query matches
    # actual article headlines (e.g. "JSW Infrastructure", not "JSWINFRA")
    company_name = clean_symbol
    try:
        stock_data = await fetch_indianapi_data(symbol, db)
        if stock_data:
            raw_name = stock_data.get("companyName") or ""
            if raw_name:
                for suffix in (" Limited", " Ltd.", " Ltd", " LTD", " LIMITED"):
                    raw_name = raw_name.replace(suffix, "")
                company_name = raw_name.strip()
    except Exception:
        pass

    # 15-minute cache keyed per company — dramatically reduces Google RSS requests
    cache_key = f"gnews_15m_{clean_symbol}"

    async def fetch():
        return await _build_news_items(company_name, symbol, db)

    return await get_cached_or_fetch(db, cache_key, fetch, expiry_hours=0.25)





async def get_technical_data(symbol: str, db: Session):
    data = await fetch_indianapi_data(symbol, db)
    if not data: return {}
    
    price_data = data.get("currentPrice") or data.get("lastPrice") or {}
    if isinstance(price_data, dict):
        nse_price = price_data.get("NSE", "N/A")
        bse_price = price_data.get("BSE", "N/A")
        curr_price = nse_price if nse_price != "N/A" else bse_price
    else:
        curr_price = price_data

    # Parse moving averages from stockTechnicalData
    tech_list = data.get("stockTechnicalData") or []
    dma50 = None
    dma200 = None
    
    for item in tech_list:
        days = item.get("days")
        # Get price prioritizing NSE then BSE
        p_val = item.get("nsePrice") or item.get("bsePrice")
        if p_val and p_val != "N/A":
            try:
                p_val = float(p_val)
            except ValueError:
                p_val = None
                
        if p_val is not None:
            if days == 50:
                dma50 = p_val
            elif days == 300: # 300 DMA is the closest long-term average available in IndianAPI
                dma200 = p_val
            elif days == 100 and dma200 is None: # fallback proxy if 300 not found
                dma200 = p_val

    # Parse average volume and today's volume indicator from keyMetrics -> priceandVolume
    vol_10d = None
    vol_3m = None
    metrics_list = data.get("keyMetrics", {}).get("priceandVolume") or []
    for m in metrics_list:
        key = m.get("key")
        val = m.get("value")
        if val and val != "N/A":
            try:
                val = float(val)
            except ValueError:
                val = None
        if val is not None:
            if key == "avgTradingVolumeLast10Days":
                vol_10d = val
            elif key == "avgTradingVolumeLast3months":
                vol_3m = val

    # Return structure mapped to technical agent expectations
    return {
        "currentPrice": float(curr_price) if curr_price not in ("N/A", None) else None,
        "fiftyTwoWeekHigh": data.get("yearHigh") or data.get("year_high"),
        "fiftyTwoWeekLow": data.get("yearLow") or data.get("year_low"),
        "fiftyDayAverage": dma50,
        "twoHundredDayAverage": dma200,
        "regularMarketVolume": vol_10d,
        "averageVolume": vol_3m,
        "percentChange": data.get("percentChange") or data.get("percent_change")
    }


async def get_valuation_data(symbol: str, db: Session):
    data, ratios_data, cf_data, bs_data, qr_data, sh_data = await asyncio.gather(
        fetch_indianapi_data(symbol, db),
        fetch_indianapi_historical_stats(symbol, "ratios", db),
        fetch_indianapi_historical_stats(symbol, "cashflow", db),
        fetch_indianapi_historical_stats(symbol, "balancesheet", db),
        fetch_indianapi_historical_stats(symbol, "quarter_results", db),
        fetch_indianapi_historical_stats(symbol, "shareholding_pattern_quarterly", db)
    )
    
    if not data: return {}
    
    fundamentals = extract_indianapi_fundamentals(data, data.get("companyName", symbol.replace(".NS", "")))
    
    price_data = data.get("currentPrice") or data.get("lastPrice") or {}
    if isinstance(price_data, dict):
        nse_price = price_data.get("NSE", "N/A")
        curr_price = nse_price if nse_price != "N/A" else price_data.get("BSE", "N/A")
    else:
        curr_price = price_data
        
    # Helper to get the latest value from a chronological dict
    def get_latest(stat_dict):
        if not stat_dict: return None
        try:
            return list(stat_dict.values())[-1]
        except:
            return None

    reusable = data.get("stockDetailsReusableData", {})
    debt_equity = reusable.get("totalDebtPerTotalEquityMostRecentQuarter")
    
    # --- Peers PE from companyProfile peerCompanyList (has more entries with PE data) ---
    cp_peers = data.get("companyProfile", {}).get("peerCompanyList", [])
    # Also check reusable peers as fallback
    reusable_peers = reusable.get("peerCompanyList", [])
    all_peers = cp_peers if cp_peers else reusable_peers
    peers_pe = None
    pe_list = []
    for p in all_peers:
        p_pe = p.get("priceToEarningsValueRatio")
        if p_pe not in (None, "N/A", "-"):
            try: pe_list.append(float(p_pe))
            except: pass
    if pe_list:
        peers_pe = sum(pe_list) / len(pe_list)
    
    # --- PE: prefer reusable key over keyMetrics (keyMetrics often returns N/A) ---
    pe_val = fundamentals["peRatio"] if fundamentals["peRatio"] != "N/A" else None
    if pe_val is None:
        reusable_pe = reusable.get("pPerEBasicExcludingExtraordinaryItemsTTM")
        if reusable_pe not in (None, "N/A", "-"):
            try: pe_val = float(reusable_pe)
            except: pass

    # --- EPS: try keyMetrics.eps first, then persharedata list inside keyMetrics ---
    eps_val = fundamentals["eps"] if fundamentals["eps"] != "N/A" else None
    if eps_val is None:
        km = data.get("keyMetrics", {})
        pershare_list = km.get("persharedata", []) if isinstance(km, dict) else []
        for item in pershare_list:
            if item.get("key") == "ePSIncludingExtraOrdinaryItemsTrailing12Month":
                v = item.get("value")
                if v not in (None, "N/A", "-"):
                    try:
                        eps_val = float(v)
                        break
                    except: pass
    if eps_val is None and pe_val is not None and curr_price not in ("N/A", None):
        try: eps_val = round(float(curr_price) / float(pe_val), 2)
        except: pass

    # --- Market Cap: prefer reusable (in Cr), convert to raw rupees ---
    market_cap_raw = fundamentals["marketCap"]
    market_cap = float(market_cap_raw) * 10000000 if market_cap_raw != "N/A" else None
    if market_cap is None:
        reusable_mc = reusable.get("marketCap")
        if reusable_mc not in (None, "N/A", "-"):
            try: market_cap = float(reusable_mc) * 10000000
            except: pass
    
    # --- Dividend Yield: from reusable (value is already in %) ---
    div_yield_val = None
    raw_dy = fundamentals["dividendYield"]
    if raw_dy != "N/A":
        try: div_yield_val = float(raw_dy) / 100
        except: pass
    if div_yield_val is None:
        reusable_dy = reusable.get("currentDividendYieldCommonStockPrimaryIssueLTM")
        if reusable_dy not in (None, "N/A", "-"):
            try: div_yield_val = float(reusable_dy) / 100
            except: pass
    
    # --- Book value per share: from keyMetrics.persharedata (use for P/B calculation as fallback) ---
    bvps = None
    km = data.get("keyMetrics", {})
    pershare_list = km.get("persharedata", []) if isinstance(km, dict) else []
    for item in pershare_list:
        if item.get("key") == "bookValuePerShareMostRecentQuarter":
            v = item.get("value")
            if v not in (None, "N/A", "-"):
                try:
                    bvps = float(v)
                    break
                except: pass
    
    # --- Promoter Holding: from shareholding list in main data ---
    promoter_holding_direct = None
    sh_list = data.get("shareholding", [])
    for s in sh_list:
        cat_name = s.get("displayName", "").lower()
        if "promoter" in cat_name:
            cats = s.get("categories", [])
            if cats:
                latest = cats[-1]
                pct = latest.get("percentage")
                if pct not in (None, "N/A", "-"):
                    try:
                        promoter_holding_direct = float(pct) / 100.0
                        break
                    except: pass
    
    fcf = get_latest(cf_data.get("Free Cash Flow"))
    if fcf is not None:
        try: fcf = float(fcf) * 10000000
        except: fcf = None
        
    roa = get_latest(ratios_data.get("ROCE %"))
    if roa is not None:
        try: roa = float(roa) / 100.0
        except: roa = None
        
    eq_cap = get_latest(bs_data.get("Equity Capital"))
    reserves = get_latest(bs_data.get("Reserves"))
    price_to_book = None
    book_value_cr = None
    if eq_cap is not None and reserves is not None:
        try: book_value_cr = float(eq_cap) + float(reserves)
        except: pass
        
    if book_value_cr and book_value_cr > 0 and market_cap is not None:
        try: price_to_book = (market_cap / 10000000) / book_value_cr
        except: pass
    
    # Fallback P/B: use bvps from persharedata and current price
    if price_to_book is None and bvps is not None and bvps > 0 and curr_price not in (None, "N/A"):
        try: price_to_book = float(curr_price) / bvps
        except: pass
            
    sales_dict = qr_data.get("Sales", {})
    price_to_sales = None
    ttm_sales = None
    if sales_dict and len(sales_dict) >= 4:
        try: ttm_sales = sum([float(x) for x in list(sales_dict.values())[-4:]])
        except: pass
        
    if ttm_sales and ttm_sales > 0 and market_cap is not None:
        try: price_to_sales = (market_cap / 10000000) / ttm_sales
        except: pass
        
    np_dict = qr_data.get("Net Profit", {})
    roe = None
    earnings_growth = None
    ttm_net_profit = None
    if np_dict and len(np_dict) >= 8:
        try:
            np_values = [float(x) for x in np_dict.values()]
            ttm_net_profit = sum(np_values[-4:])
            prev_ttm_net_profit = sum(np_values[-8:-4])
            if book_value_cr and book_value_cr > 0:
                roe = ttm_net_profit / book_value_cr
            if prev_ttm_net_profit != 0:
                earnings_growth = (ttm_net_profit - prev_ttm_net_profit) / abs(prev_ttm_net_profit)
        except: pass

    revenue_growth = None
    profit_margin = None
    opm = get_latest(qr_data.get("OPM %"))
    if opm is not None:
        try: opm = float(opm) / 100.0
        except: opm = None
        
    if sales_dict and len(sales_dict) >= 8:
        try:
            sales_values = [float(x) for x in sales_dict.values()]
            prev_ttm_sales = sum(sales_values[-8:-4])
            if prev_ttm_sales != 0 and ttm_sales is not None:
                revenue_growth = (ttm_sales - prev_ttm_sales) / abs(prev_ttm_sales)
            if ttm_sales and ttm_sales != 0 and ttm_net_profit is not None:
                profit_margin = ttm_net_profit / ttm_sales
        except: pass

    peg_ratio = None
    if pe_val is not None and earnings_growth is not None and earnings_growth > 0:
        try: peg_ratio = float(pe_val) / (earnings_growth * 100)
        except: pass
        
    ev_ebitda = None
    borrowings = get_latest(bs_data.get("Borrowings"))
    op_dict = qr_data.get("Operating Profit", {})
    if borrowings is not None and op_dict and len(op_dict) >= 4 and market_cap is not None:
        try:
            ev_cr = (market_cap / 10000000) + float(borrowings)
            ttm_ebitda = sum([float(x) for x in list(op_dict.values())[-4:]])
            if ttm_ebitda > 0:
                ev_ebitda = ev_cr / ttm_ebitda
        except: pass
        
    # Prefer direct shareholding data; fallback to historical_stats
    promoter_holding = promoter_holding_direct
    if promoter_holding is None:
        ph_raw = get_latest(sh_data.get("Promoters"))
        if ph_raw is not None:
            try: promoter_holding = float(ph_raw) / 100.0
            except: promoter_holding = None

    return {
        "currentPrice": curr_price if curr_price != "N/A" else None,
        "marketCap": market_cap,
        "trailingPE": pe_val,
        "peersPE": peers_pe,
        "pegRatio": peg_ratio,
        "priceToBook": price_to_book,
        "priceToSales": price_to_sales,
        "enterpriseToEbitda": ev_ebitda,
        "dividendYield": div_yield_val,
        "freeCashflow": fcf,
        "returnOnEquity": roe,
        "returnOnAssets": roa,
        "debtToEquity": float(debt_equity) if debt_equity not in (None, "N/A", "-") else None,
        "trailingEps": eps_val,
        "promoterHolding": promoter_holding,
        
        # Internal fields for key metrics
        "_revenueGrowth": revenue_growth,
        "_earningsGrowth": earnings_growth,
        "_profitMargin": profit_margin,
        "_operatingMargin": opm
    }
