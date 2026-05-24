from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from app.models.base import Base

class ConcallDocument(Base):
    __tablename__ = "concall_documents"
    
    id = Column(String, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    sector = Column(String, nullable=True)
    quarter = Column(String, nullable=False)
    fiscal_year = Column(String, nullable=False)
    processed_status = Column(String, default="PENDING")
    error_message = Column(String, nullable=True)
    summary_data = Column(JSON, nullable=True)
    file_hash = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
