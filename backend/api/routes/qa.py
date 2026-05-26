"""Q&A API routes — asking questions about articles with conversation memory."""

import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from api.dependencies import get_app_state
from api.limiter import limiter

router = APIRouter()


class QuestionRequest(BaseModel):
    """Request model for asking a question."""
    question: str = Field(..., min_length=1, max_length=2000)


class QuestionResponse(BaseModel):
    """Response model for Q&A."""
    question: str
    answer: str
    article_count: int


@router.post("/qa/ask")
@limiter.limit("30/minute")
def ask_question(request: Request, body: QuestionRequest):
    """Ask a question about the loaded articles with conversation memory."""
    state = get_app_state()

    if not state.articles:
        raise HTTPException(
            status_code=400,
            detail="No articles loaded. Please fetch articles first."
        )

    try:
        answer = state.qa_chain.ask(body.question)

        return {
            "question": body.question,
            "answer": answer,
            "article_count": len(state.articles)
        }

    except Exception:
        request_id = uuid.uuid4()
        logger.exception("Unhandled error in ask_question [request_id=%s]", request_id)
        raise HTTPException(status_code=500, detail=f"Internal error answering question (id={request_id})")


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
