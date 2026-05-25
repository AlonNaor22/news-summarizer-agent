"""
News Summarizer Agent - FastAPI Backend

This is the main entry point for the FastAPI application.
It provides REST API endpoints for the News Summarizer Agent.

Run with:
    uvicorn backend.main:app --reload --port 8000

Or from the backend directory:
    uvicorn main:app --reload --port 8000
"""

import logging
import sys
import os
from dotenv import load_dotenv

# Get the project root directory (parent of backend)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# Add both to path for imports
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Load .env from project root before any module that reads env vars
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import articles, sentiment, trending, similarity, comparison, qa
from config import CORS_ORIGINS

# Create FastAPI app
app = FastAPI(
    title="News Summarizer Agent API",
    description="API for fetching, summarizing, and analyzing news articles",
    version="1.0.0"
)

# Configure CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(articles.router, prefix="/api", tags=["Articles"])
app.include_router(sentiment.router, prefix="/api", tags=["Sentiment"])
app.include_router(trending.router, prefix="/api", tags=["Trending"])
app.include_router(similarity.router, prefix="/api", tags=["Similarity"])
app.include_router(comparison.router, prefix="/api", tags=["Comparison"])
app.include_router(qa.router, prefix="/api", tags=["Q&A"])


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "News Summarizer Agent API",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
