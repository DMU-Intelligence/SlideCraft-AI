from __future__ import annotations

import json
import re
from typing import Any

from ..models.project_state import ProjectState
from ..schemas.generate import PresentationOutline, Slide, SlideNotes
from .llm_client import LLMClient


def _parse_slide_number(slide_id: str) -> int | None:
    m = re.match(r"^slide_(\d+)$", slide_id)
    if not m:
        return None
    return int(m.group(1))


class RegenerationService:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def regenerate_slide(
        self,
        state: ProjectState,
        slide_id: str,
        force: bool = False,
    ) -> Slide:
        if state.outline is None:
            raise ValueError("Project outline is missing.")

        existing_index = next((i for i, s in enumerate(state.slides) if s.slide_id == slide_id), None)
        if existing_index is None:
            raise ValueError(f"Slide not found: {slide_id}")

        if slide_id in set(state.user_edited_slide_ids) and not force:
            return state.slides[existing_index]

        outline: PresentationOutline = state.outline
        slide_number = _parse_slide_number(slide_id)
        if slide_number is None:
            raise ValueError(f"Invalid slide_id: {slide_id}")

        outline_items = outline.slide_outline
        outline_index = next((i for i, it in enumerate(outline_items) if it.slide_number == slide_number), None)
        if outline_index is None:
            raise ValueError(f"Outline item not found for slide_number={slide_number}")

        item = outline_items[outline_index]
        prev_title = outline_items[outline_index - 1].title if outline_index - 1 >= 0 else ""
        next_title = outline_items[outline_index + 1].title if outline_index + 1 < len(outline_items) else ""

        chunks_for_prompt: list[dict[str, Any]] = [
            {"chunk_id": c.chunk_id, "text": (c.text[:2500] if c.text else "")}
            for c in state.chunks
        ]

        payload = {
            "slide_number": item.slide_number,
            "slide_id": slide_id,
            "outline_item": item.model_dump(),
            "prev_title": prev_title,
            "next_title": next_title,
            "chunks": chunks_for_prompt,
            "existing_slide": state.slides[existing_index].model_dump(),
        }
        prompt = f"TASK:regenerate_slide\nDATA_JSON:{json.dumps(payload, ensure_ascii=False)}"
        response = await self._llm_client.generate_json(prompt, response_schema={"slide_id": "str"})
        updated = Slide.model_validate(response)

        state.slides[existing_index] = updated
        state.touch()
        return updated

    async def regenerate_notes(
        self,
        state: ProjectState,
        slide_ids: list[str] | None = None,
    ) -> list[SlideNotes]:
        if not state.slides:
            raise ValueError("No slides found.")

        target_ids: list[str]
        if slide_ids:
            target_ids = slide_ids
        else:
            target_ids = [s.slide_id for s in state.slides]

        notes_index: dict[str, int] = {n.slide_id: i for i, n in enumerate(state.notes)}
        updated_notes: list[SlideNotes] = []

        for slide in state.slides:
            if slide.slide_id not in set(target_ids):
                continue
            payload = {"slide": slide.model_dump()}
            prompt = f"TASK:regenerate_notes\nDATA_JSON:{json.dumps(payload, ensure_ascii=False)}"
            response = await self._llm_client.generate_json(prompt, response_schema={"slide_id": "str", "notes": "str"})
            note = SlideNotes.model_validate(response)
            idx = notes_index.get(note.slide_id)
            if idx is None:
                state.notes.append(note)
            else:
                state.notes[idx] = note
            updated_notes.append(note)

        state.touch()
        return updated_notes

