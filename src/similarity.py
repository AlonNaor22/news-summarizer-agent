# =====================================================
# ARTICLE SIMILARITY MODULE
# =====================================================
#
# This module finds related/similar articles.
#
# WHY LINK SIMILAR ARTICLES?
# --------------------------
# 1. Help users discover related stories
# 2. Group articles about the same event
# 3. Show different perspectives on the same topic
# 4. Build a "recommended articles" feature
#
# UNDERSTANDING SIMILARITY:
# -------------------------
# Two articles are "similar" if they:
# - Cover the same topic (AI, climate, sports)
# - Mention the same people/organizations
# - Describe the same event from different angles
# - Share common keywords or themes
#
# THREE APPROACHES TO SIMILARITY:
# -------------------------------
#
# 1. KEYWORD OVERLAP (Simple)
#    - Count how many keywords two articles share
#    - Fast and free, but shallow understanding
#    - "AI" and "artificial intelligence" seen as different
#
# 2. EMBEDDINGS (Advanced - explained but not implemented)
#    - Convert text to numerical vectors
#    - Similar texts have similar vectors
#    - Requires embedding model (OpenAI, Cohere, etc.)
#
# 3. LLM-BASED (Smart)
#    - Ask Claude to identify relationships
#    - Best understanding, but costs API calls
#    - Can explain WHY articles are related
#
# We implement approaches 1 and 3 in this module.
#
# LANGCHAIN CONCEPTS IN THIS MODULE:
# ----------------------------------
# 1. Pairwise Comparison - Comparing items against each other
# 2. Structured Output - Getting relationship data from LLM
# 3. Embeddings Concept - Understanding vector similarity
#
# =====================================================

from typing import Any, Literal, Union

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS, SIMILARITY_THRESHOLDS
from src.models import Article


class RelatedPair(BaseModel):
    """A single pair of related articles identified by the LLM."""

    article_a: int = Field(
        description="1-based index of the first article in the pair",
        ge=1,
    )
    article_b: int = Field(
        description="1-based index of the second article in the pair",
        ge=1,
    )
    relationship: Literal[
        "same_event",
        "same_topic",
        "same_entities",
        "ongoing_story",
        "cause_effect",
    ] = Field(description="Type of relationship between the two articles")
    strength: Literal["high", "medium", "low"] = Field(
        description="How strong the relationship is",
    )
    explanation: str = Field(
        description="One-sentence explanation of why the two articles are related",
    )


class RelatedPairList(BaseModel):
    """Wrapper for a list of related-article pairs."""

    pairs: list[RelatedPair] = Field(
        default_factory=list,
        description="All related-article pairs found in the input",
    )


# Helpers so similarity functions can accept either Article instances or
# the older raw-dict shape (the test suite calls these directly with dicts).
ArticleLike = Union[Article, dict]


def _get_field(article: ArticleLike, name: str, default: Any) -> Any:
    if isinstance(article, dict):
        return article.get(name, default)
    return getattr(article, name, default)


# =====================================================
# APPROACH 1: KEYWORD-BASED SIMILARITY
# =====================================================
#
# This is the simplest approach: count shared keywords.
#
# HOW IT WORKS:
# -------------
# Article A keywords: ["ai", "technology", "apple"]
# Article B keywords: ["ai", "google", "technology"]
# Shared keywords: ["ai", "technology"] = 2 shared
#
# Similarity score = shared / total unique keywords
#                  = 2 / 4 = 0.5 (50% similar)
#
# This is called JACCARD SIMILARITY:
#   J(A,B) = |A ∩ B| / |A ∪ B|
#   (intersection size / union size)
#
# =====================================================

def calculate_keyword_similarity(article_a: ArticleLike, article_b: ArticleLike) -> float:
    """Return the Jaccard keyword similarity between two articles (0-1)."""

    keywords_a = set(kw.lower() for kw in _get_field(article_a, "keywords", []))
    keywords_b = set(kw.lower() for kw in _get_field(article_b, "keywords", []))

    if not keywords_a or not keywords_b:
        return 0.0

    intersection = keywords_a & keywords_b
    union = keywords_a | keywords_b

    if len(union) == 0:
        return 0.0

    similarity = len(intersection) / len(union)

    return round(similarity, 3)


