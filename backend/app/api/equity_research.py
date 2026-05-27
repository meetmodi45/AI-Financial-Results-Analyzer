import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.db import get_db
from app.models.equity_research import Company
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(tags=["Equity Research"])

class CompanyResponse(BaseModel):
    id: int
    symbol: str
    name: str
    isin: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("/search", response_model=List[CompanyResponse])
def search_companies(q: str = "", limit: int = 10, db: Session = Depends(get_db)):
    """
    Search for companies by symbol or name.
    Useful for debounced frontend search.
    """
    if not q or len(q) < 2:
        return []
    
    search_term = f"%{q}%"
    companies = db.query(Company).filter(
        or_(
            Company.symbol.ilike(search_term),
            Company.name.ilike(search_term)
        )
    ).limit(limit).all()
    
    return companies

# A dictionary to route module names to their respective agent classes
from app.agents.moat_agent import MoatAgent
from app.agents.business_agent import BusinessAgent
from app.agents.financials_agent import FinancialsAgent
from app.agents.news_agent import NewsAgent
from app.agents.technical_agent import TechnicalAgent
from app.agents.valuation_agent import ValuationAgent

MODULE_AGENTS = {
    "moat": MoatAgent(),
    "business": BusinessAgent(),
    "financials": FinancialsAgent(),
    "news": NewsAgent(),
    "technical": TechnicalAgent(),
    "valuation": ValuationAgent(),
}

