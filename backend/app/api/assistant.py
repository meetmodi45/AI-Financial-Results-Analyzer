import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

logger = logging.getLogger(__name__)

router = APIRouter()

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
        
    try:
        # Initialize Groq Chat Model
        llm = ChatGroq(
            temperature=0.3,
            model_name="llama-3.3-70b-versatile",
            api_key=api_key
        )
        
        messages = [
            SystemMessage(content="You are a highly intelligent, concise financial AI assistant. "
                                  "Answer the user's questions about financial concepts, formulas, or general company information clearly and accurately. "
                                  "Keep your answers short and to the point, as they will be displayed in a small floating chat window.")
        ]
        
        # Add history
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
