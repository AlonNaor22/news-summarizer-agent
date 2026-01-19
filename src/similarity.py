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

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANTHROPIC_API_KEY, MODEL_NAME


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

def calculate_keyword_similarity(article_a: dict, article_b: dict) -> float:
    """
    Calculate similarity between two articles based on keyword overlap.

    PARAMETERS:
    -----------
    article_a : dict
        First article with 'keywords' list
    article_b : dict
        Second article with 'keywords' list

    RETURNS:
    --------
    float
        Similarity score from 0.0 (nothing in common) to 1.0 (identical)

    EXAMPLE:
    --------
    >>> a = {"keywords": ["ai", "tech", "apple"]}
    >>> b = {"keywords": ["ai", "tech", "google"]}
    >>> calculate_keyword_similarity(a, b)
    0.5  # 2 shared out of 4 unique

    THE MATH (Jaccard Similarity):
    ------------------------------
    Keywords A: {ai, tech, apple}
    Keywords B: {ai, tech, google}

    Intersection (A ∩ B): {ai, tech}        → size = 2
    Union (A ∪ B): {ai, tech, apple, google} → size = 4

    Jaccard = 2 / 4 = 0.5
    """

    # Get keywords as sets (for set operations)
    # Sets automatically handle duplicates
    keywords_a = set(kw.lower() for kw in article_a.get("keywords", []))
    keywords_b = set(kw.lower() for kw in article_b.get("keywords", []))

    # Handle empty keywords
    if not keywords_a or not keywords_b:
        return 0.0

    # Calculate Jaccard similarity
    # & is intersection (items in BOTH sets)
    # | is union (items in EITHER set)
    intersection = keywords_a & keywords_b
    union = keywords_a | keywords_b

    # Avoid division by zero
    if len(union) == 0:
        return 0.0

    similarity = len(intersection) / len(union)

    return round(similarity, 3)


def calculate_entity_similarity(article_a: dict, article_b: dict) -> float:
    """
    Calculate similarity based on shared entities (people, orgs, locations).

    This complements keyword similarity by looking at WHO and WHERE,
    not just WHAT the article is about.

    EXAMPLE:
    --------
    Article A: mentions Tim Cook, Apple, California
    Article B: mentions Tim Cook, Google, California
    Shared: Tim Cook, California → 2/4 = 0.5 similarity
    """

    # Combine all entities from each article
    entities_a = set()
    entities_b = set()

    # Add all entity types
    for entity_type in ["people", "organizations", "locations"]:
        entities_a.update(e.lower() for e in article_a.get(entity_type, []))
        entities_b.update(e.lower() for e in article_b.get(entity_type, []))

    # Handle empty entities
    if not entities_a or not entities_b:
        return 0.0

    # Jaccard similarity
    intersection = entities_a & entities_b
    union = entities_a | entities_b

    if len(union) == 0:
        return 0.0

    return round(len(intersection) / len(union), 3)


