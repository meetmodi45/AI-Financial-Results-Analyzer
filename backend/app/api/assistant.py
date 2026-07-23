import os
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
from app.core.config import settings
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Off-topic keyword blocklist — checked BEFORE calling the LLM (zero tokens)
# ---------------------------------------------------------------------------
_OFF_TOPIC_PATTERNS = re.compile(
    r"\b("
    r"python|javascript|typescript|java|c\+\+|c#|golang|rust|kotlin|swift|php|ruby|bash|sql\s+query|regex|algorithm|data\s*structure|machine\s*learning|neural\s*network|deep\s*learning|pytorch|tensorflow|numpy|pandas|react|angular|vue|django|flask|fastapi|docker|kubernetes|git|github|linux|windows|android|ios|api\s+design|database\s+design"
    r"|recipe|cooking|food|movie|song|music|lyrics|sport|cricket|football|travel|hotel|flight|weather|joke|poem|story|essay|translate|health|medicine|doctor"
    r")\b",
    re.IGNORECASE,
)

_OFF_TOPIC_REPLY = (
    "I'm a finance-focused assistant and can only help with questions about "
    "stocks, markets, financial concepts, company fundamentals, and investing. "
    "Please ask me something related to finance!"
)

# ---------------------------------------------------------------------------
# Tight system prompt — second layer of defence inside the LLM
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = (
    "You are a strict, concise financial AI assistant embedded in an equity research platform. "
    "Your ONLY job is to answer questions about: stocks, equity markets, financial statements, "
    "accounting concepts, investing strategies, company fundamentals, macroeconomics, and related finance topics. "
    "If the user asks ANYTHING unrelated to finance or business — such as coding, cooking, travel, sports, "
    "entertainment, health, or general knowledge — you MUST respond with exactly: "
    "'I can only help with finance and investing questions. Please ask me something related to markets or companies.' "
    "Do NOT attempt to answer off-topic questions under any circumstances.\n\n"
    "FORMATTING RULES — always follow these:\n"
    "- Never write dense paragraphs. Always use bullet points (•) or numbered lists.\n"
    "- Keep each bullet point to 1–2 short sentences maximum.\n"
    "- Add a blank line between sections or groups of points.\n"
    "- Use a bold heading (e.g. **What it means:**) before each section if the answer has multiple parts.\n"
    "- If the answer is a single fact, just state it in one sentence — no bullets needed.\n"
    "- Never use more than 120 words in total. Be sharp and scannable."
)


class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    answer: str

@router.post("/ask", response_model=ChatResponse)
async def ask_assistant(request: ChatRequest):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

    # ── Layer 1: Fast keyword check — no API call, zero tokens spent ────────
    if _OFF_TOPIC_PATTERNS.search(request.query):
        logger.info(f"[Assistant] Off-topic query blocked before LLM call: '{request.query[:80]}'")
        return ChatResponse(answer=_OFF_TOPIC_REPLY)

    try:
        # ── Layer 2: LLM call with strict system prompt ──────────────────────
        llm = ChatGroq(
            temperature=0.3,
            model_name=settings.GROQ_MODEL,
            api_key=api_key
        )

        messages = [SystemMessage(content=_SYSTEM_PROMPT)]

        # Add conversation history
        for msg in request.history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))

        # Add current query
        messages.append(HumanMessage(content=request.query))

        response = llm.invoke(messages)
        return ChatResponse(answer=response.content)

    except Exception as e:
        logger.error(f"Error in global assistant chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch answer from assistant")
