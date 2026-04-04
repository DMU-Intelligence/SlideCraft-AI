from __future__ import annotations

from pydantic import BaseModel

from .generate import OutlineItem, SlideContent


class RegenerateSlideRequest(BaseModel):
    project_id: int
    slide_title: str      # outline key (슬라이드 제목)
    user_request: str = ""  # 수정 요청 사항


class RegenerateSlideResponse(BaseModel):
    project_id: int
    slide: SlideContent


class RegenerateNotesRequest(BaseModel):
    project_id: int


class RegenerateNotesResponse(BaseModel):
    project_id: int
    notes: str


class UpdateOutlineRequest(BaseModel):
    project_id: int
    outline_titles: list[str]   # 사용자 지정 목차 제목 목록 (순서 유지)


class UpdateOutlineResponse(BaseModel):
    project_id: int
    outline: dict[str, OutlineItem]
