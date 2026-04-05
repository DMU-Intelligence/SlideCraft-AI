from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


class OutlineItem(BaseModel):
    id: str
    role: str
    goal: str
    key_points: list[str] = Field(default_factory=list)
    tone: str = "informative"
    description: str
    page_size: int = 1
    preferred_variant: str | None = None


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
    shape_type: Literal["rectangle"] = "rectangle"
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
    bullet_char: str = "-"
    bullet_color: str = "#5B8DEF"
    font_name: str = "Malgun Gothic"
    font_size: int = 16
    font_color: str = "#1E293B"


SlideElement = Annotated[
    Union[TextBoxElement, ShapeElement, BulletListElement],
    Field(discriminator="type"),
]


class PageLayout(BaseModel):
    background: str = "#FFFFFF"
    elements: list[SlideElement] = Field(default_factory=list)
    slots: dict[str, Any] = Field(default_factory=dict)


class SlideContent(BaseModel):
    title: str
    theme: str = "clean_light"
    slide_variant: Literal[
        "title_page",
        "content_box_list",
        "content_two_panel",
        "content_sidebar",
        "content_split_band",
        "content_compact",
        "closing_page",
        "title",
        "section",
        "summary",
        "two_column",
    ] = "summary"
    pages: list[PageLayout] = Field(default_factory=list)


class SlideEvaluation(BaseModel):
    passed: bool
    score: int = Field(ge=1, le=5)
    checklist: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    feedback: str = ""


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
