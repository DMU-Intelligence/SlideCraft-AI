from __future__ import annotations

import json

from ..models.project_state import ProjectState
from ..schemas.generate import PresentationOutline
from .llm_client import LLMClient


class OutlineGenerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def generate_outline(self, state: ProjectState, max_slides: int = 8) -> PresentationOutline:
        slide_count_hint = max(1, min(max_slides, max(4, len(state.chunks) // 2)))
        payload = {
            "title": state.title,
            "language": state.language,
            "tone": state.tone,
            "summary": state.summary,
            "max_slides": max_slides,
            "slide_count_hint": slide_count_hint,
        }
        prompt = f"TASK:generate_outline\nDATA_JSON:{json.dumps(payload, ensure_ascii=False)}"
        response = await self._llm_client.generate_json(prompt, response_schema={"deck_title": "str"})
        return PresentationOutline.model_validate(response)

