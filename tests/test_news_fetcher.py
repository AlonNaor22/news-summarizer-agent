"""Tests for src/news_fetcher.py — RSS fetching and date parsing."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.news_fetcher import fetch_from_rss, parse_date


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------


def test_parse_date_rfc2822():
    assert parse_date("Mon, 18 Jan 2026 14:30:00 GMT") == "January 18, 2026 at 14:30"


def test_parse_date_empty_returns_none():
    assert parse_date("") is None


def test_parse_date_invalid_returns_original():
    assert parse_date("not-a-date") == "not-a-date"


# ---------------------------------------------------------------------------
# fetch_from_rss helpers
# ---------------------------------------------------------------------------


def _make_feed(entries=None, bozo=False):
    feed = MagicMock()
    feed.bozo = bozo
    feed.entries = entries or []
    return feed


def _entry(title="Title", summary="Summary", link="http://example.com/1", published=""):
    return {"title": title, "summary": summary, "link": link, "published": published}


# ---------------------------------------------------------------------------
# fetch_from_rss
# ---------------------------------------------------------------------------


@patch("src.news_fetcher.feedparser.parse")
@patch("src.news_fetcher.requests.get")
def test_fetch_from_rss_happy_path(mock_get, mock_fp):
    mock_response = MagicMock()
    mock_response.content = b"<rss/>"
    mock_get.return_value = mock_response
    mock_fp.return_value = _make_feed(entries=[_entry(title="Breaking News")])

    articles = fetch_from_rss("http://example.com/rss.xml", "TestSource")

    assert len(articles) == 1
    assert articles[0].title == "Breaking News"
    assert articles[0].source == "TestSource"
    assert articles[0].url == "http://example.com/1"
    # Must pass bytes to feedparser, not the URL string
    mock_get.assert_called_once_with("http://example.com/rss.xml", timeout=10)
    mock_fp.assert_called_once_with(b"<rss/>")


@patch("src.news_fetcher.requests.get")
def test_fetch_from_rss_timeout_returns_empty(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectTimeout()

    articles = fetch_from_rss("http://10.255.255.1/rss.xml", "Unreachable")

    assert articles == []


@patch("src.news_fetcher.requests.get")
def test_fetch_from_rss_request_exception_returns_empty(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("connection refused")

    articles = fetch_from_rss("http://example.com/rss.xml", "FailingSource")

    assert articles == []


@patch("src.news_fetcher.feedparser.parse")
@patch("src.news_fetcher.requests.get")
def test_fetch_from_rss_bozo_no_entries_returns_empty(mock_get, mock_fp):
    mock_response = MagicMock()
    mock_response.content = b"garbage"
    mock_get.return_value = mock_response
    mock_fp.return_value = _make_feed(bozo=True, entries=[])

    articles = fetch_from_rss("http://example.com/rss.xml", "BadFeed")

    assert articles == []


@patch("src.news_fetcher.feedparser.parse")
@patch("src.news_fetcher.requests.get")
def test_fetch_from_rss_respects_max_articles(mock_get, mock_fp):
    mock_response = MagicMock()
    mock_response.content = b"<rss/>"
    mock_get.return_value = mock_response
    mock_fp.return_value = _make_feed(entries=[_entry(title=f"Article {i}") for i in range(10)])

    articles = fetch_from_rss("http://example.com/rss.xml", "Source", max_articles=3)

    assert len(articles) == 3
