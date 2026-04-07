from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, model_validator


class OutlineItem(BaseModel):
    id: str
    role: str
    goal: str
    key_points: list[str] = Field(default_factory=list)
    tone: str = "informative"
    description: str
    page_size: int = 1
    preferred_variant: str | None = None


class PositionedElement(BaseModel):
    x: float
    y: float
    w: float
    h: float

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_coordinates(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        upgraded = dict(data)
        upgraded.setdefault("x", upgraded.get("left"))
        upgraded.setdefault("y", upgraded.get("top"))
        upgraded.setdefault("w", upgraded.get("width"))
        upgraded.setdefault("h", upgraded.get("height"))
        return upgraded

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def width(self) -> float:
        return self.w

    @property
    def height(self) -> float:
        return self.h


class TextBoxElement(PositionedElement):
    type: Literal["text_box"] = "text_box"
    text: str
    font_name: str = "Malgun Gothic"
    font_size: int = 16
    font_bold: bool = False
    font_color: str = "#FFFFFF"
    align: Literal["left", "center", "right"] = "left"


class ShapeElement(PositionedElement):
    type: Literal["shape"] = "shape"
    shape_type: Literal["rectangle"] = "rectangle"
    fill_color: str = "#5B8DEF"


class BulletListElement(PositionedElement):
    type: Literal["bullet_list"] = "bullet_list"
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


class OutlineGenerationResult(BaseModel):
    title: str
    outline: dict[str, OutlineItem]


class GenerateOutlineResponse(BaseModel):
    project_id: int
    title: str
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
    title: str
    outline: dict[str, OutlineItem]
    slides: list[SlideContent]
    notes: str
    stats: dict[str, Any] = Field(default_factory=dict)
