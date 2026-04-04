from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..schemas.generate import OutlineItem, SlideContent


class ProjectState(BaseModel):
    project_id: int                          # auto-increment (InMemory: 1부터 +1)
    title: str
    language: Literal["ko", "en"] = "ko"

    source_document_text: str = ""           # PDF 등에서 추출한 원문 그대로
    content: str = ""                        # AI 정리 이후 텍스트

    outline: dict[str, OutlineItem] = Field(default_factory=dict)
    slides: list[SlideContent] = Field(default_factory=list)
    notes: str = ""                          # 전체 슬라이드 대본 (단일 str)

    metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
