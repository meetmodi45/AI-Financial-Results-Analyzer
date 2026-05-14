from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes
from app.core.db import engine
from app.models.base import Base
from app.models.document import Document

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Financial Results Analyzer",
    description="Intelligent Earnings PDF Understanding System",
    version="1.0.0"
)

# CORS config to allow React frontend (Vite default is 5173, Next.js is 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "AI Financial Results Analyzer API is running"}