def calculate_entity_similarity(article_a: ArticleLike, article_b: ArticleLike) -> float:
    """Return the Jaccard similarity of (people | orgs | locations) between articles."""

    entities_a: set[str] = set()
    entities_b: set[str] = set()

    for entity_type in ["people", "organizations", "locations"]:
        entities_a.update(e.lower() for e in _get_field(article_a, entity_type, []))
        entities_b.update(e.lower() for e in _get_field(article_b, entity_type, []))

    if not entities_a or not entities_b:
        return 0.0

    intersection = entities_a & entities_b
    union = entities_a | entities_b

    if len(union) == 0:
        return 0.0

    return round(len(intersection) / len(union), 3)


def calculate_combined_similarity(article_a: ArticleLike, article_b: ArticleLike) -> dict:
    """Return a weighted combined-similarity dict mixing keywords, entities, and category."""

    keyword_sim = calculate_keyword_similarity(article_a, article_b)
    entity_sim = calculate_entity_similarity(article_a, article_b)

    cat_a = (_get_field(article_a, "category", "") or "").lower()
    cat_b = (_get_field(article_b, "category", "") or "").lower()
    same_category = cat_a == cat_b and cat_a != ""

    category_bonus = 0.1 if same_category else 0.0
    overall = (keyword_sim * 0.6) + (entity_sim * 0.3) + category_bonus

    overall = min(overall, 1.0)

    keywords_a = set(kw.lower() for kw in _get_field(article_a, "keywords", []))
    keywords_b = set(kw.lower() for kw in _get_field(article_b, "keywords", []))
    shared_keywords = list(keywords_a & keywords_b)

    entities_a: set[str] = set()
    entities_b: set[str] = set()
    for entity_type in ["people", "organizations", "locations"]:
        entities_a.update(_get_field(article_a, entity_type, []))
        entities_b.update(_get_field(article_b, entity_type, []))
    shared_entities = list(entities_a & entities_b)

    return {
        "overall": round(overall, 3),
        "keyword_similarity": keyword_sim,
        "entity_similarity": entity_sim,
        "same_category": same_category,
        "shared_keywords": shared_keywords,
        "shared_entities": shared_entities,
    }


# =====================================================
# FINDING SIMILAR ARTICLES (Statistical)
# =====================================================

def find_similar_articles(
    target_article: Article,
    all_articles: list[Article],
    threshold: float = SIMILARITY_THRESHOLDS["find_similar"],
    max_results: int = 5,
) -> list[Article]:
    """Return up to ``max_results`` articles that exceed ``threshold`` similarity to ``target_article``.

    The returned articles are clones of the originals with the ``similarity``
    field populated.
    """

    results: list[Article] = []

    for article in all_articles:
        if article.title == target_article.title:
            continue

        similarity = calculate_combined_similarity(target_article, article)

        if similarity["overall"] >= threshold:
            article_with_sim = article.model_copy()
            article_with_sim.similarity = similarity
            results.append(article_with_sim)

    results.sort(key=lambda x: (x.similarity or {}).get("overall", 0), reverse=True)

    return results[:max_results]


def find_all_related_pairs(
    articles: list[Article],
    threshold: float = SIMILARITY_THRESHOLDS["related_pairs"],
) -> list[dict]:
    """Return every (i,j) pair of articles whose combined similarity is ≥ ``threshold``."""

    pairs: list[dict] = []
    n = len(articles)

    for i in range(n):
        for j in range(i + 1, n):
            similarity = calculate_combined_similarity(articles[i], articles[j])

            if similarity["overall"] >= threshold:
                pairs.append({
                    "article_a_index": i,
                    "article_a_title": articles[i].title or "Untitled",
                    "article_b_index": j,
                    "article_b_title": articles[j].title or "Untitled",
                    "similarity": similarity,
                })

    pairs.sort(key=lambda x: x["similarity"]["overall"], reverse=True)

    return pairs


# =====================================================
# ABOUT EMBEDDINGS (Educational Explanation)
# =====================================================
#
# WHAT ARE EMBEDDINGS?
# --------------------
# Embeddings convert text into numerical vectors (lists of numbers).
#
# Example:
#   "Apple releases new iPhone" → [0.12, -0.45, 0.78, ..., 0.33]
#   "Google launches smartphone" → [0.15, -0.42, 0.81, ..., 0.29]
#
# Similar texts have similar vectors!
#
# WHY VECTORS?
# ------------
# Computers can easily compare numbers:
# - Calculate distance between vectors
# - Closer vectors = more similar texts
#
# COSINE SIMILARITY:
# ------------------
# The most common way to compare embeddings.
# Measures the angle between two vectors.
#
#   similarity = cos(θ) = (A · B) / (||A|| × ||B||)
#
# Result ranges from -1 to 1:
#   1.0  = identical direction (very similar)
#   0.0  = perpendicular (unrelated)
#   -1.0 = opposite direction (opposite meaning)
#
# LANGCHAIN EMBEDDINGS:
# ---------------------
# LangChain supports many embedding models:
#
#   from langchain_openai import OpenAIEmbeddings
#   embeddings = OpenAIEmbeddings()
#   vector = embeddings.embed_query("Hello world")
#
# We DON'T implement embeddings here because:
# 1. Requires additional API key (OpenAI, Cohere, etc.)
# 2. Adds complexity
# 3. Our keyword approach works well for this project
#
# But for production systems with many articles,
# embeddings are the preferred approach!
#
# =====================================================


