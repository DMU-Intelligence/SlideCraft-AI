from __future__ import annotations

import re

from ..models.project_state import ProjectState
from ..schemas.generate import PageLayout, SlideContent
from .json_validation import validate_outline_payload, validate_slides_payload
from .llm_client import LLMClient
from .template_store import load_template, sanitize_template_name


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


def _pick_variant(slide_info: dict[str, object]) -> str:
    preferred_variant = str(slide_info.get("preferred_variant") or "").strip()
    if preferred_variant in {
        "title_page",
        "content_box_list",
        "content_two_panel",
        "content_sidebar",
        "content_split_band",
        "content_compact",
        "closing_page",
    }:
        return preferred_variant

    role = str(slide_info.get("role", "")).strip().lower()
    key_points = [str(item) for item in slide_info.get("key_points", []) if isinstance(item, str)]
    if role == "problem_intro":
        return "title_page"
    if role == "analysis":
        return "content_split_band"
    if role in {"summary", "solution"}:
        return "content_compact"
    if role == "comparison" or len(key_points) >= 4:
        return "content_two_panel"
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


def _build_title_slide(title: str, people: list[str]) -> dict[str, object]:
    return SlideContent(
        title=title,
        theme="clean_light",
        slide_variant="title_page",
        pages=[
            PageLayout(
                background="#F7F8FC",
                elements=[
                    {
                        "type": "shape",
                        "x": 0.7,
                        "y": 0.7,
                        "w": 0.18,
                        "h": 5.9,
                        "fill_color": "#2563EB",
                    },
                    {
                        "type": "text_box",
                        "text": "Presentation",
                        "x": 1.1,
                        "y": 1.0,
                        "w": 3.4,
                        "h": 0.35,
                        "font_size": 13,
                        "font_bold": True,
                        "font_color": "#2563EB",
                        "align": "left",
                    },
                    {
                        "type": "text_box",
                        "text": title,
                        "x": 1.1,
                        "y": 1.55,
                        "w": 8.8,
                        "h": 1.45,
                        "font_size": 33,
                        "font_bold": True,
                        "font_color": "#0F172A",
                        "align": "left",
                    },
                    {
                        "type": "text_box",
                        "text": "\n".join(people),
                        "x": 9.2,
                        "y": 5.8,
                        "w": 3.0,
                        "h": 0.65,
                        "font_size": 10,
                        "font_color": "#475569",
                        "align": "right",
                    },
                ],
            )
        ],
    ).model_dump()


def _build_closing_slide(title: str, theme: str, people: list[str]) -> dict[str, object]:
    palette = {
        "clean_light": {"bg": "#F7F8FC", "panel": "#FFFFFF", "accent": "#2563EB", "text": "#0F172A", "muted": "#475569"},
        "bold_dark": {"bg": "#0F172A", "panel": "#162235", "accent": "#7AA2FF", "text": "#F8FAFC", "muted": "#CBD5E1"},
        "editorial": {"bg": "#FFFDF8", "panel": "#F7F1E8", "accent": "#B45309", "text": "#292524", "muted": "#57534E"},
    }.get(theme, {"bg": "#F7F8FC", "panel": "#FFFFFF", "accent": "#2563EB", "text": "#0F172A", "muted": "#475569"})
    return SlideContent(
        title=title,
        theme=theme,
        slide_variant="closing_page",
        pages=[
            PageLayout(
                background=str(palette["bg"]),
                elements=[
                    {
                        "type": "shape",
                        "x": 0.9,
                        "y": 1.0,
                        "w": 11.5,
                        "h": 5.2,
                        "fill_color": str(palette["panel"]),
                    },
                    {
                        "type": "shape",
                        "x": 0.9,
                        "y": 1.0,
                        "w": 11.5,
                        "h": 0.2,
                        "fill_color": str(palette["accent"]),
                    },
                    {
                        "type": "text_box",
                        "text": title,
                        "x": 1.35,
                        "y": 2.0,
                        "w": 10.4,
                        "h": 0.9,
                        "font_size": 38,
                        "font_bold": True,
                        "font_color": str(palette["text"]),
                        "align": "center",
                    },
                    {
                        "type": "text_box",
                        "text": "발표를 들어주셔서 감사합니다.",
                        "x": 2.0,
                        "y": 3.15,
                        "w": 9.1,
                        "h": 0.5,
                        "font_size": 16,
                        "font_color": str(palette["muted"]),
                        "align": "center",
                    },
                    {
                        "type": "text_box",
                        "text": "\n".join(people),
                        "x": 2.2,
                        "y": 4.2,
                        "w": 8.8,
                        "h": 1.2,
                        "font_size": 15,
                        "font_color": str(palette["muted"]),
                        "align": "center",
                    },
                ],
            )
        ],
    ).model_dump()


def _normalize_slide(raw_slide: dict[str, object], slide_info: dict[str, object]) -> dict[str, object]:
    role = str(slide_info.get("role", "")).strip().lower()
    tone = str(slide_info.get("tone", "")).strip().lower()
    raw_slide.setdefault("theme", _pick_theme(role, tone))
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

        titles = list(state.outline.keys())
        raw_slides: list[dict[str, object]] = [_build_title_slide(state.title, people)]

        for index, title in enumerate(titles):
            item = state.outline[title]
            previous_slide = SlideContent.model_validate(raw_slides[-1]) if raw_slides else None
            previous_slide_summary = _summarize_slide_for_context(previous_slide)
            next_slide_summary = state.outline[titles[index + 1]].description if index < len(titles) - 1 else ""

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
                next_slide_summary=next_slide_summary,
                request_label=f"slide {index + 1} project {state.project_id}: {title}",
            )
            raw_slides.append(_normalize_slide(raw_slide, slide_info))

        closing_theme = str(raw_slides[-1].get("theme", "clean_light")) if raw_slides else "clean_light"
        raw_slides.append(_build_closing_slide("감사합니다", closing_theme, people))

        state.metadata["slides_raw"] = raw_slides
        slides_ok, slides_error = validate_slides_payload(raw_slides)
        if not slides_ok:
            raise ValueError(f"{slides_error} JSON이 잘못되었습니다.")

        slides = [SlideContent.model_validate(slide) for slide in raw_slides]
        state.metadata["people_info"] = people
        return slides

    async def add_just_template(
        self,
        state: ProjectState,
        slides: list[SlideContent],
        template_name: str | None,
    ) -> list[SlideContent]:
        if template_name is None or not template_name.strip():
            return slides

        template_pages = load_template(sanitize_template_name(template_name))
        if not template_pages:
            raise ValueError("템플릿에 콘텐츠 페이지가 없습니다.")

        raw_slides = [slide.model_dump() for slide in slides]

        for index in range(1, len(raw_slides) - 1):
            slide_title = str(raw_slides[index].get("title", ""))
            raw_slides[index] = await self._llm_client.apply_template(
                generated_slide=raw_slides[index],
                template_pages=template_pages,
                language=state.language,
                request_label=f"apply_template slide {index} project {state.project_id}: {slide_title}",
            )

        slides_ok, slides_error = validate_slides_payload(raw_slides)
        if not slides_ok:
            raise ValueError(f"{slides_error} JSON이 잘못되었습니다.")

        return [SlideContent.model_validate(slide) for slide in raw_slides]
