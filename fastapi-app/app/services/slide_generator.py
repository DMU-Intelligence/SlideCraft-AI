from __future__ import annotations

import re

from ..models.project_state import ProjectState
from ..schemas.generate import PageLayout, SlideContent, SlideEvaluation
from .llm_client import LLMClient

_CONTENT_VARIANTS = [
    "content_box_list",
    "content_two_panel",
    "content_sidebar",
    "content_split_band",
    "content_compact",
]


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


def _pick_variant(index: int) -> str:
    return _CONTENT_VARIANTS[index % len(_CONTENT_VARIANTS)]


def _extract_people_info(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates: list[str] = []
    patterns = [
        re.compile(r"(발표자|작성자|팀원|팀명|조원|소속|이름)\s*[:：]\s*(.+)", re.IGNORECASE),
        re.compile(r"(presented by|presenter|team|author|authors|members|by)\s*[:：]?\s*(.+)", re.IGNORECASE),
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
            if any(token in line.lower() for token in ("대학교", "학과", "team", "presenter", "발표", "작성")):
                candidates.append(line)

    deduped: list[str] = []
    for candidate in candidates:
        normalized = candidate.strip()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped[:4]


def _ensure_slot_lists(page: PageLayout, slide_title: str) -> None:
    slots = page.slots
    slots.setdefault("headline", slide_title)
    bullets = slots.get("bullets")
    left_points = slots.get("left_points")
    right_points = slots.get("right_points")

    if not isinstance(bullets, list):
        bullets = []
    if not isinstance(left_points, list):
        left_points = []
    if not isinstance(right_points, list):
        right_points = []

    if not bullets and (left_points or right_points):
        slots["bullets"] = [*left_points, *right_points]
    elif bullets and not (left_points or right_points):
        midpoint = max(1, (len(bullets) + 1) // 2)
        slots["left_points"] = bullets[:midpoint]
        slots["right_points"] = bullets[midpoint:]
    else:
        slots["left_points"] = left_points
        slots["right_points"] = right_points
        slots["bullets"] = bullets


def _apply_title_page(slide: SlideContent, people: list[str]) -> SlideContent:
    if not slide.pages:
        slide.pages = [PageLayout()]
    page = slide.pages[0]
    _ensure_slot_lists(page, slide.title)
    page.slots["eyebrow"] = "Presentation"
    page.slots["headline"] = slide.title
    page.slots["people"] = people
    page.slots["highlight"] = ""
    slide.slide_variant = "title_page"
    return slide


def _build_title_slide(title: str, people: list[str]) -> SlideContent:
    slide = SlideContent(
        title=title,
        theme="clean_light",
        slide_variant="title_page",
        pages=[
            PageLayout(
                background="",
                slots={
                    "eyebrow": "Presentation",
                    "headline": title,
                    "body": "",
                    "people": people,
                    "highlight": "",
                },
            )
        ],
    )
    return _apply_title_page(slide, people)


def _apply_content_variant(slide: SlideContent, variant: str) -> SlideContent:
    slide.slide_variant = variant
    for page in slide.pages:
        _ensure_slot_lists(page, slide.title)
        page.slots.setdefault("title_box_label", slide.title)
    return slide


def _build_closing_slide(title: str, theme: str, people: list[str]) -> SlideContent:
    return SlideContent(
        title=title,
        theme=theme,
        slide_variant="closing_page",
        pages=[
            PageLayout(
                background="",
                slots={
                    "headline": title,
                    "body": "발표를 들어주셔서 감사합니다.",
                    "people": people,
                },
            )
        ],
    )


def _normalize_slide(raw_slide: dict[str, object], slide_info: dict[str, object], *, index: int) -> dict[str, object]:
    role = str(slide_info.get("role", "")).strip().lower()
    tone = str(slide_info.get("tone", "")).strip().lower()
    raw_slide.setdefault("theme", _pick_theme(role, tone))
    raw_slide["slide_variant"] = _pick_variant(index)
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
            "해당 문서를 처음 접하는 일반 청중",
        )
        people = _extract_people_info(state.source_document_text or state.content)

        titles = list(state.outline.keys())
        slides: list[SlideContent] = [_build_title_slide(state.title, people)]
        evaluations: dict[str, SlideEvaluation] = {}

        for index, title in enumerate(titles):
            item = state.outline[title]
            previous_slide_summary = _summarize_slide_for_context(slides[-1] if slides else None)
            next_slide_goal = state.outline[titles[index + 1]].goal if index < len(titles) - 1 else ""

            slide_info = item.model_dump()
            slide_info["title"] = title
            slide_info["people"] = people

            raw_slide = await self._llm_client.generate_slide(
                presentation_goal=presentation_goal,
                target_audience=target_audience,
                slide_info=slide_info,
                content=state.content,
                language=state.language,
                previous_slide_summary=previous_slide_summary,
                next_slide_goal=next_slide_goal,
            )
            slide = SlideContent.model_validate(_normalize_slide(raw_slide, slide_info, index=index))
            slide = _apply_content_variant(slide, _pick_variant(index))
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

        closing_theme = slides[-1].theme if slides else "clean_light"
        slides.append(_build_closing_slide("감사합니다", closing_theme, people))

        state.metadata["slide_evaluations"] = {
            key: value.model_dump() for key, value in evaluations.items()
        }
        state.metadata["people_info"] = people
        return slides
