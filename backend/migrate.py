import os
import sys
from sqlalchemy import create_engine, text

# Add backend to path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def run_migration():
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    
    with engine.connect() as conn:
        print("Adding 'sector' column...")
        try:
            conn.execute(text("ALTER TABLE concall_documents ADD COLUMN sector VARCHAR;"))
            print("Successfully added 'sector' column.")
        except Exception as e:
            print(f"Error or column already exists: {e}")
            
        print("Adding 'summary_data' column...")
        try:
            conn.execute(text("ALTER TABLE concall_documents ADD COLUMN summary_data JSON;"))
            print("Successfully added 'summary_data' column.")
        except Exception as e:
            print(f"Error or column already exists: {e}")
            
        conn.commit()

if __name__ == "__main__":
    run_migration()
