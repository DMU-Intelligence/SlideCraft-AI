from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..schemas.generate import OutlineItem, SlideContent


def _format_validation_error(exc: ValidationError) -> str:
    first_error = exc.errors()[0]
    location = ".".join(str(part) for part in first_error.get("loc", ()))
    message = str(first_error.get("msg", "validation error"))
    return f"{location}: {message}" if location else message


def validate_outline_payload(outline_payload: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        for title, item in outline_payload.items():
            OutlineItem.model_validate(item)
    except ValidationError as exc:
        return False, f"outline ({_format_validation_error(exc)})"
    return True, None


def validate_slides_payload(slides_payload: list[dict[str, Any]]) -> tuple[bool, str | None]:
    try:
        for index, slide in enumerate(slides_payload, start=1):
            SlideContent.model_validate(slide)
    except ValidationError as exc:
        return False, f"{index}번째 slide ({_format_validation_error(exc)})"
    return True, None
