"""
Q&A API Routes

Endpoints for asking questions about articles with conversation memory.
"""

import sys
import os

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import get_app_state

router = APIRouter()


class QuestionRequest(BaseModel):
    """Request model for asking a question."""
    question: str


class QuestionResponse(BaseModel):
    """Response model for Q&A."""
    question: str
    answer: str
    article_count: int


@router.post("/qa/ask")
async def ask_question(request: QuestionRequest):
    """
    Ask a question about the loaded articles.

    The Q&A system remembers conversation history, allowing for
    follow-up questions that reference previous context.

    Example questions:
    - "What are the main technology news today?"
    - "Tell me more about that" (follow-up)
    - "How do the tech articles compare to business news?"
    """
    state = get_app_state()

    if not state.articles:
        raise HTTPException(
            status_code=400,
            detail="No articles loaded. Please fetch articles first."
        )

    try:
        answer = state.qa_chain.ask(request.question)

        return {
            "question": request.question,
            "answer": answer,
            "article_count": len(state.articles)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qa/history")
async def get_conversation_history():
    """
    Get the current conversation history.
    """
    state = get_app_state()
    history = state.qa_chain.get_history()

    formatted_history = []
    for msg in history:
        role = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
        formatted_history.append({
            "role": role,
            "content": msg.content
        })

    return {
        "history": formatted_history,
        "message_count": len(history)
    }


@router.delete("/qa/history")
async def clear_conversation_history():
    """
    Clear the conversation history.

    Use this to start a fresh conversation about the same articles.
    """
    state = get_app_state()
    state.qa_chain.clear_history()

    return {"message": "Conversation history cleared"}


@router.get("/qa/status")
async def get_qa_status():
    """
    Get the current status of the Q&A system.
    """
    state = get_app_state()

    return {
        "articles_loaded": len(state.articles),
        "history_length": len(state.qa_chain.get_history()),
        "ready": len(state.articles) > 0
    }
