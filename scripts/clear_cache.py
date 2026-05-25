import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.core.db import SessionLocal
from app.models.equity_research import ResearchCache, APICache

db = SessionLocal()
db.query(ResearchCache).delete()
db.query(APICache).delete()
db.commit()
print("Caches cleared successfully!")