# =====================================================
# APPROACH 2: LLM-BASED SIMILARITY
# =====================================================
#
# Ask Claude to analyze relationships between articles.
# This is smarter than keyword matching because Claude
# understands MEANING, not just word overlap.
#
# Example where LLM beats keywords:
# - Article A: "Electric vehicle sales surge"
# - Article B: "Tesla stock reaches new high"
#
# Keyword overlap: 0 (no shared keywords!)
# LLM understanding: "Both about EV industry success"
#
# =====================================================

SIMILARITY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert at analyzing relationships between news articles.

Your job is to identify which articles are related and explain WHY.

Two articles are RELATED if they:
1. Cover the same event from different angles -> same_event
2. Discuss the same topic or theme -> same_topic
3. Mention the same people, companies, or places -> same_entities
4. Are part of the same ongoing story -> ongoing_story
5. Have cause-and-effect relationship -> cause_effect

Use the 1-based article numbers shown in the input. If articles are NOT related,
don't include them in any pair. Provide one short sentence explaining each connection."""),

    ("human", """Analyze the relationships between these {article_count} articles:

{articles_text}""")
])


def create_similarity_llm():
    """
    Create Claude LLM for similarity analysis.

    WHY TEMPERATURE = 0.2?
    ----------------------
    We want Claude to find relationships, but not invent
    connections that don't exist. Low temperature keeps
    it grounded in what's actually in the articles.
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not found!")

    settings = LLM_SETTINGS["similarity"]
    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=settings["temperature"],
        max_tokens=settings["max_tokens"],
        api_key=ANTHROPIC_API_KEY,
    )


_chain = None


def create_similarity_chain():
    """Return the (lazily-built) similarity-analysis chain.

    Uses LangChain's structured-output binding so Claude returns a validated
    :class:`RelatedPairList` instead of free-form text.
    """
    global _chain
    if _chain is None:
        llm = create_similarity_llm().with_structured_output(RelatedPairList)
        _chain = SIMILARITY_PROMPT | llm
    return _chain


def format_articles_for_similarity(articles: list[Article]) -> str:
    """Render every article into the text block used as the LLM's prompt input."""
    formatted = []

    for i, article in enumerate(articles, 1):
        text = f"""ARTICLE {i}:
Title: {article.title or 'Untitled'}
Category: {article.category or 'Unknown'}
Summary: {article.summary or article.description or 'No summary'}
Keywords: {', '.join(article.keywords) or 'None'}
People: {', '.join(article.people) or 'None'}
Organizations: {', '.join(article.organizations) or 'None'}
"""
        formatted.append(text)

    return "\n---\n".join(formatted)


def _pair_list_to_dicts(pair_list: RelatedPairList, articles: list[Article]) -> list[dict]:
    """Convert a :class:`RelatedPairList` to the legacy dict shape callers expect.

    The LLM produces 1-based article indices; we translate to 0-based and
    drop any pair whose indices fall outside the input list.
    """
    out: list[dict] = []
    n = len(articles)

    for pair in pair_list.pairs:
        idx_a = pair.article_a - 1
        idx_b = pair.article_b - 1
        if not (0 <= idx_a < n and 0 <= idx_b < n):
            continue

        out.append({
            "article_a_index": idx_a,
            "article_a_title": articles[idx_a].title or "Unknown",
            "article_b_index": idx_b,
            "article_b_title": articles[idx_b].title or "Unknown",
            "relationship": pair.relationship,
            "strength": pair.strength,
            "explanation": pair.explanation,
        })

    return out


