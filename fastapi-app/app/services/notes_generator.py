from __future__ import annotations

import json

from ..models.project_state import ProjectState
from ..schemas.generate import SlideNotes
from .llm_client import LLMClient


class NotesGenerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def generate_notes(self, state: ProjectState) -> list[SlideNotes]:
        if not state.slides:
            raise ValueError("No slides found. Call /generate/slides first.")

        notes: list[SlideNotes] = []
        for slide in state.slides:
            payload = {"slide": slide.model_dump()}
            prompt = f"TASK:generate_notes\nDATA_JSON:{json.dumps(payload, ensure_ascii=False)}"
            response = await self._llm_client.generate_json(prompt, response_schema={"slide_id": "str", "notes": "str"})
            notes.append(SlideNotes.model_validate(response))

        return notes

