from src.categorizer import clean_category, parse_multi_category_response, group_by_category
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


class TestParseMultiCategoryResponse:
    def test_parses_primary_and_secondary(self):
        response = "PRIMARY: Technology\nSECONDARY: Business"
        result = parse_multi_category_response(response)
        assert result["primary"] == "Technology"
        assert "Business" in result["secondary"]

    def test_secondary_none_yields_empty_list(self):
        response = "PRIMARY: Politics\nSECONDARY: None"
        result = parse_multi_category_response(response)
        assert result["secondary"] == []

    def test_empty_input_returns_defaults(self):
        result = parse_multi_category_response("")
        assert result["primary"] == "Other"
        assert result["secondary"] == []


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
