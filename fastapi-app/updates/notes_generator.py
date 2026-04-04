from __future__ import annotations

from ..models.project_state import ProjectState
from .llm_client import LLMClient


class NotesGenerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def generate_notes(self, state: ProjectState) -> str:
        if not state.slides:
            raise ValueError("슬라이드가 없습니다. 먼저 /generate/slides를 호출하세요.")

        slides_data = [s.model_dump() for s in state.slides]
        return await self._llm_client.generate_notes(
            slides=slides_data,
            language=state.language,
        )
