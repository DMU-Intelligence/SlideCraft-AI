from __future__ import annotations

import asyncio
import re

from ..models.project_state import ProjectState
from ..schemas.generate import PageLayout, SlideContent
from .json_validation import validate_outline_payload, validate_slides_payload
from .llm_client import LLMClient

_MAX_CONCURRENT_SLIDES = 5


def _summarize_slide_for_context(slide: SlideContent | None) -> str:
    if slide is None:
        return ""
    bullets: list[str] = []
    for page in slide.pages:
        for key in ("bullets", "left_points", "right_points"):
            slot_value = page.slots.get(key, [])
            if isinstance(slot_value, list):
                bullets.extend(str(item) for item in slot_value)
        for element in page.elements:
            if getattr(element, "type", "") == "bullet_list":
                bullets.extend(getattr(element, "items", []))
    bullets = bullets[:3]
    if bullets:
        return f"{slide.title}: " + "; ".join(bullets)
    return slide.title


def _pick_theme(role: str, tone: str) -> str:
    if tone in {"closing", "persuasive"} or role in {"summary", "closing"}:
        return "bold_dark"
    if role == "analysis":
        return "editorial"
    return "clean_light"


_ALL_VARIANTS = {
    "title_page", "content_box_list", "content_two_panel", "content_sidebar",
    "content_split_band", "content_compact", "content_card_grid", "content_steps",
    "content_highlight_split", "closing_page",
}


def _pick_variant(slide_info: dict[str, object]) -> str:
    preferred_variant = str(slide_info.get("preferred_variant") or "").strip()
    if preferred_variant in _ALL_VARIANTS:
        return preferred_variant

    role = str(slide_info.get("role", "")).strip().lower()
    key_points = [str(item) for item in slide_info.get("key_points", []) if isinstance(item, str)]
    n = len(key_points)

    if role in {"cover", "problem_intro"}:
        return "title_page"
    if role == "closing":
        return "closing_page"
    if role == "analysis":
        return "content_split_band"
    if role == "solution":
        return "content_steps"
    if role == "summary":
        return "content_compact"
    if role == "comparison":
        return "content_two_panel"
    if 2 <= n <= 5:
        return "content_card_grid"
    return "content_box_list"


def _extract_people_info(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates: list[str] = []
    patterns = [
        re.compile(r"(presented by|presenter|team|author|authors|members|by)\s*[:\-]?\s*(.+)", re.IGNORECASE),
        re.compile(r"(name|speaker|speakers)\s*[:\-]?\s*(.+)", re.IGNORECASE),
    ]

    for line in lines[:40]:
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                value = " ".join(part.strip() for part in match.groups() if part.strip())
                candidates.append(value)
                break

    if not candidates:
        short_lines = [line for line in lines[:12] if 3 <= len(line) <= 40]
        for line in short_lines:
            lowered = line.lower()
            if any(token in lowered for token in ("team", "presenter", "speaker", "author", "member", "name")):
                candidates.append(line)

    deduped: list[str] = []
    for candidate in candidates:
        normalized = candidate.strip()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped[:4]


def _normalize_slide(
    raw_slide: dict[str, object],
    slide_info: dict[str, object],
    presentation_theme: str,
) -> dict[str, object]:
    raw_slide["theme"] = presentation_theme
    raw_slide.setdefault("slide_variant", _pick_variant(slide_info))
    return raw_slide


class SlideGenerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def generate_slides(self, state: ProjectState) -> list[SlideContent]:
        if not state.outline:
            raise ValueError("Outline이 없습니다. 먼저 /generate/outline을 호출하세요.")

        presentation_goal = state.metadata.get(
            "presentation_goal",
            f"문서 '{state.title}'의 핵심 내용을 청중이 이해하기 쉽게 발표 자료로 구성한다.",
        )
        target_audience = state.metadata.get(
            "target_audience",
            "해당 문서를 처음 접하는 일반 청중",
        )
        people = _extract_people_info(state.source_document_text or state.content)

        outline_payload = {title: item.model_dump() for title, item in state.outline.items()}
        outline_ok, outline_error = validate_outline_payload(outline_payload)
        if not outline_ok:
            raise ValueError(f"{outline_error} JSON이 잘못되었습니다.")

        raw_theme = str(state.metadata.get("presentation_theme", "clean_light"))
        presentation_theme = raw_theme if raw_theme in {"clean_light", "bold_dark", "editorial"} else "clean_light"

        titles = list(state.outline.keys())
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_SLIDES)

        async def _generate_one(index: int, title: str) -> dict[str, object]:
            item = state.outline[title]
            prev_title = titles[index - 1] if index > 0 else None
            previous_slide_summary = (
                f"{prev_title}: {state.outline[prev_title].description}"
                if prev_title else ""
            )
            next_slide_summary = (
                state.outline[titles[index + 1]].description
                if index < len(titles) - 1 else ""
            )
            slide_info = item.model_dump()
            slide_info["title"] = title
            slide_info["people"] = people

            async with semaphore:
                raw_slide = await self._llm_client.generate_slide(
                    presentation_goal=presentation_goal,
                    target_audience=target_audience,
                    slide_info=slide_info,
                    content=state.content,
                    language=state.language,
                    previous_slide_summary=previous_slide_summary,
                    next_slide_summary=next_slide_summary,
                    request_label=f"slide {index + 1} project {state.project_id}: {title}",
                )
            return _normalize_slide(raw_slide, slide_info, presentation_theme)

        raw_slides: list[dict[str, object]] = list(
            await asyncio.gather(
                *[_generate_one(i, title) for i, title in enumerate(titles)]
            )
        )

        state.metadata["slides_raw"] = raw_slides
        slides_ok, slides_error = validate_slides_payload(raw_slides)
        if not slides_ok:
            raise ValueError(f"{slides_error} JSON이 잘못되었습니다.")

        slides = [SlideContent.model_validate(slide) for slide in raw_slides]
        state.metadata["people_info"] = people
        return slides
