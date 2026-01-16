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
# This reads your .env file and makes variables available via os.getenv()
load_dotenv()

# =====================================================
# API KEYS
# =====================================================

# Your Anthropic API key (loaded from .env file for security)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

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

# Maximum tokens (words roughly) for each summary
MAX_TOKENS = 500

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
# ARTICLE SETTINGS
# =====================================================

# Maximum number of articles to fetch per source
MAX_ARTICLES_PER_SOURCE = 5

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
