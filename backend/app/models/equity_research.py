from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime, timezone
from app.models.base import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    isin = Column(String(50), nullable=True)
    exchange = Column(String(50), nullable=True, default="NSE")
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

class ResearchCache(Base):
    __tablename__ = "research_cache"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    module_name = Column(String(50), index=True, nullable=False)
    generated_report = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class APICache(Base):
    __tablename__ = "api_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(255), unique=True, index=True, nullable=False)
    response_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
