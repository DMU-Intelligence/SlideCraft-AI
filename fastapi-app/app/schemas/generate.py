from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

SLIDE_WIDTH_INCHES = 13.33
SLIDE_HEIGHT_INCHES = 7.5
_SLOT_TEXT_KEYS = {"eyebrow", "headline", "body", "highlight", "title_box_label"}
_SLOT_LIST_KEYS = {"bullets", "left_points", "right_points", "people"}
_SLOT_ALLOWED_KEYS = _SLOT_TEXT_KEYS | _SLOT_LIST_KEYS


class OutlineItem(BaseModel):
    id: str
    role: str
    goal: str
    key_points: list[str] = Field(default_factory=list)
    tone: str = "informative"
    description: str
    page_size: int = 1
    preferred_variant: Literal[
        "title_page",
        "content_box_list",
        "content_two_panel",
        "content_sidebar",
        "content_split_band",
        "content_compact",
        "closing_page",
    ] | None = None

    @field_validator("page_size", mode="before")
    @classmethod
    def _normalize_page_size(cls, value: Any) -> int:
        if isinstance(value, bool):
            return 1
        if isinstance(value, (int, float)):
            numeric = float(value)
        elif isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return 1
            try:
                numeric = float(stripped)
            except ValueError:
                return 1
        else:
            return 1

        if numeric <= 1:
            return 1
        if numeric >= 2:
            return 2
        return 2 if numeric >= 1.5 else 1


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

    @model_validator(mode="after")
    def _validate_bounds(self) -> "PositionedElement":
        if self.w <= 0 or self.h <= 0:
            raise ValueError("Element width and height must be positive.")
        if self.x < 0 or self.y < 0:
            raise ValueError("Element coordinates must be non-negative.")
        if self.x + self.w > SLIDE_WIDTH_INCHES + 0.01:
            raise ValueError("Element exceeds slide width.")
        if self.y + self.h > SLIDE_HEIGHT_INCHES + 0.01:
            raise ValueError("Element exceeds slide height.")
        return self


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
    shape_type: Literal["rectangle", "round_rectangle"] = "rectangle"
    fill_color: str = "#5B8DEF"


class BulletListElement(PositionedElement):
    type: Literal["bullet_list"] = "bullet_list"
    items: list[str]
    bullet_char: str = "-"
    bullet_color: str = "#5B8DEF"
    font_name: str = "Malgun Gothic"
    font_size: int = 16
    font_color: str = "#1E293B"

    @field_validator("items")
    @classmethod
    def _validate_items(cls, items: list[str]) -> list[str]:
        normalized = [str(item).strip() for item in items if str(item).strip()]
        if not normalized:
            raise ValueError("bullet_list.items must not be empty.")
        if len(normalized) > 5:
            raise ValueError("bullet_list.items must contain at most 5 items.")
        return normalized


SlideElement = Annotated[
    Union[TextBoxElement, ShapeElement, BulletListElement],
    Field(discriminator="type"),
]


class PageLayout(BaseModel):
    background: str = "#FFFFFF"
    elements: list[SlideElement] = Field(default_factory=list)
    slots: dict[str, Any] = Field(default_factory=dict)

    @field_validator("slots")
    @classmethod
    def _validate_slots(cls, slots: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(slots, dict):
            raise ValueError("slots must be an object.")

        unknown_keys = [key for key in slots if key not in _SLOT_ALLOWED_KEYS]
        if unknown_keys:
            raise ValueError(f"Unsupported slots keys: {', '.join(sorted(unknown_keys))}")

        normalized: dict[str, Any] = {}
        for key, value in slots.items():
            if key in _SLOT_TEXT_KEYS:
                if not isinstance(value, str):
                    raise ValueError(f"slots.{key} must be a string.")
                text = value.strip()
                if text:
                    normalized[key] = text
                continue

            if key in _SLOT_LIST_KEYS:
                if not isinstance(value, list):
                    raise ValueError(f"slots.{key} must be an array.")
                items = [str(item).strip() for item in value if str(item).strip()]
                if len(items) > 5:
                    raise ValueError(f"slots.{key} must contain at most 5 items.")
                if items:
                    normalized[key] = items

        return normalized

    @model_validator(mode="after")
    def _validate_page_payload(self) -> "PageLayout":
        if not self.elements and not self.slots:
            raise ValueError("PageLayout requires at least one of elements or slots.")
        return self


class SlideContent(BaseModel):
    title: str
    theme: Literal["clean_light", "bold_dark", "editorial"] = "clean_light"
    slide_variant: Literal[
        "title_page",
        "content_box_list",
        "content_two_panel",
        "content_sidebar",
        "content_split_band",
        "content_compact",
        "closing_page",
    ] = "content_box_list"
    pages: list[PageLayout] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_pages(self) -> "SlideContent":
        if not self.pages:
            raise ValueError("SlideContent.pages must not be empty.")
        return self


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
    template_name: str | None = None


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
    template_name: str | None = None


class GenerateAllResponse(BaseModel):
    project_id: int
    title: str
    outline: dict[str, OutlineItem]
    slides: list[SlideContent]
    notes: str
    stats: dict[str, Any] = Field(default_factory=dict)
