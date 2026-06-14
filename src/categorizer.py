import asyncio
import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field, field_validator

from config import ANTHROPIC_API_KEY, MODEL_NAME, CATEGORIES, LLM_SETTINGS, LLM_CONCURRENCY
from src.models import Article
from src.retry_utils import retried_invoke, retried_ainvoke
from src.timing import timeit

logger = logging.getLogger(__name__)


class MultiCategoryResult(BaseModel):
    """Structured multi-category classification output."""

    primary: str = Field(
        description="The single most relevant category from the allowed list",
    )
    secondary: list[str] = Field(
        default_factory=list,
        description="Other relevant categories (may be empty)",
    )

    @field_validator("primary", mode="after")
    @classmethod
    def _normalize_primary(cls, value: str) -> str:
        return clean_category(value)

    @field_validator("secondary", mode="after")
    @classmethod
    def _normalize_secondary(cls, value: list[str]) -> list[str]:
        cleaned = []
        for item in value:
            if not item:
                continue
            canonical = clean_category(item)
            if canonical != "Other":
                cleaned.append(canonical)
        return cleaned


CATEGORIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a news article classifier. Your job is to categorize news articles into exactly ONE category.

Available categories:
{categories}

Rules:
1. Respond with ONLY the category name, nothing else
2. Choose the single most relevant category
3. If unsure, choose "Other"
4. Do not explain your choice, just output the category name"""),

    ("human", """Categorize this article:

TITLE: {title}

SUMMARY: {summary}

Category:""")
])


MULTI_CATEGORIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a news article classifier. Articles often cover multiple topics.
Your job is to identify the PRIMARY category and any SECONDARY categories.

Available categories:
{categories}

Rules:
1. PRIMARY = The main focus of the article (required, exactly one category from the list above)
2. SECONDARY = Other relevant topics (zero or more categories; return an empty list if none apply)
3. Pick category names exactly as written in the list"""),

    ("human", """Categorize this article:

TITLE: {title}

SUMMARY: {summary}""")
])


def create_llm():
    """Create Claude LLM instance."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not found! Check your .env file.")

    settings = LLM_SETTINGS["categorize"]
    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=settings["temperature"],
        max_tokens=settings["max_tokens"],
        api_key=ANTHROPIC_API_KEY,
    )


# Lazy singletons — chains are built once and reused for every article.
_single_chain = None
_multi_chain = None


def create_categorize_chain():
    """Return the (lazily-built) single-category chain."""
    global _single_chain
    if _single_chain is None:
        _single_chain = CATEGORIZE_PROMPT | create_llm() | StrOutputParser()
    return _single_chain


def clean_category(raw_category: str) -> str:
    """Normalize a raw LLM category response to one of the known CATEGORIES, or 'Other'."""
    cleaned = raw_category.strip().strip(".,!?\"'")

    for category in CATEGORIES:
        if category.lower() == cleaned.lower():
            return category
        if category.lower() in cleaned.lower():
            return category

    return "Other"


def _categories_str() -> str:
    return "\n".join(f"- {cat}" for cat in CATEGORIES)


def _missing_summary_fallback(article: Article) -> Article | None:
    """Default ``category`` to ``"Other"`` when there's no summary/description to classify."""
    summary = article.summary or article.description or ""
    if not summary:
        article.category = "Other"
        return article
    return None


@timeit
def categorize_article(article: Article) -> Article:
    """Set ``article.category`` via Claude and return the article."""
    chain = create_categorize_chain()

    fallback = _missing_summary_fallback(article)
    if fallback is not None:
        return fallback

    title = article.title or "Untitled"
    summary = article.summary or article.description or ""

    logger.info("Categorizing: %s...", title[:40])

    raw_response = retried_invoke(chain, {
        "categories": _categories_str(),
        "title": title,
        "summary": summary,
    })

    category = clean_category(raw_response)
    article.category = category

    logger.info("  -> %s", category)

    return article


@timeit
async def categorize_article_async(article: Article) -> Article:
    """Async sibling of :func:`categorize_article`."""
    chain = create_categorize_chain()

    fallback = _missing_summary_fallback(article)
    if fallback is not None:
        return fallback

    title = article.title or "Untitled"
    summary = article.summary or article.description or ""

    logger.info("Categorizing: %s...", title[:40])

    raw_response = await retried_ainvoke(chain, {
        "categories": _categories_str(),
        "title": title,
        "summary": summary,
    })

    category = clean_category(raw_response)
    article.category = category

    logger.info("  -> %s", category)

    return article


async def categorize_articles_async(
    articles: list[Article], sem: asyncio.Semaphore | None = None
) -> list[Article]:
    """Categorize every article concurrently, throttled by a semaphore.

    ``sem`` lets a caller share one concurrency limit across stages that run at
    the same time (see :func:`src.pipeline.process_articles_async`). When
    omitted, the stage uses its own ``LLM_CONCURRENCY`` semaphore.
    """
    logger.info("=" * 50)
    logger.info(
        "CATEGORIZING ARTICLES (async, concurrency=%d)",
        LLM_CONCURRENCY,
    )
    logger.info("=" * 50)

    sem = sem or asyncio.Semaphore(LLM_CONCURRENCY)
    total = len(articles)

    async def _one(idx: int, article: Article) -> Article:
        async with sem:
            logger.info("[%d/%d]", idx, total)
            try:
                return await categorize_article_async(article)
            except Exception as e:
                logger.error("Error categorizing: %s", e)
                article.category = "Other"
                return article

    results = await asyncio.gather(
        *[_one(i, a) for i, a in enumerate(articles, 1)]
    )

    logger.info("=" * 50)
    logger.info("CATEGORIZATION COMPLETE")
    logger.info("=" * 50)

    return list(results)


