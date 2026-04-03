from __future__ import annotations

from pydantic import BaseModel, Field

from .generate import Slide, SlideNotes


class RegenerateSlideRequest(BaseModel):
    project_id: str
    slide_id: str
    force: bool = False
    user_edited_slide_ids: list[str] = Field(default_factory=list)


class RegenerateSlideResponse(BaseModel):
    project_id: str
    slide: Slide


class RegenerateNotesRequest(BaseModel):
    project_id: str
    slide_id: str | None = None
    # If provided, notes are regenerated only for these slide ids.
    slide_ids: list[str] = Field(default_factory=list)


class RegenerateNotesResponse(BaseModel):
    project_id: str
    notes: list[SlideNotes]

