from sqlalchemy import Column, String, Integer, DateTime, Enum, JSON
from sqlalchemy.sql import func
import enum
from app.models.base import Base

class ProcessingStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    CLASSIFYING_PDF = "CLASSIFYING_PDF"
    OCR_EXTRACTION = "OCR_EXTRACTION"
    DOCUMENT_CLASSIFICATION = "DOCUMENT_CLASSIFICATION"
    TABLE_EXTRACTION = "TABLE_EXTRACTION"
    NORMALIZING_METRICS = "NORMALIZING_METRICS"
    FINANCIAL_ANALYSIS = "FINANCIAL_ANALYSIS"
    NLP_SUMMARIZATION = "NLP_SUMMARIZATION"
    VERDICT_PREDICTION = "VERDICT_PREDICTION"
    VISUALIZATION_PREP = "VISUALIZATION_PREP"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_size = Column(Integer)
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.UPLOADED)
    
    # JSON columns to store output of various agents
    metadata_json = Column(JSON, default={})
    extracted_text = Column(JSON, default={})
    financial_data = Column(JSON, default={})
    error_message = Column(String, nullable=True)
    analysis_results = Column(JSON, default={})
    nlp_summary = Column(JSON, default={})
    verdict = Column(JSON, default={})
