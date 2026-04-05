from __future__ import annotations

from ..models.project_state import ProjectState
from ..schemas.generate import SlideContent, SlideEvaluation
from .llm_client import LLMClient


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
    if tone in {"closing", "persuasive"} or role == "summary":
        return "bold_dark"
    if role == "analysis":
        return "editorial"
    return "clean_light"


def _pick_variant(role: str, key_points: list[str]) -> str:
    if role == "problem_intro":
        return "title"
    if role in {"summary", "solution"}:
        return "summary"
    if len(key_points) >= 4:
        return "two_column"
    return "section"


def _normalize_slide(raw_slide: dict[str, object], slide_info: dict[str, object]) -> dict[str, object]:
    role = str(slide_info.get("role", "")).strip().lower()
    tone = str(slide_info.get("tone", "")).strip().lower()
    key_points = [str(item) for item in slide_info.get("key_points", []) if isinstance(item, str)]
    raw_slide.setdefault("theme", _pick_theme(role, tone))
    raw_slide.setdefault("slide_variant", _pick_variant(role, key_points))
    return raw_slide


class SlideGenerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def generate_slides(self, state: ProjectState) -> list[SlideContent]:
        if not state.outline:
            raise ValueError("Outline이 없습니다. 먼저 /generate/outline을 호출하세요.")

        presentation_goal = state.metadata.get(
            "presentation_goal",
            f"문서 '{state.title}'의 핵심 내용을 청중이 빠르게 이해하도록 구조화한다.",
        )
        target_audience = state.metadata.get(
            "target_audience",
            "해당 문서를 읽지 않았거나 배경지식이 많지 않을 수 있는 일반 청중",
        )

        titles = list(state.outline.keys())
        slides: list[SlideContent] = []
        evaluations: dict[str, SlideEvaluation] = {}

        for index, title in enumerate(titles):
            item = state.outline[title]
            previous_slide = slides[index - 1] if index > 0 else None
            previous_slide_summary = _summarize_slide_for_context(previous_slide)
            next_slide_goal = state.outline[titles[index + 1]].goal if index < len(titles) - 1 else ""

            slide_info = item.model_dump()
            slide_info["title"] = title

            raw_slide = await self._llm_client.generate_slide(
                presentation_goal=presentation_goal,
                target_audience=target_audience,
                slide_info=slide_info,
                content=state.content,
                language=state.language,
                previous_slide_summary=previous_slide_summary,
                next_slide_goal=next_slide_goal,
            )
            slide = SlideContent.model_validate(_normalize_slide(raw_slide, slide_info))
            slides.append(slide)

            raw_evaluation = await self._llm_client.evaluate_slide(
                slide_title=title,
                slide_info=slide_info,
                slide_output=slide.model_dump(),
                previous_slide_summary=previous_slide_summary,
                next_slide_goal=next_slide_goal,
                language=state.language,
            )
            evaluations[title] = SlideEvaluation.model_validate(raw_evaluation)

        state.metadata["slide_evaluations"] = {
            key: value.model_dump() for key, value in evaluations.items()
        }
        return slides
