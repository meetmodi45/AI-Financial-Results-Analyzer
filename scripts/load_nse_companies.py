import pandas as pd
import os
import sys
from dotenv import load_dotenv

# Ensure we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.core.db import SessionLocal, engine
from app.models.base import Base
from app.models.equity_research import Company, ResearchCache, APICache

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def load_csv(csv_path: str):
    print(f"Loading data from {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    db = SessionLocal()
    
    count = 0
    for _, row in df.iterrows():
        # Clean up column names which might have leading spaces
        row_dict = {str(k).strip(): v for k, v in row.items()}
        
        symbol = str(row_dict.get('SYMBOL', '')).strip()
        name = str(row_dict.get('NAME OF COMPANY', '')).strip()
        
        if not symbol or not name or symbol == 'nan' or name == 'nan':
            continue
            
        isin = str(row_dict.get('ISIN NUMBER', '')).strip()
        industry = str(row_dict.get('Industry', '')).strip() # not in CSV, will be empty
        
        # Check if already exists
        existing = db.query(Company).filter(Company.symbol == symbol).first()
        if not existing:
            new_company = Company(
                symbol=symbol,
                name=name,
                isin=isin if isin and str(isin).lower() != 'nan' else None,
                industry=industry if industry and str(industry).lower() != 'nan' else None,
                exchange="NSE"
            )
            db.add(new_company)
            count += 1
            
        if count % 100 == 0:
            db.commit()
            print(f"Loaded {count} companies...")
            
    db.commit()
    db.close()
    print(f"Successfully loaded {count} new companies into the database.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python load_nse_companies.py <path_to_csv>")
        sys.exit(1)
        
    csv_file_path = sys.argv[1]
    if os.path.exists(csv_file_path):
        load_csv(csv_file_path)
    else:
        print("Error: File not found.")
