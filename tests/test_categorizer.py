from unittest.mock import MagicMock, patch

from src.categorizer import (
    MultiCategoryResult,
    categorize_article,
    categorize_article_multi,
    categorize_articles,
    clean_category,
    group_by_category,
)
from src.models import Article


def _make_article(**kwargs) -> Article:
    """Build an Article with the test-required fields and defaults for the rest."""
    kwargs.setdefault("source", "Test")
    kwargs.setdefault("url", "")
    return Article(**kwargs)


class TestCleanCategory:
    def test_politics_exact_match(self):
        # Simulates Claude returning "Politics" for election/government/president articles
        assert clean_category("Politics") == "Politics"

    def test_technology_exact_match(self):
        # Simulates Claude returning "Technology" for iPhone/AI/software articles
        assert clean_category("Technology") == "Technology"

    def test_business_exact_match(self):
        # Simulates Claude returning "Business" for stock/earnings/GDP articles
        assert clean_category("Business") == "Business"

    def test_case_insensitive_match(self):
        assert clean_category("politics") == "Politics"

    def test_strips_trailing_punctuation(self):
        assert clean_category("Technology.") == "Technology"

    def test_category_name_embedded_in_political_text(self):
        # clean_category finds "Politics" inside a longer string —
        # this mirrors how Claude might wrap its answer in a sentence
        result = clean_category("election government president Politics oversight")
        assert result == "Politics"

    def test_category_name_embedded_in_tech_text(self):
        result = clean_category("iPhone AI software Technology release")
        assert result == "Technology"

    def test_empty_string_returns_other(self):
        assert clean_category("") == "Other"

    def test_unknown_topic_returns_fallback_other(self):
        assert clean_category("xyzzy quux frobnicate random words") == "Other"


class TestMultiCategoryResultModel:
    def test_validator_canonicalizes_primary(self):
        # Pydantic validator runs clean_category, so lowercase input is normalized.
        result = MultiCategoryResult(primary="technology", secondary=["business"])
        assert result.primary == "Technology"
        assert result.secondary == ["Business"]

    def test_unknown_categories_dropped_from_secondary(self):
        # "Quux" isn't a known category -> would map to "Other" -> excluded from secondary.
        result = MultiCategoryResult(primary="Health", secondary=["Science", "Quux"])
        assert result.primary == "Health"
        assert result.secondary == ["Science"]


class TestCategorizeArticleMultiStructuredOutput:
    def test_writes_primary_and_secondary_back_to_article(self):
        article = _make_article(title="Apple AI launch", summary="Apple launched a new AI iPhone." )

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = MultiCategoryResult(
            primary="Technology",
            secondary=["Business"],
        )

        with patch("src.categorizer.create_multi_categorize_chain", return_value=mock_chain):
            result = categorize_article_multi(article)

        assert result.category == "Technology"
        assert result.secondary_categories == ["Business"]


class TestGroupByCategory:
    def test_empty_list_returns_empty_dict(self):
        assert group_by_category([]) == {}

    def test_groups_articles_by_category_correctly(self):
        articles = [
            _make_article(title="A1", category="Technology"),
            _make_article(title="A2", category="Business"),
            _make_article(title="A3", category="Technology"),
        ]
        grouped = group_by_category(articles)
        assert len(grouped["Technology"]) == 2
        assert len(grouped["Business"]) == 1

    def test_missing_category_falls_back_to_other(self):
        articles = [_make_article(title="No category article")]
        grouped = group_by_category(articles)
        assert "Other" in grouped


class TestCategorizeArticle:
    def test_sets_category_from_llm_response(self):
        article = _make_article(title="Apple AI chip", summary="Apple released a new AI chip.")

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Technology"

        with patch("src.categorizer.create_categorize_chain", return_value=mock_chain):
            result = categorize_article(article)

        assert result.category == "Technology"
        mock_chain.invoke.assert_called_once()

    def test_missing_summary_returns_other_without_llm_call(self):
        # No summary and no description → short-circuit, no LLM call
        article = _make_article(title="No content article")
        mock_chain = MagicMock()

        with patch("src.categorizer.create_categorize_chain", return_value=mock_chain):
            result = categorize_article(article)

        assert result.category == "Other"
        mock_chain.invoke.assert_not_called()


class TestCategorizeArticles:
    def test_batch_sets_all_categories(self):
        articles = [
            _make_article(title="Tech news", summary="Apple released a new AI chip."),
            _make_article(title="Election results", summary="Congress passed a new bill."),
        ]

        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = ["Technology", "Politics"]

        with patch("src.categorizer.create_categorize_chain", return_value=mock_chain):
            result = categorize_articles(articles)

        assert result[0].category == "Technology"
        assert result[1].category == "Politics"

    def test_per_item_error_falls_back_to_other(self):
        articles = [
            _make_article(title="A1", summary="Tech news about AI."),
            _make_article(title="A2", summary="Economic data released."),
        ]

        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = [RuntimeError("LLM unavailable"), "Business"]

        with patch("src.categorizer.create_categorize_chain", return_value=mock_chain):
            result = categorize_articles(articles)

        assert len(result) == 2
        assert result[0].category == "Other"  # fallback on error
        assert result[1].category == "Business"