def calculate_combined_similarity(article_a: dict, article_b: dict) -> dict:
    """
    Calculate overall similarity using multiple factors.

    WEIGHTED COMBINATION:
    ---------------------
    We combine keyword and entity similarity with weights:
    - Keywords: 60% weight (topic is most important)
    - Entities: 30% weight (who/where matters)
    - Category: 10% weight (same category = small boost)

    RETURNS:
    --------
    dict with:
        - overall: Combined similarity score (0-1)
        - keyword_similarity: Keyword-based score
        - entity_similarity: Entity-based score
        - same_category: Whether categories match
        - shared_keywords: List of shared keywords
        - shared_entities: List of shared entities
    """

    # Calculate individual similarities
    keyword_sim = calculate_keyword_similarity(article_a, article_b)
    entity_sim = calculate_entity_similarity(article_a, article_b)

    # Check if same category
    cat_a = article_a.get("category", "").lower()
    cat_b = article_b.get("category", "").lower()
    same_category = cat_a == cat_b and cat_a != ""

    # Weighted combination
    # Keywords matter most (60%), entities second (30%), category bonus (10%)
    category_bonus = 0.1 if same_category else 0.0
    overall = (keyword_sim * 0.6) + (entity_sim * 0.3) + category_bonus

    # Cap at 1.0
    overall = min(overall, 1.0)

    # Find shared items for display
    keywords_a = set(kw.lower() for kw in article_a.get("keywords", []))
    keywords_b = set(kw.lower() for kw in article_b.get("keywords", []))
    shared_keywords = list(keywords_a & keywords_b)

    entities_a = set()
    entities_b = set()
    for entity_type in ["people", "organizations", "locations"]:
        entities_a.update(article_a.get(entity_type, []))
        entities_b.update(article_b.get(entity_type, []))
    shared_entities = list(entities_a & entities_b)

    return {
        "overall": round(overall, 3),
        "keyword_similarity": keyword_sim,
        "entity_similarity": entity_sim,
        "same_category": same_category,
        "shared_keywords": shared_keywords,
        "shared_entities": shared_entities
    }


# =====================================================
# FINDING SIMILAR ARTICLES (Statistical)
# =====================================================

def find_similar_articles(
    target_article: dict,
    all_articles: list[dict],
    threshold: float = 0.2,
    max_results: int = 5
) -> list[dict]:
    """
    Find articles similar to a target article.

    PARAMETERS:
    -----------
    target_article : dict
        The article to find similar ones for
    all_articles : list[dict]
        All available articles to search through
    threshold : float
        Minimum similarity score (0-1) to be considered "similar"
        Default 0.2 = at least 20% similar
    max_results : int
        Maximum number of similar articles to return

    RETURNS:
    --------
    list[dict]
        Similar articles, each with added 'similarity' field

    EXAMPLE:
    --------
    >>> target = articles[0]  # Article about Apple AI
    >>> similar = find_similar_articles(target, articles)
    >>> print(similar[0]["title"])
    "Google's AI Chatbot..."  # Related AI article
    >>> print(similar[0]["similarity"]["overall"])
    0.65  # 65% similar
    """

    results = []

    for article in all_articles:
        # Skip comparing article to itself
        if article.get("title") == target_article.get("title"):
            continue

        # Calculate similarity
        similarity = calculate_combined_similarity(target_article, article)

        # Only include if above threshold
        if similarity["overall"] >= threshold:
            # Create a copy with similarity data
            article_with_sim = article.copy()
            article_with_sim["similarity"] = similarity
            results.append(article_with_sim)

    # Sort by similarity (highest first)
    results.sort(key=lambda x: x["similarity"]["overall"], reverse=True)

    # Return top N results
    return results[:max_results]


def find_all_related_pairs(
    articles: list[dict],
    threshold: float = 0.3
) -> list[dict]:
    """
    Find ALL pairs of related articles.

    This compares every article against every other article
    and returns pairs that exceed the similarity threshold.

    PARAMETERS:
    -----------
    articles : list[dict]
        All articles to compare
    threshold : float
        Minimum similarity to be considered related

    RETURNS:
    --------
    list[dict]
        List of related pairs, each with:
        - article_a: First article (title)
        - article_b: Second article (title)
        - similarity: Similarity details

    NOTE ON COMPLEXITY:
    -------------------
    This is O(n²) - for n articles, we make n*(n-1)/2 comparisons.
    - 10 articles = 45 comparisons
    - 50 articles = 1,225 comparisons
    - 100 articles = 4,950 comparisons

    For large datasets, consider using embeddings instead!
    """

    pairs = []
    n = len(articles)

    # Compare each pair (avoid duplicates by only comparing i < j)
    for i in range(n):
        for j in range(i + 1, n):
            similarity = calculate_combined_similarity(articles[i], articles[j])

            if similarity["overall"] >= threshold:
                pairs.append({
                    "article_a_index": i,
                    "article_a_title": articles[i].get("title", "Untitled"),
                    "article_b_index": j,
                    "article_b_title": articles[j].get("title", "Untitled"),
                    "similarity": similarity
                })

    # Sort by similarity
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
1. Cover the same event from different angles
2. Discuss the same topic or theme
3. Mention the same people, companies, or places
4. Are part of the same ongoing story
5. Have cause-and-effect relationship

