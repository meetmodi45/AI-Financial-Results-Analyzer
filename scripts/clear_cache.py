import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from sqlalchemy import delete
from app.core.db import SessionLocal  # type: ignore
from app.models.equity_research import ResearchCache, APICache  # type: ignore

db = SessionLocal()
try:
    db.execute(delete(ResearchCache))
    db.execute(delete(APICache))
    db.commit()
    print("Caches cleared successfully!")
finally:
    db.close()
