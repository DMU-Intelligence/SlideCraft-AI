from __future__ import annotations

import json
from typing import Any

from ..models.project_state import ProjectState
from ..schemas.generate import PresentationOutline, Slide
from .llm_client import LLMClient


class SlideGenerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def generate_slides(
        self,
        state: ProjectState,
        max_slides: int = 8,
    ) -> list[Slide]:
        if state.outline is None:
            raise ValueError("Project outline is missing. Call /generate/outline first.")

        outline: PresentationOutline = state.outline
        slide_items = outline.slide_outline[: max(1, max_slides)]

        chunks_for_prompt: list[dict[str, Any]] = [
            {"chunk_id": c.chunk_id, "text": (c.text[:2500] if c.text else "")}
            for c in state.chunks
        ]

        slides: list[Slide] = []
        for i, item in enumerate(slide_items):
            slide_id = f"slide_{item.slide_number:02d}"
            prev_title = slide_items[i - 1].title if i - 1 >= 0 else ""
            next_title = slide_items[i + 1].title if i + 1 < len(slide_items) else ""
            payload = {
                "slide_number": item.slide_number,
                "slide_id": slide_id,
                "outline_item": item.model_dump(),
                "prev_title": prev_title,
                "next_title": next_title,
                "chunks": chunks_for_prompt,
            }
            prompt = f"TASK:generate_slide\nDATA_JSON:{json.dumps(payload, ensure_ascii=False)}"
            response = await self._llm_client.generate_json(prompt, response_schema={"slide_id": "str"})
            slides.append(Slide.model_validate(response))

        return slides

