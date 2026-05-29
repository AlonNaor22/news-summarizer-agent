import asyncio
import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS, LLM_CONCURRENCY
from src.models import Article
from src.retry_utils import retried_invoke, retried_ainvoke
from src.timing import timeit

logger = logging.getLogger(__name__)



def create_llm():
    """Create and return a configured Claude LLM instance."""

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


SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
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

    ("human", """Please summarize this news article:

TITLE: {title}

CONTENT: {content}

Provide a clear, concise summary:""")
])


# Lazily-built singleton: reused across all articles instead of paying the LLM
# client construction cost per article.
_chain = None


def create_summary_chain():
    """Return the (lazily-built) summarization chain."""
    global _chain
    if _chain is None:
        _chain = SUMMARY_PROMPT | create_llm() | StrOutputParser()
    return _chain


def _short_content_fallback(article: Article) -> Article | None:
    """If the article's body is too short to summarize, set a fallback and return it."""
    content = article.description
    if not content or len(content.strip()) < 50:
        article.summary = "Summary unavailable - article content too short."
        return article
    return None


@timeit
def summarize_article(article: Article) -> Article:
    """Set ``article.summary`` via Claude and return the article."""

    chain = create_summary_chain()

    fallback = _short_content_fallback(article)
    if fallback is not None:
        return fallback

    title = article.title or "Untitled"
    logger.info("Summarizing: %s...", title[:50])

    summary = retried_invoke(chain, {
        "title": title,
        "content": article.description,
    })

    article.summary = summary

    return article


@timeit
async def summarize_article_async(article: Article) -> Article:
    """Async sibling of :func:`summarize_article` — awaits Claude's async API."""

    chain = create_summary_chain()

    fallback = _short_content_fallback(article)
    if fallback is not None:
        return fallback

    title = article.title or "Untitled"
    logger.info("Summarizing: %s...", title[:50])

    summary = await retried_ainvoke(chain, {
        "title": title,
        "content": article.description,
    })

    article.summary = summary

    return article


async def summarize_articles_async(articles: list[Article]) -> list[Article]:
    """Summarize every article concurrently, throttled by a semaphore."""

    logger.info("=" * 50)
    logger.info(
        "SUMMARIZING ARTICLES WITH CLAUDE (async, concurrency=%d)",
        LLM_CONCURRENCY,
    )
    logger.info("=" * 50)

    sem = asyncio.Semaphore(LLM_CONCURRENCY)
    total = len(articles)

    async def _one(idx: int, article: Article) -> Article:
        async with sem:
            logger.info("[%d/%d]", idx, total)
            try:
                return await summarize_article_async(article)
            except Exception as e:
                logger.error("Error summarizing: %s", e)
                article.summary = f"Error: Could not summarize - {e}"
                return article

    results = await asyncio.gather(
        *[_one(i, a) for i, a in enumerate(articles, 1)]
    )

    logger.info("=" * 50)
    logger.info("COMPLETED: %d articles summarized", len(results))
    logger.info("=" * 50)

    return list(results)


def summarize_articles(articles: list[Article]) -> list[Article]:
    """Sync wrapper around :func:`summarize_articles_async` for non-async callers."""
    return asyncio.run(summarize_articles_async(articles))


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
