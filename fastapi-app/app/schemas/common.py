from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    """Generic metadata bag for frontend-friendly responses."""

    source_filename: str | None = None
    file_type: str | None = None
    parser_version: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    message: str
    details: str | None = None

