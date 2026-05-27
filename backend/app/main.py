from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes
from app.api import concall
from app.api import assistant
from app.api import equity_research
from app.core.db import engine
from app.models.base import Base
from app.models.document import Document
from app.models.concall import ConcallDocument
from app.models.equity_research import Company, ResearchCache, APICache
import logging

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

# Auto-migrate: safely add new columns to existing tables so production DB
# stays in sync without needing a manual migration step on Render.
def run_auto_migrations():
    from sqlalchemy import text
    migrations = [
        ("concall_documents", "sector",       "ALTER TABLE concall_documents ADD COLUMN sector VARCHAR;"),
        ("concall_documents", "summary_data",  "ALTER TABLE concall_documents ADD COLUMN summary_data JSON;"),
        ("concall_documents", "error_message", "ALTER TABLE concall_documents ADD COLUMN error_message VARCHAR;"),
        ("concall_documents", "file_hash",     "ALTER TABLE concall_documents ADD COLUMN file_hash VARCHAR;"),
    ]
    with engine.connect() as conn:
        for table, column, sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.info(f"Migration applied: added '{column}' to '{table}'")
            except Exception:
                conn.rollback()
                # Column already exists — this is expected on subsequent deploys

try:
    run_auto_migrations()
except Exception as e:
    logger.warning(f"Auto-migration step failed (non-fatal): {e}")

app = FastAPI(
    title="AI Financial Results Analyzer",
    description="Intelligent Earnings PDF Understanding System",
    version="1.0.0"
)

import io
import csv
import os

@app.on_event("startup")
def populate_companies_if_empty():
    from app.core.db import SessionLocal
    from app.models.equity_research import Company
    
    db = SessionLocal()
    try:
        count = db.query(Company).count()
        if count == 0:
            # Load from the bundled CSV — avoids 403s from NSE WAF on non-Indian IPs (e.g. Render)
            csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "NSE_EQUITY.csv")
            csv_path = os.path.abspath(csv_path)
            
            logger.info(f"Company table is empty. Loading NSE equities from bundled CSV: {csv_path}")
            
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                added = 0
                for row in reader:
                    row_dict = {str(k).strip(): v for k, v in row.items()}
                    
                    symbol = str(row_dict.get('SYMBOL', '')).strip()
                    name = str(row_dict.get('NAME OF COMPANY', '')).strip()
                    
                    if not symbol or not name or symbol.lower() == 'nan':
                        continue
                        
                    isin = str(row_dict.get('ISIN NUMBER', '')).strip()
                    
                    db.add(Company(
                        symbol=symbol,
                        name=name,
                        isin=isin if isin and isin.lower() != 'nan' else None,
                        exchange="NSE"
                    ))
                    added += 1
                    
                    if added % 500 == 0:
                        db.commit()
                
                db.commit()
                logger.info(f"Successfully populated database with {added} NSE companies from bundled CSV.")
    except Exception as e:
        logger.error(f"Failed to auto-populate NSE companies: {e}")
    finally:
        db.close()


# CORS config to allow React frontend (Vite default is 5173, Next.js is 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api/v1")
app.include_router(concall.router, prefix="/api/v1/concall")
app.include_router(assistant.router, prefix="/api/v1/assistant")
app.include_router(equity_research.router, prefix="/api/v1/equity-research")

@app.get("/")
def read_root():
    return {"message": "AI Financial Results Analyzer API is running"}

@app.get("/api/v1/debug/yahoo")
def debug_yahoo():
    import requests
    from app.services.fmp_client import yf_session
    try:
        response = yf_session.get("https://query1.finance.yahoo.com/v8/finance/chart/RELIANCE.NS", timeout=10)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body_snippet": response.text[:500],
            "error": None
        }
    except Exception as e:
        return {
            "status_code": 500,
            "headers": {},
            "body_snippet": "",
            "error": str(e)
        }

