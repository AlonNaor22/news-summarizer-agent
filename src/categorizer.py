import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field, field_validator

from config import ANTHROPIC_API_KEY, MODEL_NAME, CATEGORIES, LLM_SETTINGS
from src.models import Article
from src.retry_utils import retried_invoke
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


@timeit
def categorize_article(article: Article) -> Article:
    """Set ``article.category`` via Claude and return the article."""
    chain = create_categorize_chain()

    title = article.title or "Untitled"
    summary = article.summary or article.description or ""

    if not summary:
        article.category = "Other"
        return article

    logger.info("Categorizing: %s...", title[:40])

    categories_str = "\n".join(f"- {cat}" for cat in CATEGORIES)

    raw_response = retried_invoke(chain, {
        "categories": categories_str,
        "title": title,
        "summary": summary,
    })

    category = clean_category(raw_response)
    article.category = category

    logger.info("  -> %s", category)

    return article


def categorize_articles(articles: list[Article]) -> list[Article]:
    """Categorize every article, falling back to ``"Other"`` on errors."""
    logger.info("=" * 50)
    logger.info("CATEGORIZING ARTICLES")
    logger.info("=" * 50)

    categorized: list[Article] = []
    total = len(articles)

    for i, article in enumerate(articles, 1):
        logger.info("[%d/%d]", i, total)

        try:
            categorized_article = categorize_article(article)
            categorized.append(categorized_article)
        except Exception as e:
            logger.error("Error categorizing: %s", e)
            article.category = "Other"
            categorized.append(article)

    logger.info("=" * 50)
    logger.info("CATEGORIZATION COMPLETE")
    logger.info("=" * 50)

    return categorized



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


def categorize_article_multi(article: Article) -> Article:
    """Set ``article.category`` and ``article.secondary_categories`` from Claude."""
    chain = create_multi_categorize_chain()

    title = article.title or "Untitled"
    summary = article.summary or article.description or ""

    if not summary:
        article.category = "Other"
        article.secondary_categories = []
        return article

    logger.info("Categorizing: %s...", title[:40])

    categories_str = "\n".join(f"- {cat}" for cat in CATEGORIES)

    parsed: MultiCategoryResult = retried_invoke(chain, {
        "categories": categories_str,
        "title": title,
        "summary": summary,
    })

    article.category = parsed.primary
    article.secondary_categories = parsed.secondary

    secondary_str = ", ".join(parsed.secondary) if parsed.secondary else "None"
    logger.info("  -> Primary: %s", parsed.primary)
    logger.info("  -> Secondary: %s", secondary_str)

    return article


def categorize_articles_multi(articles: list[Article]) -> list[Article]:
    """Apply multi-category classification to every article."""
    logger.info("=" * 50)
    logger.info("CATEGORIZING ARTICLES (Multi-Category)")
    logger.info("=" * 50)

    categorized: list[Article] = []
    total = len(articles)

    for i, article in enumerate(articles, 1):
        logger.info("[%d/%d]", i, total)

        try:
            categorized_article = categorize_article_multi(article)
            categorized.append(categorized_article)
        except Exception as e:
            logger.error("Error categorizing: %s", e)
            article.category = "Other"
            article.secondary_categories = []
            categorized.append(article)

    logger.info("=" * 50)
    logger.info("CATEGORIZATION COMPLETE")
    logger.info("=" * 50)

    return categorized


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

