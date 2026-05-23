import config


def test_model_name_is_nonempty_string():
    assert isinstance(config.MODEL_NAME, str)
    assert len(config.MODEL_NAME) > 0


def test_rss_feeds_is_nonempty_dict():
    assert isinstance(config.RSS_FEEDS, dict)
    assert len(config.RSS_FEEDS) > 0


def test_categories_is_nonempty_list():
    assert isinstance(config.CATEGORIES, list)
    assert len(config.CATEGORIES) > 0


def test_categories_contains_other_fallback():
    assert "Other" in config.CATEGORIES


def test_temperature_is_numeric():
    assert isinstance(config.TEMPERATURE, (int, float))


def test_required_keys_exist():
    required = ["MODEL_NAME", "RSS_FEEDS", "CATEGORIES", "TEMPERATURE", "MAX_TOKENS"]
    for key in required:
        assert hasattr(config, key), f"config is missing required key: {key}"
