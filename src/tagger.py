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

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS
from src.models import Article


# =====================================================
# THE TAGGING PROMPT
# =====================================================
#
# This prompt asks Claude to extract keywords and entities
# in a SPECIFIC format that we can parse.
#
# Key technique: We give Claude an exact output format
# and examples to follow. This is called "few-shot prompting".
#
# =====================================================

TAGGING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert at analyzing news articles and extracting key information.

Your job is to extract:
1. KEYWORDS: 3-5 main topics or themes (lowercase, comma-separated)
2. ENTITIES: Named people, organizations, and locations mentioned

You MUST respond in this EXACT format:
KEYWORDS: keyword1, keyword2, keyword3
PEOPLE: person1, person2 (or "None" if no people mentioned)
ORGANIZATIONS: org1, org2 (or "None" if no organizations mentioned)
LOCATIONS: location1, location2 (or "None" if no locations mentioned)

Example response:
KEYWORDS: artificial intelligence, technology, smartphones
PEOPLE: Tim Cook, Elon Musk
ORGANIZATIONS: Apple, Tesla, OpenAI
LOCATIONS: California, Silicon Valley

Rules:
- Keywords should be lowercase
- Entity names should be properly capitalized
- Don't include generic terms like "news" or "article" as keywords
- Only include entities that are specifically named in the text
- If a category has no items, write "None" """),

    ("human", """Extract keywords and entities from this article:

TITLE: {title}

CONTENT: {content}

Extract the information:""")
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
    """Return the (lazily-built) tagging chain."""
    global _chain
    if _chain is None:
        _chain = TAGGING_PROMPT | create_llm() | StrOutputParser()
    return _chain


def parse_tagging_response(response: str) -> dict:
    """
    Parse Claude's response into a structured dictionary.

    This function takes the raw text response from Claude
    and converts it into a Python dictionary we can use.

    INPUT (from Claude):
    --------------------
    "KEYWORDS: ai, technology, smartphones
     PEOPLE: Tim Cook, Elon Musk
     ORGANIZATIONS: Apple, Tesla
     LOCATIONS: California"

    OUTPUT (Python dict):
    ---------------------
    {
        "keywords": ["ai", "technology", "smartphones"],
        "people": ["Tim Cook", "Elon Musk"],
        "organizations": ["Apple", "Tesla"],
        "locations": ["California"]
    }

    WHY DO WE NEED THIS?
    --------------------
    Claude returns text, but we need structured data.
    This function bridges that gap by parsing the text.
    """

    result = {
        "keywords": [],
        "people": [],
        "organizations": [],
        "locations": []
    }

    # Split response into lines
    lines = response.strip().split("\n")

    for line in lines:
        line = line.strip()

        # Parse KEYWORDS line
        if line.upper().startswith("KEYWORDS:"):
            value = line.split(":", 1)[1].strip()
            if value.lower() != "none":
                # Split by comma, clean each keyword
                result["keywords"] = [
                    kw.strip().lower()
                    for kw in value.split(",")
                    if kw.strip()
                ]

        # Parse PEOPLE line
        elif line.upper().startswith("PEOPLE:"):
            value = line.split(":", 1)[1].strip()
            if value.lower() != "none":
                result["people"] = [
                    p.strip()
                    for p in value.split(",")
                    if p.strip()
                ]

        # Parse ORGANIZATIONS line
        elif line.upper().startswith("ORGANIZATIONS:"):
            value = line.split(":", 1)[1].strip()
            if value.lower() != "none":
                result["organizations"] = [
                    o.strip()
                    for o in value.split(",")
                    if o.strip()
                ]

        # Parse LOCATIONS line
        elif line.upper().startswith("LOCATIONS:"):
            value = line.split(":", 1)[1].strip()
            if value.lower() != "none":
                result["locations"] = [
                    loc.strip()
                    for loc in value.split(",")
                    if loc.strip()
                ]

    return result


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

    print(f"  Tagging: {title[:40]}...")

    response = chain.invoke({
        "title": title,
        "content": content,
    })

    tags = parse_tagging_response(response)

    article.keywords = tags["keywords"]
    article.people = tags["people"]
    article.organizations = tags["organizations"]
    article.locations = tags["locations"]

    if tags["keywords"]:
        print(f"    Keywords: {', '.join(tags['keywords'][:3])}...")
    if tags["people"]:
        print(f"    People: {', '.join(tags['people'])}")

    return article


def tag_articles(articles: list[Article]) -> list[Article]:
    """Apply tagging to every article, falling back to empty lists on errors."""

    print("\n" + "=" * 50)
    print("EXTRACTING KEYWORDS & ENTITIES")
    print("=" * 50)

    tagged: list[Article] = []
    total = len(articles)

    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{total}]", end="")

        try:
            tagged_article = tag_article(article)
            tagged.append(tagged_article)
        except Exception as e:
            print(f"  Error tagging: {e}")
            article.keywords = []
            article.people = []
            article.organizations = []
            article.locations = []
            tagged.append(article)

    print("\n" + "=" * 50)
    print("TAGGING COMPLETE")
    print("=" * 50)

    return tagged


def display_tags(article: Article) -> None:
    """Print an article's tags in a readable format."""
    print(f"\n📰 {(article.title or 'Untitled')[:50]}...")

    keywords = article.keywords
    people = article.people
    organizations = article.organizations
    locations = article.locations

    if keywords:
        print(f"   🏷️  Keywords: {', '.join(keywords)}")
    if people:
        print(f"   👤 People: {', '.join(people)}")
    if organizations:
        print(f"   🏢 Organizations: {', '.join(organizations)}")
    if locations:
        print(f"   📍 Locations: {', '.join(locations)}")

    if not any([keywords, people, organizations, locations]):
        print("   (No tags extracted)")


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