@router.get("/analyze/{ticker}/{module}")
async def analyze_module(ticker: str, module: str, db: Session = Depends(get_db)):
    """
    Stream the AI analysis for a specific module of a company.
    """
    agent = MODULE_AGENTS.get(module.lower())
    if not agent:
        raise HTTPException(status_code=400, detail=f"Module '{module}' not recognized or implemented yet.")
        
    return StreamingResponse(
        agent.analyze_stream(ticker, module.lower(), db), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


from app.services.fmp_client import get_income_statement, get_balance_sheet, get_cash_flow_statement, get_technical_data, get_key_metrics, fetch_indianapi_data, get_company_news

@router.get("/financials-data/{ticker}")
async def get_financials_data(ticker: str, db: Session = Depends(get_db)):
    """
    Returns raw financial statement tables (Income Statement, Balance Sheet, Cash Flow)
    as structured JSON — NO LLM involved. Used by the frontend to display data tables
    immediately. The user can then optionally trigger LLM summarization separately.
    """
    income_stmt, balance_sheet, cash_flow = await asyncio.gather(
        get_income_statement(ticker, db),
        get_balance_sheet(ticker, db),
        get_cash_flow_statement(ticker, db),
    )
    return {
        "income_statement": income_stmt,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
    }

@router.get("/technical-data/{ticker}")
async def get_technical_data_endpoint(ticker: str, db: Session = Depends(get_db)):
    """
    Returns raw technical metrics (DMA moving averages, volume statistics, 52-week extremes)
    as structured JSON — NO LLM involved. Used by the frontend to display metrics immediately.
    The user can then optionally trigger LLM summarization separately.
    """
    return await get_technical_data(ticker, db)

@router.get("/moat-data/{ticker}")
async def get_moat_data_endpoint(ticker: str, db: Session = Depends(get_db)):
    """
    Returns raw competitive metrics and peer comparison data (ROE, margins, peer PE/PB/Cap)
    as structured JSON — NO LLM involved. Used by the frontend to display competitive comparison immediately.
    The user can then optionally trigger LLM summarization separately.
    """
    metrics_list = await get_key_metrics(ticker, db)
    metrics = metrics_list[0] if metrics_list else {}
    
    data = await fetch_indianapi_data(ticker, db)
    peers = []
    if data:
        reusable = data.get("stockDetailsReusableData") or {}
        profile = data.get("companyProfile") or {}
        peers = profile.get("peerCompanyList") or reusable.get("peerCompanyList") or []
        
    return {
        "metrics": metrics,
        "peers": peers
    }

@router.get("/news-data/{ticker}")
async def get_news_data_endpoint(ticker: str, db: Session = Depends(get_db)):
    """
    Returns raw recent news articles (headlines, publication dates, sources, and links)
    as structured JSON — NO LLM involved. Used by the frontend to display news list immediately.
    The user can then optionally trigger LLM summarization separately.
    """
    return await get_company_news(ticker, db)

@router.get("/business-data/{ticker}")
async def get_business_data_endpoint(ticker: str, db: Session = Depends(get_db)):
    """
    Returns qualitative business overview data — company description, management team,
    shareholding pattern, sector/industry classification — as structured JSON.
    NO LLM, NO financial metrics. Used by the frontend to display the business profile
    immediately. The user can then optionally trigger the LLM deep-dive separately.
    """
    raw_data = await fetch_indianapi_data(ticker, db)

    description = ""
    industry = ""
    mg_industry = ""
    exchange_nse = ""
    exchange_bse = ""
    isin = ""
    company_name = ticker
    officers = []
    shareholding = []

    if raw_data:
        company_name = raw_data.get("companyName") or ticker
        industry = raw_data.get("industry") or ""
        profile = raw_data.get("companyProfile") or {}
        description = profile.get("companyDescription") or ""
        mg_industry = profile.get("mgIndustry") or ""
        exchange_nse = profile.get("exchangeCodeNse") or ""
        exchange_bse = profile.get("exchangeCodeBse") or ""
        isin = profile.get("isInId") or ""

        # Extract management team (officers)
        raw_officers = profile.get("officers") or {}
        officer_list = raw_officers.get("officer") or [] if isinstance(raw_officers, dict) else []
        for o in officer_list:
            if not isinstance(o, dict):
                continue
            title_obj = o.get("title") or {}
            title_val = title_obj.get("Value", "") if isinstance(title_obj, dict) else str(title_obj)
            name = f"{o.get('firstName', '')} {o.get('mI', '')} {o.get('lastName', '')}".strip().replace("  ", " ")
            officers.append({
                "name": name,
                "title": title_val,
                "age": o.get("age"),
                "since": o.get("since") or "",
            })

        # Extract shareholding pattern (latest quarter for each category)
        raw_sh = raw_data.get("shareholding") or []
        for category in raw_sh:
            if not isinstance(category, dict):
                continue
            cats = category.get("categories") or []
            latest = cats[-1] if cats else {}
            shareholding.append({
                "name": category.get("displayName") or category.get("categoryName") or "",
                "percentage": latest.get("percentage"),
                "asOf": latest.get("holdingDate"),
            })

    return {
        "companyName": company_name,
        "industry": industry,
        "mgIndustry": mg_industry,
        "exchangeNse": exchange_nse,
        "exchangeBse": exchange_bse,
        "isin": isin,
        "description": description,
        "officers": officers,
        "shareholding": shareholding,
    }

class ArticleSummaryRequest(BaseModel):
    title: str
    symbol: str

@router.post("/summarize-article")
async def summarize_article(req: ArticleSummaryRequest):
    """
    Summarize a single news article based on its headline and the company symbol.
    Returns a 2-3 sentence explanation of the news event and its financial implications.
    """
    from app.agents.base_agent import BaseResearchAgent
    from langchain_core.messages import SystemMessage, HumanMessage
    
    agent = BaseResearchAgent()
    
    system_prompt = (
        "You are an elite, razor-sharp institutional equity research analyst. "
        "Your task is to analyze financial news headlines and explain their direct operational and market implications."
    )
    human_prompt = f"""Analyze this news headline for {req.symbol} and write a highly specific, 2-to-3 sentence explanation of the news event and its direct financial/business implications.

Headline: {req.title}

STRICT INSTRUCTIONS:
- Do NOT use generic filler, introductory phrases (e.g. "This news reports...", "Based on the headline...", "The news suggests..."), or concluding remarks. Start immediately with the concrete impact.
- Translate the headline into business reality: if it mentions earnings, explain the margin impact; if it mentions a contract or product launch, explain the revenue or market share impact; if it mentions regulatory action or technical moves, explain the risk or price action significance.
- Refer specifically to the company and its business domain (e.g. mutual fund transfer agency for CAMS, IT services for TCS, energy/telecom for Reliance).
- Keep the summary strictly to 2 or 3 sentences. Be extremely dense with information.
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    try:
        response = await agent.primary_llm.ainvoke(messages)
        content = response.content
    except Exception as e:
        print(f"Primary LLM failed ({e}). Using Groq Fallback...")
        response = await agent.fallback_llm.ainvoke(messages)
        content = response.content
        
    return {"summary": content}




