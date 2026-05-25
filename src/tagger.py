# =====================================================
# TAGGER MODULE
# =====================================================
#
# This module extracts keywords and named entities from articles.
#
# WHAT ARE ENTITIES?
# ------------------
# Named entities are specific things mentioned in text:
# - PERSON: People's names (Elon Musk, Joe Biden)
# - ORGANIZATION: Companies, agencies (Apple, NASA, UN)
# - LOCATION: Places (California, London, Mount Everest)
#
# WHAT ARE KEYWORDS?
# ------------------
# Keywords are the main topics or themes of an article:
# - "artificial intelligence", "climate change", "stock market"
#
# LANGCHAIN CONCEPT: Structured Output
# ------------------------------------
# We need Claude to return data in a specific format.
# We do this by:
# 1. Giving very specific instructions in the prompt
# 2. Parsing the response to extract the structured data
#
# =====================================================

import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS
from src.models import Article

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


def tag_article(article: Article) -> Article:
    """Populate ``article.keywords``/``.people``/``.organizations``/``.locations``."""

    chain = create_tagging_chain()

    title = article.title or "Untitled"
    content = article.summary or article.description or ""

    if not content or len(content.strip()) < 30:
        article.keywords = []
        article.people = []
        article.organizations = []
        article.locations = []
        return article

    logger.info("Tagging: %s...", title[:40])

    tags: ArticleTags = chain.invoke({
        "title": title,
        "content": content,
    })

    article.keywords = tags.keywords
    article.people = tags.people
    article.organizations = tags.organizations
    article.locations = tags.locations

    if tags.keywords:
        logger.info("  Keywords: %s...", ", ".join(tags.keywords[:3]))
    if tags.people:
        logger.info("  People: %s", ", ".join(tags.people))

    return article


def tag_articles(articles: list[Article]) -> list[Article]:
    """Apply tagging to every article, falling back to empty lists on errors."""

    logger.info("=" * 50)
    logger.info("EXTRACTING KEYWORDS & ENTITIES")
    logger.info("=" * 50)

    tagged: list[Article] = []
    total = len(articles)

    for i, article in enumerate(articles, 1):
        logger.info("[%d/%d]", i, total)

        try:
            tagged_article = tag_article(article)
            tagged.append(tagged_article)
        except Exception as e:
            logger.error("Error tagging: %s", e)
            article.keywords = []
            article.people = []
            article.organizations = []
            article.locations = []
            tagged.append(article)

    logger.info("=" * 50)
    logger.info("TAGGING COMPLETE")
    logger.info("=" * 50)

    return tagged


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


# =====================================================
# TEST CODE
# =====================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING TAGGER")
    print("="*60)

    test_articles = [
        Article(
            title="Apple CEO Tim Cook Announces New AI Features at WWDC in California",
            summary="""Apple's CEO Tim Cook unveiled groundbreaking AI capabilities
            at the Worldwide Developers Conference in Cupertino, California. The new
            features, developed in partnership with OpenAI, will be available on iPhone,
            iPad, and Mac devices. Microsoft and Google are expected to respond with
            their own announcements at upcoming events in Seattle and New York.""",
            source="Test",
            url="",
        ),
        Article(
            title="Climate Summit: World Leaders Meet in Paris",
            summary="""Representatives from the United Nations gathered in Paris
            for an emergency climate summit. French President Emmanuel Macron and
            UN Secretary-General António Guterres called for immediate action on
            reducing carbon emissions. The European Union announced new green energy
            initiatives.""",
            source="Test",
            url="",
        ),
    ]

    print("\n--- Tagging Articles ---")
    tagged = tag_articles(test_articles)

    print("\n--- Results ---")
    for article in tagged:
        display_tags(article)

    print("\n--- Keyword Frequency ---")
    keywords = get_all_keywords(tagged)
    for kw, count in keywords.items():
        print(f"  {kw}: {count}")

    print("\n--- Entity Frequency ---")
    entities = get_all_entities(tagged)
    print("\nPeople:")
    for name, count in entities["people"].items():
        print(f"  {name}: {count}")
    print("\nOrganizations:")
    for name, count in entities["organizations"].items():
        print(f"  {name}: {count}")
    print("\nLocations:")
    for name, count in entities["locations"].items():
        print(f"  {name}: {count}")
