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
        # Primary Model: Gemini
        self.primary_llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL, 
            temperature=0.2,
            max_tokens=1000,
            api_key=settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        )
        
        # Fallback Model: Groq (openai/gpt-oss-20b)
        self.fallback_llm = ChatGroq(
            model=settings.GROQ_MODEL, 
            temperature=0.2,
            max_tokens=1000,
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
        
    # How many days each module's LLM output is considered fresh
    CACHE_TTL_DAYS = {
        "business":  7,   # business model rarely changes
        "moat":      7,   # moat/competition analysis is stable
        "financials": 3,  # results change each quarter
        "valuation":  1,  # price-based — daily staleness
        "technical":  1,  # technical picture changes daily
        "news":       0,  # always fresh (no caching)
    }

    async def analyze_stream(self, symbol: str, module_name: str, db: Session) -> AsyncGenerator[str, None]:
        """
        Main entrypoint for the streaming endpoint.
        Checks ResearchCache first; streams cached report instantly if still fresh.
        Otherwise runs the LLM, streams live, and saves result to cache.
        """
        import json

        ttl_days = self.CACHE_TTL_DAYS.get(module_name.lower(), 1)

        # ── 1. Cache read ──────────────────────────────────────────────────────
        cached_report = None
        if ttl_days > 0:
            cached_report = db.query(ResearchCache).filter(
                ResearchCache.symbol == symbol,
                ResearchCache.module_name == module_name
            ).first()

            if cached_report and cached_report.generated_report:
                # Normalise timezone before comparing
                created = cached_report.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                age_days = (datetime.now(timezone.utc) - created).days

                if age_days < ttl_days:
                    # Serve from cache — stream in chunks so frontend behaves normally
                    yield f"data: {json.dumps({'clear': True})}\n\n"
                    report = cached_report.generated_report
                    chunk_size = 60
                    for i in range(0, len(report), chunk_size):
                        yield f"data: {json.dumps({'content': report[i:i+chunk_size]})}\n\n"
                        await asyncio.sleep(0.005)
                    yield "data: [DONE]\n\n"
                    return

        # ── 2. Cache miss — fetch data & call LLM ─────────────────────────────
        data = await self.fetch_data(symbol, db)

        system_prompt = "You are a Senior Equity Research Analyst at a top-tier institutional firm."
        human_prompt = self.get_prompt_template().format(**data, symbol=symbol)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]

        yield f"data: {json.dumps({'clear': True})}\n\n"

        full_response = ""
        try:
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
            yield f"data: {json.dumps({'error': f'Error during generation: {str(e)}'})}\n\n"

        # ── 3. Save to cache ──────────────────────────────────────────────────
        if full_response and ttl_days > 0:
            try:
                if cached_report:
                    cached_report.generated_report = full_response
                    cached_report.created_at = datetime.now(timezone.utc)
                else:
                    db.add(ResearchCache(
                        symbol=symbol,
                        module_name=module_name,
                        generated_report=full_response
                    ))
                db.commit()
            except Exception:
                db.rollback()

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