def find_related_articles_llm(articles: list[Article]) -> list[dict]:
    """
    Use Claude to find related articles.

    This is the SMART approach - Claude understands meaning,
    not just keyword overlap.

    PARAMETERS:
    -----------
    articles : list[dict]
        All articles to analyze

    RETURNS:
    --------
    list[dict]
        List of related pairs with explanations

    EXAMPLE:
    --------
    >>> pairs = find_related_articles_llm(articles)
    >>> print(pairs[0])
    {
        "article_a_title": "Apple AI Launch",
        "article_b_title": "Google AI Response",
        "relationship": "same_topic",
        "strength": "high",
        "explanation": "Both cover AI assistants in tech industry"
    }
    """

    if len(articles) < 2:
        return []

    print("\n🤖 Asking Claude to find article relationships...")

    chain = create_similarity_chain()

    # Format articles
    articles_text = format_articles_for_similarity(articles)

    # Call Claude — returns a validated RelatedPairList
    pair_list: RelatedPairList = chain.invoke({
        "article_count": len(articles),
        "articles_text": articles_text
    })

    pairs = _pair_list_to_dicts(pair_list, articles)

    print(f"   Found {len(pairs)} related pairs")

    return pairs


# =====================================================
# COMBINED SIMILARITY ANALYSIS
# =====================================================

def analyze_article_relationships(
    articles: list[Article],
    use_llm: bool = True,
) -> dict:
    """
    Comprehensive relationship analysis using both approaches.

    PARAMETERS:
    -----------
    articles : list[dict]
        All articles to analyze
    use_llm : bool
        Whether to use Claude for smart analysis

    RETURNS:
    --------
    dict with:
        - statistical_pairs: Pairs found by keyword overlap
        - llm_pairs: Pairs found by Claude (if use_llm=True)
        - article_connections: For each article, its related articles
    """

    print("\n" + "=" * 50)
    print("ANALYZING ARTICLE RELATIONSHIPS")
    print("=" * 50)

    result = {
        "statistical_pairs": [],
        "llm_pairs": [],
        "article_connections": {}
    }

    # -------------------------------------------------
    # Statistical Analysis (Fast, Free)
    # -------------------------------------------------
    print("\n📊 Finding relationships by keyword overlap...")
    result["statistical_pairs"] = find_all_related_pairs(
        articles, threshold=SIMILARITY_THRESHOLDS["find_similar"]
    )
    print(f"   Found {len(result['statistical_pairs'])} related pairs")

    # -------------------------------------------------
    # LLM Analysis (Smart)
    # -------------------------------------------------
    if use_llm and len(articles) >= 2:
        result["llm_pairs"] = find_related_articles_llm(articles)

    # -------------------------------------------------
    # Build connections map
    # -------------------------------------------------
    # For each article, list its related articles
    for i, article in enumerate(articles):
        title = article.title or f"Article {i + 1}"
        connections = []

        # From statistical analysis
        for pair in result["statistical_pairs"]:
            if pair["article_a_index"] == i:
                connections.append({
                    "title": pair["article_b_title"],
                    "method": "keywords",
                    "score": pair["similarity"]["overall"]
                })
            elif pair["article_b_index"] == i:
                connections.append({
                    "title": pair["article_a_title"],
                    "method": "keywords",
                    "score": pair["similarity"]["overall"]
                })

        # From LLM analysis
        for pair in result["llm_pairs"]:
            if pair["article_a_index"] == i:
                connections.append({
                    "title": pair["article_b_title"],
                    "method": "llm",
                    "relationship": pair["relationship"],
                    "explanation": pair["explanation"]
                })
            elif pair["article_b_index"] == i:
                connections.append({
                    "title": pair["article_a_title"],
                    "method": "llm",
                    "relationship": pair["relationship"],
                    "explanation": pair["explanation"]
                })

        result["article_connections"][title] = connections

    print("\n" + "=" * 50)
    print("RELATIONSHIP ANALYSIS COMPLETE")
    print("=" * 50)

    return result


# =====================================================
# DISPLAY FUNCTIONS
# =====================================================

def display_similar_articles(target: Article, similar: list[Article]) -> None:
    """Print articles similar to ``target`` along with their similarity stats."""

    print("\n" + "=" * 60)
    print(f"📰 ARTICLES SIMILAR TO:")
    print(f"   \"{(target.title or 'Unknown')[:50]}...\"")
    print("=" * 60)

    if not similar:
        print("\n   No similar articles found.")
        return

    for i, article in enumerate(similar, 1):
        sim = article.similarity or {}
        score = sim.get("overall", 0)
        score_bar = "█" * int(score * 10)

        print(f"\n  {i}. {(article.title or 'Untitled')[:50]}...")
        print(f"     Similarity: {score_bar} {score:.0%}")

        if sim.get("shared_keywords"):
            print(f"     Shared keywords: {', '.join(sim['shared_keywords'])}")

        if sim.get("shared_entities"):
            print(f"     Shared entities: {', '.join(sim['shared_entities'])}")


