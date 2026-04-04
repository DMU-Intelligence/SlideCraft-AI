from __future__ import annotations

from ..models.project_state import ProjectState
from ..schemas.generate import OutlineItem, SlideContent
from .llm_client import LLMClient


class RegenerationService:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def regenerate_slide(
        self,
        state: ProjectState,
        slide_title: str,
        user_request: str = "",
    ) -> SlideContent:
        if slide_title not in state.outline:
            raise ValueError(f"'{slide_title}' 슬라이드가 outline에 없습니다.")

        item = state.outline[slide_title]
        existing = next((s for s in state.slides if s.title == slide_title), None)
        current_slide = existing.model_dump() if existing else {}

        titles = list(state.outline.keys())
        idx = titles.index(slide_title)
        prev_title = titles[idx - 1] if idx > 0 else ""
        next_title = titles[idx + 1] if idx < len(titles) - 1 else ""

        if user_request:
            raw = await self._llm_client.regenerate_slide(
                slide_title=slide_title,
                description=item.description,
                page_size=item.page_size,
                content=state.content,
                language=state.language,
                user_request=user_request,
                current_slide=current_slide,
            )
        else:
            raw = await self._llm_client.generate_slide(
                slide_title=slide_title,
                description=item.description,
                page_size=item.page_size,
                content=state.content,
                language=state.language,
                prev_title=prev_title,
                next_title=next_title,
            )

        updated = SlideContent.model_validate(raw)

        # 기존 슬라이드 교체 or 추가
        for i, s in enumerate(state.slides):
            if s.title == slide_title:
                state.slides[i] = updated
                break
        else:
            state.slides.append(updated)

        state.touch()
        return updated

    async def regenerate_notes(self, state: ProjectState) -> str:
        if not state.slides:
            raise ValueError("슬라이드가 없습니다.")

        notes = await self._llm_client.generate_notes(
            slides=[s.model_dump() for s in state.slides],
            language=state.language,
        )
        state.notes = notes
        state.touch()
        return notes

    async def update_outline(
        self, state: ProjectState, titles: list[str]
    ) -> dict[str, OutlineItem]:
        """사용자 지정 titles 목록으로 outline 재생성 (description/page_size는 AI 생성)"""
        raw = await self._llm_client.update_outline(
            titles=titles,
            content=state.content,
            language=state.language,
        )
        outline = {
            title: OutlineItem.model_validate(item)
            for title, item in raw.items()
        }
        state.outline = outline
        state.touch()
        return outline
