from unittest.mock import MagicMock, patch

from src.models import Article
from src.tagger import ArticleTags, get_all_keywords, tag_article


SAMPLE_TAGS = ArticleTags(
    keywords=["artificial intelligence", "technology", "smartphones"],
    people=["Tim Cook", "Elon Musk"],
    organizations=["Apple", "Tesla"],
    locations=["California", "Silicon Valley"],
)


def _make_article(**kwargs) -> Article:
    kwargs.setdefault("title", "Sample tagging article")
    kwargs.setdefault("source", "Test")
    kwargs.setdefault("url", "")
    kwargs.setdefault(
        "summary",
        "Apple unveiled new AI-powered iPhone features at WWDC, with Tim Cook on stage in California.",
    )
    return Article(**kwargs)


class TestArticleTagsModel:
    def test_keywords_field_is_a_list(self):
        assert isinstance(SAMPLE_TAGS.keywords, list)

    def test_keywords_are_lowercased_by_validator(self):
        tags = ArticleTags(keywords=["AI", "Tech", "Smartphones"])
        assert tags.keywords == ["ai", "tech", "smartphones"]

    def test_blank_keywords_are_filtered_out(self):
        tags = ArticleTags(keywords=["ai", "", "  ", "tech"])
        assert tags.keywords == ["ai", "tech"]

    def test_defaults_produce_empty_lists(self):
        tags = ArticleTags()
        assert tags.keywords == []
        assert tags.people == []
        assert tags.organizations == []
        assert tags.locations == []

    def test_people_and_orgs_preserve_casing(self):
        # Only keywords are normalized; entity names should keep their original casing.
        tags = ArticleTags(
            people=["Tim Cook"],
            organizations=["Apple"],
            locations=["California"],
        )
        assert tags.people == ["Tim Cook"]
        assert tags.organizations == ["Apple"]
        assert tags.locations == ["California"]


class TestTagArticleStructuredOutput:
    def test_tag_article_writes_structured_fields_back_to_article(self):
        article = _make_article()

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = SAMPLE_TAGS

        with patch("src.tagger.create_tagging_chain", return_value=mock_chain):
            result = tag_article(article)

        assert result.keywords == ["artificial intelligence", "technology", "smartphones"]
        assert "Tim Cook" in result.people
        assert "Apple" in result.organizations

    def test_short_content_skips_llm_and_clears_tags(self):
        # Short content -> chain.invoke shouldn't run; existing tags are cleared.
        article = _make_article(summary="too short")
        article.keywords = ["stale"]

        mock_chain = MagicMock()

        with patch("src.tagger.create_tagging_chain", return_value=mock_chain):
            tag_article(article)

        mock_chain.invoke.assert_not_called()
        assert article.keywords == []

    def test_empty_pydantic_result_produces_empty_lists(self):
        article = _make_article()

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = ArticleTags()

        with patch("src.tagger.create_tagging_chain", return_value=mock_chain):
            result = tag_article(article)

        assert result.keywords == []
        assert result.people == []


class TestGetAllKeywords:
    def test_counts_keyword_frequency_correctly(self):
        articles = [
            {"keywords": ["ai", "technology"]},
            {"keywords": ["ai", "business"]},
            {"keywords": ["technology"]},
        ]
        counts = get_all_keywords(articles)
        assert counts["ai"] == 2
        assert counts["technology"] == 2
        assert counts["business"] == 1

    def test_empty_article_list_returns_empty_dict(self):
        assert get_all_keywords([]) == {}
