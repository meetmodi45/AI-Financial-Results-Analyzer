from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.models.base import Base

class ConcallDocument(Base):
    __tablename__ = "concall_documents"
    
    id = Column(String, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    quarter = Column(String, nullable=False)
    fiscal_year = Column(String, nullable=False)
    file_path = Column(String, nullable=True)  # No longer used — files processed in memory
    processed_status = Column(String, default="PENDING")
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
