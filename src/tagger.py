import asyncio
import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS, LLM_CONCURRENCY
from src.models import Article
from src.retry_utils import retried_invoke, retried_ainvoke
from src.timing import timeit

logger = logging.getLogger(__name__)


class ArticleTags(BaseModel):
    """Structured tagging output: keywords + named entities."""

    keywords: list[str] = Field(
        default_factory=list,
        description="3-5 main topics or themes, lowercase",
    )
    people: list[str] = Field(
        default_factory=list,
        description="Named people mentioned in the article",
    )
    organizations: list[str] = Field(
        default_factory=list,
        description="Named organizations mentioned in the article",
    )
    locations: list[str] = Field(
        default_factory=list,
        description="Named locations mentioned in the article",
    )

    @field_validator("keywords", mode="after")
    @classmethod
    def _lowercase_keywords(cls, value: list[str]) -> list[str]:
        return [kw.strip().lower() for kw in value if kw and kw.strip()]


TAGGING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert at analyzing news articles and extracting key information.

Your job is to extract:
1. KEYWORDS: 3-5 main topics or themes (lowercase)
2. PEOPLE: Named people mentioned
3. ORGANIZATIONS: Named companies, agencies, or other organizations mentioned
4. LOCATIONS: Named places mentioned

Rules:
- Keywords should be lowercase
- Entity names should be properly capitalized
- Don't include generic terms like "news" or "article" as keywords
- Only include entities that are specifically named in the text
- If a category has no items, return an empty list"""),

    ("human", """Extract keywords and entities from this article:

TITLE: {title}

CONTENT: {content}""")
])


def create_llm():
    """Create Claude LLM for tagging."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not found!")

    settings = LLM_SETTINGS["tag"]
    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=settings["temperature"],
        max_tokens=settings["max_tokens"],
        api_key=ANTHROPIC_API_KEY,
    )


_chain = None


def create_tagging_chain():
    """Return the (lazily-built) tagging chain.

    Uses LangChain's structured-output binding so Claude returns a validated
    :class:`ArticleTags` instance instead of free-form text.
    """
    global _chain
    if _chain is None:
        llm = create_llm().with_structured_output(ArticleTags)
        _chain = TAGGING_PROMPT | llm
    return _chain


def _short_content_fallback(article: Article) -> Article | None:
    """If the article's content is too short to tag, clear tags and return it."""
    content = article.summary or article.description or ""
    if not content or len(content.strip()) < 30:
        article.keywords = []
        article.people = []
        article.organizations = []
        article.locations = []
        return article
    return None


def _apply_tags(article: Article, tags: ArticleTags) -> None:
    article.keywords = tags.keywords
    article.people = tags.people
    article.organizations = tags.organizations
    article.locations = tags.locations

    if tags.keywords:
        logger.info("  Keywords: %s...", ", ".join(tags.keywords[:3]))
    if tags.people:
        logger.info("  People: %s", ", ".join(tags.people))


@timeit
def tag_article(article: Article) -> Article:
    """Populate ``article.keywords``/``.people``/``.organizations``/``.locations``."""

    chain = create_tagging_chain()

    fallback = _short_content_fallback(article)
    if fallback is not None:
        return fallback

    title = article.title or "Untitled"
    content = article.summary or article.description or ""

    logger.info("Tagging: %s...", title[:40])

    tags: ArticleTags = retried_invoke(chain, {
        "title": title,
        "content": content,
    })

    _apply_tags(article, tags)

    return article


@timeit
async def tag_article_async(article: Article) -> Article:
    """Async sibling of :func:`tag_article`."""

    chain = create_tagging_chain()

    fallback = _short_content_fallback(article)
    if fallback is not None:
        return fallback

    title = article.title or "Untitled"
    content = article.summary or article.description or ""

    logger.info("Tagging: %s...", title[:40])

    tags: ArticleTags = await retried_ainvoke(chain, {
        "title": title,
        "content": content,
    })

    _apply_tags(article, tags)

    return article


async def tag_articles_async(articles: list[Article]) -> list[Article]:
    """Tag every article concurrently, throttled by a semaphore."""

    logger.info("=" * 50)
    logger.info(
        "EXTRACTING KEYWORDS & ENTITIES (async, concurrency=%d)",
        LLM_CONCURRENCY,
    )
    logger.info("=" * 50)

    sem = asyncio.Semaphore(LLM_CONCURRENCY)
    total = len(articles)

    async def _one(idx: int, article: Article) -> Article:
        async with sem:
            logger.info("[%d/%d]", idx, total)
            try:
                return await tag_article_async(article)
            except Exception as e:
                logger.error("Error tagging: %s", e)
                article.keywords = []
                article.people = []
                article.organizations = []
                article.locations = []
                return article

    results = await asyncio.gather(
        *[_one(i, a) for i, a in enumerate(articles, 1)]
    )

    logger.info("=" * 50)
    logger.info("TAGGING COMPLETE")
    logger.info("=" * 50)

    return list(results)


def tag_articles(articles: list[Article]) -> list[Article]:
    """Sync wrapper around :func:`tag_articles_async` for non-async callers."""
    return asyncio.run(tag_articles_async(articles))


def display_tags(article: Article) -> None:
    """Log an article's tags in a readable format."""
    logger.info("📰 %s...", (article.title or "Untitled")[:50])

    keywords = article.keywords
    people = article.people
    organizations = article.organizations
    locations = article.locations

    if keywords:
        logger.info("   🏷️  Keywords: %s", ", ".join(keywords))
    if people:
        logger.info("   👤 People: %s", ", ".join(people))
    if organizations:
        logger.info("   🏢 Organizations: %s", ", ".join(organizations))
    if locations:
        logger.info("   📍 Locations: %s", ", ".join(locations))

    if not any([keywords, people, organizations, locations]):
        logger.info("   (No tags extracted)")


def get_all_keywords(articles: list[Article] | list[dict]) -> dict[str, int]:
    """Return a ``{keyword: count}`` dict sorted by frequency (descending).

    Accepts ``dict``-style fallback so that legacy tests calling this with
    raw dicts continue to work.
    """

    keyword_counts: dict[str, int] = {}

    for article in articles:
        if isinstance(article, dict):
            keywords = article.get("keywords", [])
        else:
            keywords = article.keywords

        for keyword in keywords:
            keyword = keyword.lower()
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

    return dict(
        sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
    )


def get_all_entities(articles: list[Article]) -> dict:
    """Return frequency-sorted entity counts grouped by people/orgs/locations."""

    entities: dict[str, dict[str, int]] = {
        "people": {},
        "organizations": {},
        "locations": {},
    }

    for article in articles:
        for person in article.people:
            entities["people"][person] = entities["people"].get(person, 0) + 1

        for org in article.organizations:
            entities["organizations"][org] = entities["organizations"].get(org, 0) + 1

        for loc in article.locations:
            entities["locations"][loc] = entities["locations"].get(loc, 0) + 1

    for key in entities:
        entities[key] = dict(
            sorted(entities[key].items(), key=lambda x: x[1], reverse=True)
        )

    return entities
