from __future__ import annotations

from ..models.project_state import ProjectState
from ..schemas.generate import OutlineItem, SlideContent
from .llm_client import LLMClient


def _slide_summary(slides: list[SlideContent], index: int) -> str:
    if index < 0 or index >= len(slides):
        return ""
    slide = slides[index]
    bullets: list[str] = []
    for page in slide.pages:
        for key in ("bullets", "left_points", "right_points"):
            slot_value = page.slots.get(key, [])
            if isinstance(slot_value, list):
                bullets.extend(str(item) for item in slot_value)
        for element in page.elements:
            if getattr(element, "type", "") == "bullet_list":
                bullets.extend(getattr(element, "items", []))
    if bullets:
        return f"{slide.title}: " + "; ".join(bullets[:3])
    return slide.title


def _pick_theme(role: str, tone: str) -> str:
    if tone in {"closing", "persuasive"} or role == "summary":
        return "bold_dark"
    if role == "analysis":
        return "editorial"
    return "clean_light"


def _pick_variant(role: str, key_points: list[str]) -> str:
    if role == "problem_intro":
        return "title_page"
    if role == "analysis":
        return "content_split_band"
    if role in {"summary", "solution"}:
        return "content_compact"
    if role == "comparison":
        return "content_two_panel"
    if len(key_points) >= 4:
        return "content_two_panel"
    return "content_box_list"


def _normalize_slide(raw_slide: dict[str, object], slide_info: dict[str, object]) -> dict[str, object]:
    role = str(slide_info.get("role", "")).strip().lower()
    tone = str(slide_info.get("tone", "")).strip().lower()
    key_points = [str(item) for item in slide_info.get("key_points", []) if isinstance(item, str)]
    raw_slide.setdefault("theme", _pick_theme(role, tone))
    raw_slide.setdefault("slide_variant", _pick_variant(role, key_points))
    return raw_slide


class RegenerationService:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def regenerate_slide(
        self,
        state: ProjectState,
        slide_title: str,
        user_request: str = "",
    ) -> SlideContent:
        if slide_title not in state.outline:
            raise ValueError(f"'{slide_title}' 슬라이드가 outline에 없습니다.")

        item = state.outline[slide_title]
        titles = list(state.outline.keys())
        idx = titles.index(slide_title)
        existing = next((slide for slide in state.slides if slide.title == slide_title), None)
        current_slide = existing.model_dump() if existing else {}

        presentation_goal = state.metadata.get(
            "presentation_goal",
            f"문서 '{state.title}'의 핵심 내용을 청중이 빠르게 이해하도록 구조화한다.",
        )
        target_audience = state.metadata.get(
            "target_audience",
            "해당 문서를 읽지 않았거나 배경지식이 많지 않을 수 있는 일반 청중",
        )
        previous_slide_summary = _slide_summary(state.slides, idx - 1)
        next_slide_summary = state.outline[titles[idx + 1]].description if idx < len(titles) - 1 else ""
        slide_info = item.model_dump()
        slide_info["title"] = slide_title

        if user_request:
            raw = await self._llm_client.regenerate_slide(
                presentation_goal=presentation_goal,
                target_audience=target_audience,
                slide_info=slide_info,
                content=state.content,
                language=state.language,
                user_request=user_request,
                current_slide=current_slide,
                previous_slide_summary=previous_slide_summary,
                next_slide_summary=next_slide_summary,
                request_label=f"regenerate slide {idx + 1} project {state.project_id}: {slide_title}",
            )
        else:
            raw = await self._llm_client.generate_slide(
                presentation_goal=presentation_goal,
                target_audience=target_audience,
                slide_info=slide_info,
                content=state.content,
                language=state.language,
                previous_slide_summary=previous_slide_summary,
                next_slide_summary=next_slide_summary,
                request_label=f"slide {idx + 1} project {state.project_id}: {slide_title}",
            )

        updated = SlideContent.model_validate(_normalize_slide(raw, slide_info))

        for index, slide in enumerate(state.slides):
            if slide.title == slide_title:
                state.slides[index] = updated
                break
        else:
            state.slides.append(updated)

        state.touch()
        return updated

    async def regenerate_notes(self, state: ProjectState) -> str:
        if not state.slides:
            raise ValueError("슬라이드가 없습니다.")

        notes = await self._llm_client.generate_notes(
            slides=[slide.model_dump() for slide in state.slides],
            outline={title: item.model_dump() for title, item in state.outline.items()},
            language=state.language,
        )
        state.notes = notes
        state.touch()
        return notes

    async def update_outline(
        self, state: ProjectState, titles: list[str]
    ) -> dict[str, OutlineItem]:
        presentation_goal = state.metadata.get(
            "presentation_goal",
            f"문서 '{state.title}'의 핵심 내용을 청중이 빠르게 이해하도록 구조화한다.",
        )
        target_audience = state.metadata.get(
            "target_audience",
            "해당 문서를 읽지 않았거나 배경지식이 많지 않을 수 있는 일반 청중",
        )
        raw = await self._llm_client.update_outline(
            titles=titles,
            content=state.content,
            language=state.language,
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            request_label=f"update_outline project {state.project_id}",
        )
        outline: dict[str, OutlineItem] = {}
        for title, item in raw.items():
            outline_item = OutlineItem.model_validate(item)
            if not outline_item.preferred_variant:
                outline_item.preferred_variant = _pick_variant(
                    outline_item.role,
                    outline_item.key_points,
                )
            outline[title] = outline_item
        state.outline = outline
        state.touch()
        return outline
