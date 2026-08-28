import os
from pydantic_settings import BaseSettings

# Resolve the SQLite database path relative to this file so it works
# regardless of the working directory (local dev or Render deployment).
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SQLITE_PATH = os.path.join(_BASE_DIR, "financial_analyzer.db")
_SQLITE_URL = f"sqlite:///{_SQLITE_PATH}"

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Financial Results Analyzer"

    # PostgreSQL settings are intentionally removed.
    # This app uses SQLite exclusively. The DATABASE_URL env var is only
    # honoured when it explicitly points to a SQLite URI; all other values
    # (postgres://, postgresql://, etc.) are ignored so that an expired or
    # missing Render PostgreSQL add-on cannot crash the application on boot.
    DATABASE_URL: str | None = None

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL and self.DATABASE_URL.startswith("sqlite"):
            return self.DATABASE_URL
        # Always fall back to the local SQLite file — never PostgreSQL.
        return _SQLITE_URL

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    PINECONE_API_KEY: str | None = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME: str | None = os.getenv("PINECONE_INDEX_NAME", "financial-reports-index")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    class Config:
        extra = "ignore"
        env_file = ".env" if os.path.exists(".env") else "../.env"

settings = Settings()
