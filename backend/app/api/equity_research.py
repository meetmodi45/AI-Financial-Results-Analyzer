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
    Run an AI analysis agent for a specific module of a company.
    Returns the full analysis as JSON once complete.
    """
    from fastapi.responses import JSONResponse

    agent = MODULE_AGENTS.get(module.lower())
    if not agent:
        raise HTTPException(status_code=400, detail=f"Module '{module}' not recognized.")

    try:
        result = await agent.analyze(ticker, module.lower(), db)
        return JSONResponse(content={"content": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
