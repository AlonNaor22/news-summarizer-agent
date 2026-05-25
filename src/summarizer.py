# =====================================================
# SUMMARIZER MODULE
# =====================================================
#
# This module uses Claude (via LangChain) to summarize articles.
#
# LANGCHAIN CONCEPTS USED:
#
# 1. ChatAnthropic - The LLM (AI model) we talk to
# 2. ChatPromptTemplate - Instructions with placeholders
# 3. Chain (using |) - Connects prompt → LLM → output
#
# =====================================================

import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS
from src.models import Article

logger = logging.getLogger(__name__)


# =====================================================
# STEP 1: CREATE THE LLM (The AI Brain)
# =====================================================
#
# ChatAnthropic is LangChain's way to connect to Claude.
# We configure it with:
#   - model: Which Claude version to use
#   - temperature: Creativity level (0=focused, 1=creative)
#   - max_tokens: Maximum length of response
#
# =====================================================

def create_llm():
    """
    Create and return a configured Claude LLM instance.

    We put this in a function so we can:
    1. Check if API key exists before creating
    2. Reuse the same configuration everywhere
    """

    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY not found!\n"
            "Please create a .env file with your API key.\n"
            "See .env.example for the format."
        )

    settings = LLM_SETTINGS["summarize"]
    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=settings["temperature"],
        max_tokens=settings["max_tokens"],
        api_key=ANTHROPIC_API_KEY,
    )


# =====================================================
# STEP 2: CREATE THE PROMPT TEMPLATE
# =====================================================
#
# A prompt template is like a form letter with blanks.
#
# Example:
#   "Dear {name}, thank you for {action}."
#
# We fill in {name} and {action} later.
#
# For our summarizer, we have {title} and {content}.
#
# =====================================================

# This is the instruction we send to Claude
SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    # "system" message sets the AI's role and behavior
    ("system", """You are a professional news summarizer. Your job is to:
1. Read news articles carefully
2. Extract the most important information
3. Write clear, concise summaries

Guidelines:
- Keep summaries to 3-4 sentences
- Focus on WHO, WHAT, WHEN, WHERE, WHY
- Be objective and neutral
- Don't add opinions or speculation
- If the content is unclear, say so"""),

    # "human" message is what the user sends
    # {title} and {content} are placeholders we fill in later
    ("human", """Please summarize this news article:

TITLE: {title}

CONTENT: {content}

Provide a clear, concise summary:""")
])


# =====================================================
# STEP 3: CREATE THE CHAIN
# =====================================================
#
# A "chain" connects components together using the | operator.
#
# prompt | llm | parser
#    ↓      ↓      ↓
#  Fill   Send   Convert
#  in     to     response
#  vars   Claude to string
#
# =====================================================

# Lazily-built singleton chain. Reused across all articles in a fetch
# pipeline instead of paying the LLM client construction cost per article.
_chain = None


def create_summary_chain():
    """Return the (lazily-built) summarization chain."""
    global _chain
    if _chain is None:
        _chain = SUMMARY_PROMPT | create_llm() | StrOutputParser()
    return _chain


# =====================================================
# STEP 4: THE MAIN SUMMARIZE FUNCTION
# =====================================================

def summarize_article(article: Article) -> Article:
    """Set ``article.summary`` via Claude and return the article."""

    chain = create_summary_chain()

    content = article.description
    title = article.title or "Untitled"

    if not content or len(content.strip()) < 50:
        article.summary = "Summary unavailable - article content too short."
        return article

    logger.info("Summarizing: %s...", title[:50])

    summary = chain.invoke({
        "title": title,
        "content": content,
    })

    article.summary = summary

    return article


def summarize_articles(articles: list[Article]) -> list[Article]:
    """Summarize every article in ``articles``, returning the same list."""

    logger.info("=" * 50)
    logger.info("SUMMARIZING ARTICLES WITH CLAUDE")
    logger.info("=" * 50)

    summarized: list[Article] = []
    total = len(articles)

    for i, article in enumerate(articles, 1):
        logger.info("[%d/%d]", i, total)

        try:
            summarized_article = summarize_article(article)
            summarized.append(summarized_article)
        except Exception as e:
            logger.error("Error summarizing: %s", e)
            article.summary = f"Error: Could not summarize - {str(e)}"
            summarized.append(article)

    logger.info("=" * 50)
    logger.info("COMPLETED: %d articles summarized", len(summarized))
    logger.info("=" * 50)

    return summarized


def display_summary(article: Article) -> None:
    """Log a summarized article in a readable format."""
    logger.info("=" * 60)
    logger.info("📰 %s", article.title)
    logger.info("=" * 60)
    logger.info("Source: %s", article.source)
    logger.info("Published: %s", article.published or "Unknown")
    logger.info("📝 SUMMARY:")
    logger.info("   %s", article.summary or "No summary available")
    logger.info("🔗 %s", article.url)


# =====================================================
# TEST CODE
# =====================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING SUMMARIZER")
    print("="*60)

    # Test with a sample article
    test_article = Article(
        title="Global Leaders Meet to Discuss Climate Action",
        description="""
        World leaders from over 150 countries gathered in Geneva today
        for an emergency summit on climate change. The meeting, which
        was called after record-breaking temperatures were recorded
        across three continents last month, aims to establish new
        emissions targets and funding mechanisms for developing nations.

        The UN Secretary-General opened the summit with a stark warning:
        "We are running out of time. The decisions we make this week
        will determine the future of our planet." Key topics on the
        agenda include carbon pricing, renewable energy investment,
        and climate adaptation funding.

        Several major economies have already signaled their willingness
        to increase their commitments, though disagreements remain over
        how costs should be distributed between developed and developing
        nations.
        """,
        url="https://example.com/climate-summit",
        source="Test News",
        published="January 16, 2026",
    )

    print("\n--- Original Article ---")
    print(f"Title: {test_article.title}")
    print(f"Content length: {len(test_article.description)} characters")

    print("\n--- Calling Claude to Summarize ---")
    result = summarize_article(test_article)

    print("\n--- Result ---")
    display_summary(result)
