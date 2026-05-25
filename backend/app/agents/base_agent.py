import os
import asyncio
from typing import AsyncGenerator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy.orm import Session
from app.models.equity_research import ResearchCache
from app.core.config import settings
from datetime import datetime, timezone

class BaseResearchAgent:
    def __init__(self):
        # Primary Model: Gemini 2.0 Flash (or whatever the user has API key for, 
        # usually falls back to models/gemini-1.5-flash if 2.0 is not available in their region yet)
        self.primary_llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            temperature=0.2,
            api_key=settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        )
        
        # Fallback Model: Groq Llama 3
        self.fallback_llm = ChatGroq(
            model="llama-3.3-70b-versatile", 
            temperature=0.2,
            api_key=settings.GROQ_API_KEY
        )
        
        # Combine them with Langchain's fallback mechanism
        self.llm = self.primary_llm.with_fallbacks([self.fallback_llm])

    async def fetch_data(self, symbol: str, db: Session) -> dict:
        """
        Override this method in subclasses to fetch specific FMP/Finnhub data.
        Returns a dictionary of data to be injected into the prompt.
        """
        raise NotImplementedError

    def get_prompt_template(self) -> str:
        """
        Override this method to return the specific institutional prompt for the module.
        """
        raise NotImplementedError
        
    async def analyze_stream(self, symbol: str, module_name: str, db: Session) -> AsyncGenerator[str, None]:
        """
        Main entrypoint for the streaming endpoint.
        """
        # 1. Bypass checking the cache per user request
        # cached_report = db.query(ResearchCache).filter(
        #     ResearchCache.symbol == symbol,
        #     ResearchCache.module_name == module_name
        # ).first()
        # 
        # if cached_report:
        #     age = datetime.now(timezone.utc) - cached_report.created_at
        #     if age.days < 10:
        #         # Stream the cached report chunk by chunk to simulate generation
        #         chunk_size = 50
        #         report = cached_report.generated_report
        #         import json
        #         for i in range(0, len(report), chunk_size):
        #             chunk = report[i:i+chunk_size]
        #             yield f"data: {json.dumps({'content': chunk})}\n\n"
        #             await asyncio.sleep(0.01)
        #         yield "data: [DONE]\n\n"
        #         return

        # Fetch required data concurrently
        data = await self.fetch_data(symbol, db)
        
        # Format prompt
        system_prompt = "You are a Senior Equity Research Analyst at a top-tier institutional firm."
        human_prompt = self.get_prompt_template().format(**data, symbol=symbol)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        # Stream the response
        full_response = ""
        try:
            import json
            try:
                # Attempt primary LLM (Gemini)
                async for chunk in self.primary_llm.astream(messages):
                    if chunk.content:
                        full_response += chunk.content
                        yield f"data: {json.dumps({'content': chunk.content})}\n\n"
            except Exception as primary_e:
                print(f"Primary LLM failed ({primary_e}). Triggering Groq Fallback...")
                # Attempt fallback LLM (Groq) on rate limit or crash
                async for chunk in self.fallback_llm.astream(messages):
                    if chunk.content:
                        full_response += chunk.content
                        yield f"data: {json.dumps({'content': chunk.content})}\n\n"
        except Exception as e:
            import json
            yield f"data: {json.dumps({'error': f'Error during generation: {str(e)}'})}\n\n"
                
        # Save full_response to ResearchCache in Postgres bypassed per user request
        # if full_response:
        #     if cached_report:
        #         cached_report.generated_report = full_response
        #         cached_report.created_at = datetime.now(timezone.utc)
        #     else:
        #         new_cache = ResearchCache(
        #             symbol=symbol,
        #             module_name=module_name,
        #             generated_report=full_response
        #         )
        #         db.add(new_cache)
        #     try:
        #         db.commit()
        #     except Exception:
        #         db.rollback()
        
        yield "data: [DONE]\n\n"

    async def analyze(self, symbol: str, module_name: str, db: Session) -> str:
        """
        Non-streaming version: returns the complete analysis as a plain string.
        Used by the JSON endpoint to avoid SSE/nginx buffering issues on Render.
        """
        data = await self.fetch_data(symbol, db)

        system_prompt = "You are a Senior Equity Research Analyst at a top-tier institutional firm."
        human_prompt = self.get_prompt_template().format(**data, symbol=symbol)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]

        try:
            response = await self.primary_llm.ainvoke(messages)
            return response.content
        except Exception as primary_e:
            print(f"Primary LLM failed ({primary_e}). Triggering Groq fallback...")
            response = await self.fallback_llm.ainvoke(messages)
            return response.content
