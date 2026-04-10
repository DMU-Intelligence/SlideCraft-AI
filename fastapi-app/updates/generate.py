from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


# ── Outline ────────────────────────────────────────────────────────────────────

class OutlineItem(BaseModel):
    description: str
    page_size: int = 1


# ── Element 타입 ───────────────────────────────────────────────────────────────

class TextBoxElement(BaseModel):
    type: Literal["text_box"] = "text_box"
    text: str
    left: float
    top: float
    width: float
    height: float
    font_name: str = "Malgun Gothic"
    font_size: int = 16
    font_bold: bool = False
    font_color: str = "#FFFFFF"
    align: Literal["left", "center", "right"] = "left"


class ShapeElement(BaseModel):
    type: Literal["shape"] = "shape"
    shape_type: Literal["rectangle", "round_rectangle"] = "rectangle"
    left: float
    top: float
    width: float
    height: float
    fill_color: str = "#5B8DEF"


class BulletListElement(BaseModel):
    type: Literal["bullet_list"] = "bullet_list"
    left: float
    top: float
    width: float
    height: float
    items: list[str]
    bullet_char: str = "▸"
    bullet_color: str = "#5B8DEF"
    font_name: str = "Malgun Gothic"
    font_size: int = 16
    font_color: str = "#D4D8E8"


# Pydantic v2 discriminated union
SlideElement = Annotated[
    Union[TextBoxElement, ShapeElement, BulletListElement],
    Field(discriminator="type"),
]


# ── 슬라이드 구조 ──────────────────────────────────────────────────────────────

class PageLayout(BaseModel):
    background: str = "#0F172A"
    elements: list[SlideElement] = Field(default_factory=list)


class SlideContent(BaseModel):
    title: str
    pages: list[PageLayout] = Field(default_factory=list)


# ── Request / Response ─────────────────────────────────────────────────────────

class GenerateOutlineRequest(BaseModel):
    project_id: int


class GenerateOutlineResponse(BaseModel):
    project_id: int
    outline: dict[str, OutlineItem]


class GenerateSlidesRequest(BaseModel):
    project_id: int


class GenerateSlidesResponse(BaseModel):
    project_id: int
    slides: list[SlideContent]


class GenerateNotesRequest(BaseModel):
    project_id: int


class GenerateNotesResponse(BaseModel):
    project_id: int
    notes: str


class GenerateAllRequest(BaseModel):
    project_id: int


class GenerateAllResponse(BaseModel):
    project_id: int
    outline: dict[str, OutlineItem]
    slides: list[SlideContent]
    notes: str
    stats: dict[str, Any] = Field(default_factory=dict)
