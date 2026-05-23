from src.similarity import (
    calculate_keyword_similarity,
    calculate_entity_similarity,
    calculate_combined_similarity,
)


class TestKeywordSimilarity:
    def test_identical_keywords_score_one(self):
        a = {"keywords": ["ai", "technology", "apple"]}
        b = {"keywords": ["ai", "technology", "apple"]}
        assert calculate_keyword_similarity(a, b) == 1.0

    def test_no_overlap_scores_zero(self):
        a = {"keywords": ["politics", "election"]}
        b = {"keywords": ["sports", "basketball"]}
        assert calculate_keyword_similarity(a, b) == 0.0

    def test_partial_overlap_is_between_zero_and_one(self):
        a = {"keywords": ["ai", "technology", "apple"]}
        b = {"keywords": ["ai", "technology", "google"]}
        score = calculate_keyword_similarity(a, b)
        assert 0.0 < score < 1.0

    def test_identical_scores_higher_than_no_overlap(self):
        a = {"keywords": ["ai", "technology"]}
        b_identical = {"keywords": ["ai", "technology"]}
        b_no_overlap = {"keywords": ["sports", "basketball"]}
        assert calculate_keyword_similarity(a, b_identical) > calculate_keyword_similarity(a, b_no_overlap)

    def test_empty_keyword_list_returns_zero_no_crash(self):
        a = {"keywords": []}
        b = {"keywords": ["ai", "technology"]}
        assert calculate_keyword_similarity(a, b) == 0.0

    def test_both_empty_returns_zero_no_crash(self):
        assert calculate_keyword_similarity({"keywords": []}, {"keywords": []}) == 0.0

    def test_self_similarity_is_one(self):
        article = {"keywords": ["ai", "machine learning", "technology"]}
        assert calculate_keyword_similarity(article, article) == 1.0


class TestCombinedSimilarity:
    def test_same_category_yields_higher_score_than_different(self):
        base = {"keywords": ["ai"], "people": [], "organizations": [], "locations": []}
        same_cat = {**base, "category": "Technology"}
        diff_cat = {**base, "category": "Business"}
        target = {**base, "category": "Technology"}
        assert (
            calculate_combined_similarity(target, same_cat)["overall"]
            > calculate_combined_similarity(target, diff_cat)["overall"]
        )

    def test_result_contains_required_keys(self):
        a = {"keywords": ["ai"], "people": [], "organizations": [], "locations": []}
        result = calculate_combined_similarity(a, a)
        for key in ("overall", "keyword_similarity", "entity_similarity", "same_category"):
            assert key in result
