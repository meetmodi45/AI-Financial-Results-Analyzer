from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes
from app.api import concall
from app.api import assistant
from app.core.db import engine
from app.models.base import Base
from app.models.document import Document
from app.models.concall import ConcallDocument
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

@app.get("/")
def read_root():
    return {"message": "AI Financial Results Analyzer API is running"}