def display_all_relationships(analysis: dict) -> None:
    """Display all article relationships."""

    print("\n" + "=" * 60)
    print("🔗 ARTICLE RELATIONSHIPS")
    print("=" * 60)

    # Display LLM-found relationships (most insightful)
    if analysis.get("llm_pairs"):
        print("\n🤖 AI-DETECTED RELATIONSHIPS")
        print("-" * 40)

        for pair in analysis["llm_pairs"]:
            strength_emoji = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(pair["strength"], "⚪")

            print(f"\n  {strength_emoji} {pair['relationship'].upper()}")
            print(f"     📰 \"{pair['article_a_title'][:40]}...\"")
            print(f"     📰 \"{pair['article_b_title'][:40]}...\"")
            print(f"     💡 {pair['explanation']}")

    # Display statistical relationships
    if analysis.get("statistical_pairs"):
        print("\n\n📊 KEYWORD-BASED RELATIONSHIPS")
        print("-" * 40)

        for pair in analysis["statistical_pairs"][:5]:  # Top 5
            score = pair["similarity"]["overall"]
            shared = pair["similarity"].get("shared_keywords", [])

            print(f"\n  Score: {score:.0%}")
            print(f"     📰 \"{pair['article_a_title'][:40]}...\"")
            print(f"     📰 \"{pair['article_b_title'][:40]}...\"")
            if shared:
                print(f"     🏷️  Shared: {', '.join(shared)}")

    print("\n" + "=" * 60)


# =====================================================
# TEST CODE
# =====================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING ARTICLE SIMILARITY")
    print("=" * 60)

    test_articles = [
        Article(
            title="Apple Unveils New AI-Powered iPhone Features",
            summary="Apple announced revolutionary AI capabilities including smart assistants and photo editing.",
            category="Technology",
            keywords=["artificial intelligence", "smartphones", "apple", "technology"],
            people=["Tim Cook"],
            organizations=["Apple"],
            locations=["California"],
            source="Test",
            url="",
        ),
        Article(
            title="Google Responds with AI Chatbot Update",
            summary="Google upgraded its AI assistant to compete with Apple's new features.",
            category="Technology",
            keywords=["artificial intelligence", "chatbot", "google", "technology"],
            people=["Sundar Pichai"],
            organizations=["Google"],
            locations=["Mountain View"],
            source="Test",
            url="",
        ),
        Article(
            title="Tech Stocks Surge on AI Announcements",
            summary="Technology stocks rallied as investors bet on AI growth from major companies.",
            category="Business",
            keywords=["stocks", "investment", "technology", "artificial intelligence"],
            organizations=["Apple", "Google", "NVIDIA"],
            locations=["Wall Street"],
            source="Test",
            url="",
        ),
        Article(
            title="Climate Summit Reaches Historic Agreement",
            summary="World leaders agreed to ambitious emission targets at the Paris summit.",
            category="World News",
            keywords=["climate change", "environment", "policy", "international"],
            people=["Emmanuel Macron"],
            organizations=["United Nations"],
            locations=["Paris"],
            source="Test",
            url="",
        ),
        Article(
            title="Renewable Energy Investment Breaks Records",
            summary="Global investment in clean energy reached $500 billion this year.",
            category="Business",
            keywords=["climate change", "renewable energy", "investment", "environment"],
            source="Test",
            url="",
        ),
    ]

    # -------------------------------------------------
    # Test 1: Find similar articles to first one
    # -------------------------------------------------
    print("\n--- Test 1: Find Similar Articles ---")
    target = test_articles[0]
    similar = find_similar_articles(target, test_articles)
    display_similar_articles(target, similar)

    # -------------------------------------------------
    # Test 2: Find all relationships
    # -------------------------------------------------
    print("\n\n--- Test 2: All Relationships ---")
    analysis = analyze_article_relationships(test_articles, use_llm=True)
    display_all_relationships(analysis)

    # -------------------------------------------------
    # Test 3: Show connections for each article
    # -------------------------------------------------
    print("\n\n--- Test 3: Article Connection Map ---")
    for title, connections in analysis["article_connections"].items():
        if connections:
            print(f"\n📰 \"{title[:40]}...\"")
            print(f"   Connected to {len(connections)} article(s)")
