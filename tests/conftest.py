import pytest


@pytest.fixture
def sample_article():
    return {
        "title": "Tech Giant Announces Revolutionary AI Breakthrough",
        "content": (
            "Silicon Valley's leading technology company unveiled a groundbreaking "
            "artificial intelligence system capable of solving complex scientific problems. "
            "The software, developed over five years, reportedly surpasses human-level "
            "performance on multiple benchmarks and could reshape the industry."
        ),
        "source": "TechCrunch",
        "url": "https://example.com/articles/ai-breakthrough-2024",
        "published_at": "2024-01-15T10:30:00Z",
    }
