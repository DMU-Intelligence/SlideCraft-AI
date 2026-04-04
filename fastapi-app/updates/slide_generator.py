from __future__ import annotations

from ..models.project_state import ProjectState
from ..schemas.generate import SlideContent
from .llm_client import LLMClient


class SlideGenerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def generate_slides(self, state: ProjectState) -> list[SlideContent]:
        if not state.outline:
            raise ValueError("Outline이 없습니다. 먼저 /generate/outline을 호출하세요.")

        titles = list(state.outline.keys())
        slides: list[SlideContent] = []

        for i, title in enumerate(titles):
            item = state.outline[title]
            prev_title = titles[i - 1] if i > 0 else ""
            next_title = titles[i + 1] if i < len(titles) - 1 else ""

            raw = await self._llm_client.generate_slide(
                slide_title=title,
                description=item.description,
                page_size=item.page_size,
                content=state.content,
                language=state.language,
                prev_title=prev_title,
                next_title=next_title,
            )
            slides.append(SlideContent.model_validate(raw))

        return slides