You MUST respond in this EXACT format for each related pair:

PAIR: <article_number_1> - <article_number_2>
RELATIONSHIP: <type: same_event | same_topic | same_entities | ongoing_story | cause_effect>
STRENGTH: <high | medium | low>
EXPLANATION: <one sentence explaining the connection>

If articles are NOT related, don't include them in any pair.

Example response:
PAIR: 1 - 3
RELATIONSHIP: same_topic
STRENGTH: high
EXPLANATION: Both articles discuss artificial intelligence developments in tech industry.

PAIR: 2 - 4
RELATIONSHIP: cause_effect
STRENGTH: medium
EXPLANATION: Article 2's policy announcement led to the market reaction in Article 4."""),

    ("human", """Analyze the relationships between these {article_count} articles:

{articles_text}

Find all related pairs:""")
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

    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=0.2,
        max_tokens=1500,  # May need more for many pairs
        api_key=ANTHROPIC_API_KEY
    )


def create_similarity_chain():
    """Create the similarity analysis chain."""
    llm = create_similarity_llm()
    parser = StrOutputParser()
    return SIMILARITY_PROMPT | llm | parser


def format_articles_for_similarity(articles: list[dict]) -> str:
    """
    Format articles for similarity analysis.

    We include enough context for Claude to find connections.
    """
    formatted = []

    for i, article in enumerate(articles, 1):
        text = f"""ARTICLE {i}:
Title: {article.get('title', 'Untitled')}
Category: {article.get('category', 'Unknown')}
Summary: {article.get('summary', article.get('description', 'No summary'))}
Keywords: {', '.join(article.get('keywords', [])) or 'None'}
People: {', '.join(article.get('people', [])) or 'None'}
Organizations: {', '.join(article.get('organizations', [])) or 'None'}
"""
        formatted.append(text)

    return "\n---\n".join(formatted)


def parse_similarity_response(response: str, articles: list[dict]) -> list[dict]:
    """
    Parse Claude's similarity analysis into structured data.

    INPUT (from Claude):
    --------------------
    "PAIR: 1 - 3
     RELATIONSHIP: same_topic
     STRENGTH: high
     EXPLANATION: Both discuss AI..."

    OUTPUT (Python list):
    ---------------------
    [
        {
            "article_a_index": 0,
            "article_a_title": "...",
            "article_b_index": 2,
            "article_b_title": "...",
            "relationship": "same_topic",
            "strength": "high",
            "explanation": "Both discuss AI..."
        }
    ]
    """

    pairs = []
    current_pair = None

    lines = response.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # New pair starts
        if line.upper().startswith("PAIR:"):
            # Save previous pair
            if current_pair:
                pairs.append(current_pair)

            # Parse "PAIR: 1 - 3" format
            try:
                pair_str = line.split(":", 1)[1].strip()
                # Handle various formats: "1 - 3", "1-3", "1 and 3"
                pair_str = pair_str.replace(" and ", "-").replace(" ", "")
                parts = pair_str.split("-")

                if len(parts) >= 2:
                    idx_a = int(parts[0]) - 1  # Convert to 0-indexed
                    idx_b = int(parts[1]) - 1

                    current_pair = {
                        "article_a_index": idx_a,
                        "article_a_title": articles[idx_a].get("title", "Unknown") if idx_a < len(articles) else "Unknown",
                        "article_b_index": idx_b,
                        "article_b_title": articles[idx_b].get("title", "Unknown") if idx_b < len(articles) else "Unknown",
                        "relationship": "related",
                        "strength": "medium",
                        "explanation": ""
                    }
            except (ValueError, IndexError):
                current_pair = None

        # Parse pair properties
        elif current_pair:
            if line.upper().startswith("RELATIONSHIP:"):
                current_pair["relationship"] = line.split(":", 1)[1].strip().lower()

            elif line.upper().startswith("STRENGTH:"):
                strength = line.split(":", 1)[1].strip().lower()
                if strength in ["high", "medium", "low"]:
                    current_pair["strength"] = strength

            elif line.upper().startswith("EXPLANATION:"):
                current_pair["explanation"] = line.split(":", 1)[1].strip()

    # Don't forget last pair
    if current_pair:
        pairs.append(current_pair)

    return pairs


