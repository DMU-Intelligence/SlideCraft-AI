from __future__ import annotations

from ..models.project_state import ProjectState
from ..schemas.generate import OutlineItem
from .llm_client import LLMClient


class OutlineGenerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def generate_outline(self, state: ProjectState) -> dict[str, OutlineItem]:
        raw = await self._llm_client.generate_outline(
            title=state.title,
            content=state.content,
            language=state.language,
        )
        return {
            title: OutlineItem.model_validate(item)
            for title, item in raw.items()
        }
