from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..schemas.generate import OutlineItem, SlideContent


def validate_outline_payload(outline_payload: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        for title, item in outline_payload.items():
            OutlineItem.model_validate(item)
    except ValidationError:
        return False, "outline"
    return True, None


def validate_slides_payload(slides_payload: list[dict[str, Any]]) -> tuple[bool, str | None]:
    try:
        for index, slide in enumerate(slides_payload, start=1):
            SlideContent.model_validate(slide)
    except ValidationError:
        return False, f"{index}번째 slide"
    return True, None

