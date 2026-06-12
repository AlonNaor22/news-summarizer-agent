"""Q&A API routes — asking questions about articles with conversation memory."""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.dependencies import AppState, get_session_state
from api.limiter import limiter

logger = logging.getLogger(__name__)

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
def ask_question(
    request: Request,
    body: QuestionRequest,
    state: AppState = Depends(get_session_state),
):
    """Ask a question about the loaded articles with conversation memory."""
    if not state.articles:
        raise HTTPException(
            status_code=400,
            detail="No articles loaded. Please fetch articles first."
        )

    try:
        answer = state.qa_chain.ask(body.question)
        state.persist_qa_exchange(body.question, answer)

        return {
            "question": body.question,
            "answer": answer,
            "article_count": len(state.articles)
        }

    except Exception:
        request_id = uuid.uuid4()
        logger.exception("Unhandled error in ask_question [request_id=%s]", request_id)
        raise HTTPException(status_code=500, detail=f"Internal error answering question (id={request_id})")


def _sse_event(event_type: str, payload: dict) -> bytes:
    """Encode a single SSE message: `event: <type>` then `data: <json>` then blank line."""
    body = json.dumps(payload, ensure_ascii=False)
    return f"event: {event_type}\ndata: {body}\n\n".encode("utf-8")


@router.post("/qa/ask/stream")
@limiter.limit("30/minute")
async def ask_question_stream(
    request: Request,
    body: QuestionRequest,
    state: AppState = Depends(get_session_state),
):
    """Stream a Q&A answer over Server-Sent Events.

    Emits one `event: chunk` per token (with `{"text": "..."}`), then a final
    `event: done` carrying `{"article_count": N}`. On error, emits
    `event: error` with `{"detail": "..."}` and stops.
    """
    if not state.articles:
        raise HTTPException(
            status_code=400,
            detail="No articles loaded. Please fetch articles first.",
        )

    qa_chain = state.qa_chain
    question = body.question
    article_count = len(state.articles)

    async def event_source():
        collected: list[str] = []
        try:
            async for chunk in qa_chain.astream(question):
                if chunk:
                    collected.append(chunk)
                    yield _sse_event("chunk", {"text": chunk})
            yield _sse_event("done", {"article_count": article_count})
            state.persist_qa_exchange(question, "".join(collected))
        except Exception:
            request_id = uuid.uuid4()
            logger.exception(
                "Unhandled error in ask_question_stream [request_id=%s]", request_id
            )
            yield _sse_event(
                "error",
                {"detail": f"Internal error answering question (id={request_id})"},
            )

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/qa/history")
async def get_conversation_history(state: AppState = Depends(get_session_state)):
    """Return the current conversation history as role/content pairs."""
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
async def clear_conversation_history(state: AppState = Depends(get_session_state)):
    """Clear the conversation history (keeps the loaded articles)."""
    state.clear_qa_history()

    return {"message": "Conversation history cleared"}


@router.get("/qa/status")
async def get_qa_status(state: AppState = Depends(get_session_state)):
    """Return Q&A readiness: article count, history length, and ready flag."""
    return {
        "articles_loaded": len(state.articles),
        "history_length": len(state.qa_chain.get_history()),
        "ready": len(state.articles) > 0
    }
