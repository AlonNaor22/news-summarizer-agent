"""Pydantic models for the news pipeline.

The :class:`Article` model replaces the loose ``dict`` representation that
every src/ module used to pass around. Fields are populated incrementally
as articles flow through the pipeline (fetch -> summarize -> categorize ->
tag -> sentiment), so most are optional with sensible defaults.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Article(BaseModel):
    """A news article passed through the processing pipeline.

    Only ``title``, ``source``, and ``url`` are required (set at fetch time).
    Every other field starts empty and is filled in by a later pipeline stage.
    """

    model_config = ConfigDict(extra="ignore")

    title: str
    source: str
    url: str

    description: str = ""
    summary: str = ""
    published: Optional[str] = None

    category: Optional[str] = None
    secondary_categories: list[str] = Field(default_factory=list)

    sentiment: Optional[str] = None
    sentiment_confidence: Optional[str] = None
    sentiment_reason: Optional[str] = None

    keywords: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)

    author: Optional[str] = None
    image_url: Optional[str] = None
    id: Optional[int] = None

    similarity: Optional[dict[str, Any]] = None
