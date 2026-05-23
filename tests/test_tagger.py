from src.tagger import parse_tagging_response, get_all_keywords


SAMPLE_RESPONSE = (
    "KEYWORDS: artificial intelligence, technology, smartphones\n"
    "PEOPLE: Tim Cook, Elon Musk\n"
    "ORGANIZATIONS: Apple, Tesla\n"
    "LOCATIONS: California, Silicon Valley"
)


class TestParseTaggingResponse:
    def test_keywords_field_is_a_list(self):
        result = parse_tagging_response(SAMPLE_RESPONSE)
        assert isinstance(result["keywords"], list)

    def test_keywords_field_is_not_none(self):
        result = parse_tagging_response(SAMPLE_RESPONSE)
        assert result["keywords"] is not None

    def test_keywords_field_is_not_a_string(self):
        result = parse_tagging_response(SAMPLE_RESPONSE)
        assert not isinstance(result["keywords"], str)

    def test_extracted_keywords_appear_in_input(self):
        result = parse_tagging_response(SAMPLE_RESPONSE)
        input_lower = SAMPLE_RESPONSE.lower()
        for keyword in result["keywords"]:
            assert keyword in input_lower

    def test_keywords_are_lowercase(self):
        result = parse_tagging_response(SAMPLE_RESPONSE)
        for keyword in result["keywords"]:
            assert keyword == keyword.lower()

    def test_people_extracted_correctly(self):
        result = parse_tagging_response(SAMPLE_RESPONSE)
        assert "Tim Cook" in result["people"]
        assert "Elon Musk" in result["people"]

    def test_none_values_produce_empty_lists(self):
        none_response = (
            "KEYWORDS: None\n"
            "PEOPLE: None\n"
            "ORGANIZATIONS: None\n"
            "LOCATIONS: None"
        )
        result = parse_tagging_response(none_response)
        assert result["keywords"] == []
        assert result["people"] == []

    def test_empty_string_does_not_crash(self):
        result = parse_tagging_response("")
        assert isinstance(result["keywords"], list)
        assert result["keywords"] == []


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