def find_related_articles_llm(articles: list[dict]) -> list[dict]:
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

    # Call Claude
    response = chain.invoke({
        "article_count": len(articles),
        "articles_text": articles_text
    })

    # Parse response
    pairs = parse_similarity_response(response, articles)

    print(f"   Found {len(pairs)} related pairs")

    return pairs


# =====================================================
# COMBINED SIMILARITY ANALYSIS
# =====================================================

def analyze_article_relationships(
    articles: list[dict],
    use_llm: bool = True
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
    result["statistical_pairs"] = find_all_related_pairs(articles, threshold=0.2)
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
        title = article.get("title", f"Article {i+1}")
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

def display_similar_articles(target: dict, similar: list[dict]) -> None:
    """Display articles similar to a target article."""

    print("\n" + "=" * 60)
    print(f"📰 ARTICLES SIMILAR TO:")
    print(f"   \"{target.get('title', 'Unknown')[:50]}...\"")
    print("=" * 60)

    if not similar:
        print("\n   No similar articles found.")
        return

    for i, article in enumerate(similar, 1):
        sim = article.get("similarity", {})
        score = sim.get("overall", 0)
        score_bar = "█" * int(score * 10)

        print(f"\n  {i}. {article.get('title', 'Untitled')[:50]}...")
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

    # Test articles with some overlap
    test_articles = [
        {
            "title": "Apple Unveils New AI-Powered iPhone Features",
            "summary": "Apple announced revolutionary AI capabilities including smart assistants and photo editing.",
            "category": "Technology",
            "keywords": ["artificial intelligence", "smartphones", "apple", "technology"],
            "people": ["Tim Cook"],
            "organizations": ["Apple"],
            "locations": ["California"]
        },
        {
            "title": "Google Responds with AI Chatbot Update",
            "summary": "Google upgraded its AI assistant to compete with Apple's new features.",
            "category": "Technology",
            "keywords": ["artificial intelligence", "chatbot", "google", "technology"],
            "people": ["Sundar Pichai"],
            "organizations": ["Google"],
            "locations": ["Mountain View"]
        },
        {
            "title": "Tech Stocks Surge on AI Announcements",
            "summary": "Technology stocks rallied as investors bet on AI growth from major companies.",
            "category": "Business",
            "keywords": ["stocks", "investment", "technology", "artificial intelligence"],
            "people": [],
            "organizations": ["Apple", "Google", "NVIDIA"],
            "locations": ["Wall Street"]
        },
        {
            "title": "Climate Summit Reaches Historic Agreement",
            "summary": "World leaders agreed to ambitious emission targets at the Paris summit.",
            "category": "World News",
            "keywords": ["climate change", "environment", "policy", "international"],
            "people": ["Emmanuel Macron"],
            "organizations": ["United Nations"],
            "locations": ["Paris"]
        },
        {
            "title": "Renewable Energy Investment Breaks Records",
            "summary": "Global investment in clean energy reached $500 billion this year.",
            "category": "Business",
            "keywords": ["climate change", "renewable energy", "investment", "environment"],
            "people": [],
            "organizations": [],
            "locations": []
        },
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
