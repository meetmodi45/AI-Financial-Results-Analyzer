import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Financial Results Analyzer"
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "financial_analyzer")
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            return db_url
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
    
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    PINECONE_API_KEY: str | None = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME: str | None = os.getenv("PINECONE_INDEX_NAME", "financial-reports-index")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    
    class Config:
        extra = "ignore"
        env_file = "../.env"

settings = Settings()
