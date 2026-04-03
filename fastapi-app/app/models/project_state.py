from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..schemas.generate import PresentationOutline, Slide, SlideNotes
from ..schemas.ingest import ParsedChunk


class ProjectState(BaseModel):
    project_id: str
    title: str
    language: str
    tone: str

    source_document_text: str
    chunks: list[ParsedChunk] = Field(default_factory=list)
    summary: str = ""

    outline: PresentationOutline | None = None
    slides: list[Slide] = Field(default_factory=list)
    notes: list[SlideNotes] = Field(default_factory=list)

    user_edited_slide_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()

