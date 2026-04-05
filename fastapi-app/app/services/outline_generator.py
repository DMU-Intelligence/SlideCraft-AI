from __future__ import annotations

from ..models.project_state import ProjectState
from ..schemas.generate import OutlineItem
from .llm_client import LLMClient


class OutlineGenerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def generate_outline(self, state: ProjectState) -> dict[str, OutlineItem]:
        presentation_goal = state.metadata.get(
            "presentation_goal",
            f"문서 '{state.title}'의 핵심 내용을 청중이 빠르게 이해하도록 구조화한다.",
        )
        target_audience = state.metadata.get(
            "target_audience",
            "해당 문서를 읽지 않았거나 배경지식이 많지 않을 수 있는 일반 청중",
        )
        raw = await self._llm_client.generate_outline(
            title=state.title,
            content=state.content,
            language=state.language,
            presentation_goal=presentation_goal,
            target_audience=target_audience,
        )
        return {
            title: OutlineItem.model_validate(item)
            for title, item in raw.items()
        }
