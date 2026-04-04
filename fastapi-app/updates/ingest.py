from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import Metadata


class IngestDocumentResponse(BaseModel):
    project_id: int
    title: str
    language: str
    content: str          # AI 정리 후 텍스트
    metadata: Metadata
    stats: dict[str, Any] = Field(default_factory=dict)
