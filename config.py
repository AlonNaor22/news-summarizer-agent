# =====================================================
# NEWS SUMMARIZER AGENT - CONFIGURATION
# =====================================================
#
# This file contains all the settings for our application.
# Having everything in one place makes it easy to adjust.
#
# =====================================================

import os
from dotenv import load_dotenv

# Load environment variables from .env file
# This reads your .env file and makes variables available via os.getenv().
# override=True so .env wins over empty env vars some shells inject
# (matches the fix in backend/main.py from 52e771f).
load_dotenv(override=True)

# =====================================================
# API KEYS
# =====================================================

# Your Anthropic API key (loaded from .env file for security)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# NewsAPI key (optional - for fetching from NewsAPI instead of RSS)
# Get a free key at: https://newsapi.org/
# Free tier: 100 requests/day
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# =====================================================
# CLAUDE MODEL SETTINGS
# =====================================================

# Which Claude model to use
# - "claude-sonnet-4-5-20250929": Best quality, more expensive
# - "claude-haiku-4-5-20251001": Faster and cheaper, good for simple tasks
MODEL_NAME = "claude-sonnet-4-5-20250929"

# Temperature: Controls creativity (0 = focused, 1 = creative)
# For news summaries, we want accuracy, so we use a low value
TEMPERATURE = 0.3

# Per-task LLM settings. Each task tunes temperature/max_tokens differently:
# - Classification tasks want low temperature for consistency
# - Generative tasks need more tokens for longer output
LLM_SETTINGS = {
    "summarize":  {"temperature": 0.3, "max_tokens": 500},
    "categorize": {"temperature": 0.1, "max_tokens": 50},
    "categorize_multi": {"temperature": 0.1, "max_tokens": 100},
    "tag":        {"temperature": 0.1, "max_tokens": 300},
    "sentiment":  {"temperature": 0.1, "max_tokens": 150},
    "trending":   {"temperature": 0.3, "max_tokens": 1000},
    "similarity": {"temperature": 0.2, "max_tokens": 1500},
    "comparison": {"temperature": 0.2, "max_tokens": 2000},
    "qa":         {"temperature": 0.3, "max_tokens": 1000},
}

# Kept for backwards compatibility with anything still importing MAX_TOKENS
MAX_TOKENS = LLM_SETTINGS["summarize"]["max_tokens"]

# Max simultaneous Claude requests when batching articles via asyncio.gather.
# Keeps us under Anthropic's rate limits while still giving a 5–10× speedup
# over the old sequential loop.
LLM_CONCURRENCY = 5

# =====================================================
# RSS FEED SOURCES (Free - No API Key Needed!)
# =====================================================

# These are free RSS feeds from major news outlets
# RSS = Really Simple Syndication - a standard format for news feeds
RSS_FEEDS = {
    "BBC News": "http://feeds.bbci.co.uk/news/rss.xml",
    "BBC Technology": "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "BBC Business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "NPR News": "https://feeds.npr.org/1001/rss.xml",
    "Reuters World": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
}

# =====================================================
# NEWSAPI SETTINGS (Alternative to RSS)
# =====================================================

# NewsAPI sources to fetch from
# Full list: https://newsapi.org/sources
NEWSAPI_SOURCES = [
    "bbc-news",
    "cnn",
    "techcrunch",
    "reuters",
    "the-verge",
]

# NewsAPI categories (use ONE when fetching top headlines)
# Options: business, entertainment, general, health, science, sports, technology
NEWSAPI_CATEGORIES = [
    "technology",
    "business",
    "science",
    "health",
]

# =====================================================
# ARTICLE SETTINGS
# =====================================================

# Maximum number of articles to fetch per source
MAX_ARTICLES_PER_SOURCE = 5

# Average reading speed used for "X min read" estimates
WORDS_PER_MINUTE = 200

# Similarity thresholds used by src/similarity.py and src/comparator.py
# Values are Jaccard scores in [0, 1].
SIMILARITY_THRESHOLDS = {
    "find_similar":   0.20,  # default threshold for find_similar_articles
    "find_similar_cli": 0.15,  # CLI uses a lower bar to surface more matches
    "related_pairs":  0.30,  # threshold for "are these articles related?"
    "same_story":     0.40,  # threshold for "is this the same story?"
}

# =====================================================
# CATEGORIES FOR CLASSIFICATION
# =====================================================

# These are the topics we'll classify articles into
CATEGORIES = [
    "Politics",
    "Business",
    "Technology",
    "Science",
    "Health",
    "Sports",
    "Entertainment",
    "World News",
    "Other"
]

# =====================================================
# MEMORY SETTINGS (for Q&A conversation)
# =====================================================

# How many previous exchanges to remember in conversation
MEMORY_SIZE = 10

# =====================================================
# WEB APP SETTINGS (for React frontend)
# =====================================================

# CORS allowed origins for the FastAPI backend
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative React port
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# Backend server settings
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8000

# Frontend server settings
FRONTEND_PORT = 5173