def categorize_articles(articles: list[Article]) -> list[Article]:
    """Sync wrapper around :func:`categorize_articles_async` for non-async callers."""
    return asyncio.run(categorize_articles_async(articles))



def create_multi_categorize_chain():
    """Return the (lazily-built) multi-category chain.

    Uses LangChain's structured-output binding so Claude returns a validated
    :class:`MultiCategoryResult` instance instead of free-form text.
    """
    global _multi_chain
    if _multi_chain is None:
        settings = LLM_SETTINGS["categorize_multi"]
        llm = ChatAnthropic(
            model=MODEL_NAME,
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            api_key=ANTHROPIC_API_KEY,
        )
        _multi_chain = MULTI_CATEGORIZE_PROMPT | llm.with_structured_output(MultiCategoryResult)
    return _multi_chain


def _missing_summary_fallback_multi(article: Article) -> Article | None:
    summary = article.summary or article.description or ""
    if not summary:
        article.category = "Other"
        article.secondary_categories = []
        return article
    return None


def categorize_article_multi(article: Article) -> Article:
    """Set ``article.category`` and ``article.secondary_categories`` from Claude."""
    chain = create_multi_categorize_chain()

    fallback = _missing_summary_fallback_multi(article)
    if fallback is not None:
        return fallback

    title = article.title or "Untitled"
    summary = article.summary or article.description or ""

    logger.info("Categorizing: %s...", title[:40])

    parsed: MultiCategoryResult = retried_invoke(chain, {
        "categories": _categories_str(),
        "title": title,
        "summary": summary,
    })

    article.category = parsed.primary
    article.secondary_categories = parsed.secondary

    secondary_str = ", ".join(parsed.secondary) if parsed.secondary else "None"
    logger.info("  -> Primary: %s", parsed.primary)
    logger.info("  -> Secondary: %s", secondary_str)

    return article


async def categorize_article_multi_async(article: Article) -> Article:
    """Async sibling of :func:`categorize_article_multi`."""
    chain = create_multi_categorize_chain()

    fallback = _missing_summary_fallback_multi(article)
    if fallback is not None:
        return fallback

    title = article.title or "Untitled"
    summary = article.summary or article.description or ""

    logger.info("Categorizing: %s...", title[:40])

    parsed: MultiCategoryResult = await retried_ainvoke(chain, {
        "categories": _categories_str(),
        "title": title,
        "summary": summary,
    })

    article.category = parsed.primary
    article.secondary_categories = parsed.secondary

    secondary_str = ", ".join(parsed.secondary) if parsed.secondary else "None"
    logger.info("  -> Primary: %s", parsed.primary)
    logger.info("  -> Secondary: %s", secondary_str)

    return article


async def categorize_articles_multi_async(articles: list[Article]) -> list[Article]:
    """Apply multi-category classification concurrently."""
    logger.info("=" * 50)
    logger.info(
        "CATEGORIZING ARTICLES (Multi-Category, async, concurrency=%d)",
        LLM_CONCURRENCY,
    )
    logger.info("=" * 50)

    sem = asyncio.Semaphore(LLM_CONCURRENCY)
    total = len(articles)

    async def _one(idx: int, article: Article) -> Article:
        async with sem:
            logger.info("[%d/%d]", idx, total)
            try:
                return await categorize_article_multi_async(article)
            except Exception as e:
                logger.error("Error categorizing: %s", e)
                article.category = "Other"
                article.secondary_categories = []
                return article

    results = await asyncio.gather(
        *[_one(i, a) for i, a in enumerate(articles, 1)]
    )

    logger.info("=" * 50)
    logger.info("CATEGORIZATION COMPLETE")
    logger.info("=" * 50)

    return list(results)


def categorize_articles_multi(articles: list[Article]) -> list[Article]:
    """Sync wrapper around :func:`categorize_articles_multi_async`."""
    return asyncio.run(categorize_articles_multi_async(articles))


def display_multi_categories(articles: list[Article]) -> None:
    """Log articles along with their primary + secondary categories."""
    logger.info("=" * 60)
    logger.info("ARTICLES WITH MULTIPLE CATEGORIES")
    logger.info("=" * 60)

    for article in articles:
        logger.info("📰 %s...", article.title[:50])
        logger.info("   Primary:   %s", article.category or "Other")

        secondary = article.secondary_categories
        if secondary:
            logger.info("   Secondary: %s", ", ".join(secondary))
        else:
            logger.info("   Secondary: None")


def group_by_category(articles: list[Article]) -> dict[str, list[Article]]:
    """Group articles into a ``{category: [articles]}`` dict."""
    grouped: dict[str, list[Article]] = {}

    for article in articles:
        category = article.category or "Other"

        if category not in grouped:
            grouped[category] = []

        grouped[category].append(article)

    return grouped


def display_by_category(articles: list[Article]) -> None:
    """Log articles grouped by category."""
    grouped = group_by_category(articles)

    logger.info("=" * 60)
    logger.info("ARTICLES BY CATEGORY")
    logger.info("=" * 60)

    for category, category_articles in grouped.items():
        logger.info("📁 %s (%d articles)", category.upper(), len(category_articles))
        logger.info("-" * 40)

        for article in category_articles:
            logger.info("  • %s...", article.title[:50])
            logger.info("    Source: %s", article.source)
