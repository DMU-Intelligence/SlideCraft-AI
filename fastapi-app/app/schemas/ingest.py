from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import Metadata


class ParsedChunk(BaseModel):
    chunk_id: str
    text: str
    heading: str | None = None
    start_char: int
    end_char: int


class IngestDocumentRequest(BaseModel):
    project_id: str | None = None
    title: str | None = None
    language: str = "en"
    tone: str = "neutral"
    file_path: str | None = None
    max_chunk_chars: int = 1200
    chunk_overlap: int = 150
    user_edited_slide_ids: list[str] = Field(default_factory=list)


class IngestDocumentResponse(BaseModel):
    project_id: str
    raw_text: str
    chunks: list[ParsedChunk]
    summary: str
    metadata: Metadata
    stats: dict[str, Any] = Field(default_factory=dict)

