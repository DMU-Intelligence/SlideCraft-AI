from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PresentationOutlineItem(BaseModel):
    slide_number: int
    title: str
    goal: str


class PresentationOutline(BaseModel):
    deck_title: str
    presentation_objective: str
    slide_outline: list[PresentationOutlineItem]


class Slide(BaseModel):
    slide_id: str
    title: str
    goal: str
    bullets: list[str]
    source_chunk_ids: list[str]


class SlideNotes(BaseModel):
    slide_id: str
    notes: str


class GenerateOutlineRequest(BaseModel):
    project_id: str


class GenerateOutlineResponse(BaseModel):
    project_id: str
    outline: PresentationOutline
    summary: str


class GenerateSlidesRequest(BaseModel):
    project_id: str
    max_slides: int = 8


class GenerateSlidesResponse(BaseModel):
    project_id: str
    slides: list[Slide]


class GenerateNotesRequest(BaseModel):
    project_id: str


class GenerateNotesResponse(BaseModel):
    project_id: str
    notes: list[SlideNotes]


class GenerateAllRequest(BaseModel):
    project_id: str
    max_slides: int = 8


class GenerateAllResponse(BaseModel):
    project_id: str
    outline: PresentationOutline
    slides: list[Slide]
    notes: list[SlideNotes]
    summary: str
    stats: dict[str, Any] = Field(default_factory=dict)

