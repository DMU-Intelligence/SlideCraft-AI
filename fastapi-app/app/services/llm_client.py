from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx

from ..core.config import Settings

logger = logging.getLogger(__name__)
_FASTAPI_APP_DIR = Path(__file__).resolve().parents[2]
_CANONICAL_SLIDE_VARIANTS = (
    "title_page|content_box_list|content_two_panel|content_sidebar|"
    "content_split_band|content_compact|closing_page"
)


def _load_prompt_contract(filename: str) -> str:
    return (_FASTAPI_APP_DIR / filename).read_text(encoding="utf-8").strip()


_SLOTS_PROMPT_SCHEMA = _load_prompt_contract("slots.json")
_ELEMENTS_PROMPT_SCHEMA = _load_prompt_contract("elements.json")
_OUTLINE_PROMPT_SCHEMA = _load_prompt_contract("outline.json")
_SLIDE_PAGE_PROMPT_SCHEMA = {
    "background": "#RRGGBB",
    "slots": {
        "headline": "string",
        "body": "string",
        "bullets": ["string"],
        "left_points": ["string"],
        "right_points": ["string"],
        "highlight": "string",
        "people": ["string"],
    },
    "elements": ["SlideElement"],
}
_SLIDE_RESPONSE_PROMPT_SCHEMA = json.dumps(
    {
        "title": "string",
        "theme": "clean_light|bold_dark|editorial",
        "slide_variant": _CANONICAL_SLIDE_VARIANTS,
        "pages": [_SLIDE_PAGE_PROMPT_SCHEMA],
    },
    ensure_ascii=False,
)


def _normalize_request_label(request_label: str, fallback: str) -> str:
    return request_label.strip() or fallback


def _log_llm_text(stage: str, request_label: str, text: str) -> None:
    logger.info("[LLM][%s][%s]\n%s", request_label, stage, text)


def _to_log_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


async def _call_cli_bridge(
    *,
    url_env_var: str,
    default_url: str,
    prompt: str,
    bridge_name: str,
) -> str:
    url = os.getenv(url_env_var, default_url).rstrip("/")
    full_prompt = "Return only valid JSON. No explanation, no markdown fences.\n\n" + prompt

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{url}/generate",
                json={"prompt": full_prompt},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"{bridge_name} bridge server connection failed: {url}/generate "
            f"(set {url_env_var} or start the bridge server)"
        ) from exc
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            payload = exc.response.json()
            detail_value = payload.get("detail")
            if detail_value:
                detail = f": {detail_value}"
        except Exception:
            body = (exc.response.text or "").strip()
            if body:
                detail = f": {body[:300]}"
        raise RuntimeError(
            f"{bridge_name} bridge server returned {exc.response.status_code} for "
            f"{url}/generate{detail}"
        ) from exc

    return str(data["response"])


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise RuntimeError(f"LLM did not return valid JSON. Response: {cleaned[:300]}")
    return json.loads(cleaned[start : end + 1])


def _extract_slide_bullets(slide: dict[str, Any]) -> list[str]:
    bullets: list[str] = []
    for page in slide.get("pages", []):
        slots = page.get("slots", {})
        for key in ("bullets", "left_points", "right_points"):
            value = slots.get(key, [])
            if isinstance(value, list):
                bullets.extend(str(item) for item in value)
        for element in page.get("elements", []):
            if element.get("type") == "bullet_list":
                bullets.extend(str(item) for item in element.get("items", []))
    return bullets


def _pick_slide_variant(slide_info: dict[str, Any]) -> str:
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
    key_points = slide_info.get("key_points", [])
    if role == "problem_intro":
        return "title_page"
    if role == "analysis":
        return "content_split_band"
    if role in {"summary", "solution"}:
        return "content_compact"
    if role == "comparison":
        return "content_two_panel"
    if isinstance(key_points, list) and len(key_points) >= 4:
        return "content_two_panel"
    return "content_box_list"


def _pick_theme(slide_info: dict[str, Any]) -> str:
    tone = str(slide_info.get("tone", "")).strip().lower()
    role = str(slide_info.get("role", "")).strip().lower()
    if tone in {"closing", "persuasive"} or role == "summary":
        return "bold_dark"
    if role == "analysis":
        return "editorial"
    return "clean_light"


class LLMClient(ABC):
    @abstractmethod
    async def clean_text(self, raw_text: str, language: str, request_label: str = "") -> str:
        raise NotImplementedError

    @abstractmethod
    async def generate_outline(
        self,
        title: str,
        content: str,
        language: str,
        presentation_goal: str,
        target_audience: str,
        request_label: str = "",
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def generate_slide(
        self,
        presentation_goal: str,
        target_audience: str,
        slide_info: dict[str, Any],
        content: str,
        language: str,
        previous_slide_summary: str = "",
        next_slide_goal: str = "",
        request_label: str = "",
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def generate_notes(
        self,
        slides: list[dict[str, Any]],
        outline: dict[str, Any],
        language: str,
        request_label: str = "",
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def update_outline(
        self,
        titles: list[str],
        content: str,
        language: str,
        presentation_goal: str,
        target_audience: str,
        request_label: str = "",
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def regenerate_slide(
        self,
        presentation_goal: str,
        target_audience: str,
        slide_info: dict[str, Any],
        content: str,
        language: str,
        user_request: str,
        current_slide: dict[str, Any],
        previous_slide_summary: str = "",
        next_slide_goal: str = "",
        request_label: str = "",
    ) -> dict[str, Any]:
        raise NotImplementedError


_CLEAN_TEXT_PROMPT = """
You clean extracted document text.
Return valid JSON only: {{"content": "..."}}.

Rules:
- Preserve the source meaning.
- Remove obvious PDF artifacts, broken spacing, page numbers, and duplicated noise.
- Do not add new facts.
- Keep the output in {language}.

Source text:
{raw_text}
"""

_GENERATE_OUTLINE_PROMPT = """
You design a presentation outline from a source document.
Return valid JSON only.

Context:
- Document title: {title}
- Language: {language}
- Presentation goal: {presentation_goal}
- Target audience: {target_audience}

Return:
- "title": concise presentation title
- "outline": object keyed by slide title

Outline prompt contract:
{outline_schema_json}

Constraints:
- Create slide-level entries, not section-only headings.
- Make the title specific and natural.
- Keep flow coherent for a general audience.
- Keep key_points concise and source-grounded.
- Choose a preferred_variant that fits the content density.
- Do not include unsupported topics.

Source document:
{content}
"""

_GENERATE_SLIDE_PROMPT = """
You create one presentation slide in JSON.
Return valid JSON only.

Response schema:
{slide_response_schema_json}

Slots prompt contract:
{slots_schema_json}

Elements prompt contract:
{elements_schema_json}

Presentation context:
- Goal: {presentation_goal}
- Target audience: {target_audience}
- Previous slide summary: {previous_slide_summary}
- Next slide goal: {next_slide_goal}

Current slide contract:
{slide_info_json}

Rules:
- This is a fill-in task based on the slide contract, not a free rewrite.
- Prefer elements as the primary representation.
- If you include slots, follow the slots prompt contract exactly.
- If you include elements, follow the elements prompt contract exactly.
- Use one canonical slide_variant only.
- Make the chosen slide_variant visible in the layout, not only in metadata.
- Reflect the slide goal and key_points directly.
- Use only source-backed content.
- Keep wording easy for non-experts.
- Never exceed 5 bullet items in one bullet_list or slots list.
- If the slide is an opening slide and people info exists, include people in slots.
- Keep the slide connected to the previous and next flow.
- Write in {language}.

Source document:
{content}
"""

_GENERATE_NOTES_PROMPT = """
You write presentation speaker notes from generated slides.
Return valid JSON only: {{"notes": "..."}}.

Rules:
- The notes are a speaking script that explains the slides.
- Use the actual generated slide output as the primary source.
- Do not invent a new structure unrelated to the slides.
- You may add smooth transitions, but stay tightly coupled to slide titles and bullets.
- Write one continuous script string in {language}.

Outline:
{outline_json}

Slides:
{slides_json}
"""

_UPDATE_OUTLINE_PROMPT = """
You are updating a presentation outline using fixed slide titles.
Return valid JSON only.

Use the exact titles provided. For each title, create:
an outline item that follows this prompt contract:
{outline_schema_json}

Presentation goal: {presentation_goal}
Target audience: {target_audience}
Language: {language}
Titles:
{titles}

Source document:
{content}
"""

_REGENERATE_SLIDE_PROMPT = """
You are revising an existing slide.
Return valid JSON only in the same shape as slide generation.

Response schema:
{slide_response_schema_json}

Slots prompt contract:
{slots_schema_json}

Elements prompt contract:
{elements_schema_json}

Presentation goal: {presentation_goal}
Target audience: {target_audience}
Previous slide summary: {previous_slide_summary}
Next slide goal: {next_slide_goal}
User request:
{user_request}

Slide contract:
{slide_info_json}

Current slide:
{current_slide_json}

Rules:
- Preserve the slide contract.
- Apply the user request without breaking the flow.
- Prefer elements as the primary representation.
- If you include slots, follow the slots prompt contract exactly.
- If you include elements, follow the elements prompt contract exactly.
- Do not exceed 5 bullets.
- Use only source-backed content.
- Write in {language}.

Source document:
{content}
"""

_EVALUATE_SLIDE_PROMPT = """
You evaluate one generated presentation slide.
Return valid JSON only with keys: passed, score, checklist, issues, feedback.

Language: {language}
Previous slide summary: {previous_slide_summary}
Next slide goal: {next_slide_goal}
Slide contract:
{slide_info_json}
Slide output:
{slide_output_json}
"""


class MockLLMClient(LLMClient):
    async def clean_text(self, raw_text: str, language: str, request_label: str = "") -> str:
        prompt = _CLEAN_TEXT_PROMPT.format(language=language, raw_text=raw_text[:8000])
        cleaned = re.sub(r"\s+", " ", raw_text).strip()
        label = _normalize_request_label(request_label, "clean_text")
        _log_llm_text("prompt", label, prompt)
        _log_llm_text("response", label, _to_log_text({"content": cleaned}))
        return cleaned

    async def generate_outline(
        self,
        title: str,
        content: str,
        language: str,
        presentation_goal: str,
        target_audience: str,
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _GENERATE_OUTLINE_PROMPT.format(
            title=title,
            content=content[:7000],
            language=language,
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            canonical_slide_variants=_CANONICAL_SLIDE_VARIANTS,
            outline_schema_json=_OUTLINE_PROMPT_SCHEMA,
        )
        sections = [
            ("서론", "problem_intro", "피부 관리의 중요성을 강조한다."),
            ("피부 타입 분석", "detail", "피부 타입의 분류와 특징을 설명한다."),
            ("나의 피부 타입", "detail", "자신의 피부 타입을 분석한다."),
            ("피부 타입에 따른 원인 분석", "analysis", "피부 타입에 영향을 미치는 요인을 분석한다."),
            ("피부 관리 방법 설계", "solution", "효과적인 피부 관리 방법을 제시한다."),
            ("결론", "summary", "피부 관리의 핵심 포인트를 정리한다."),
        ]
        result: dict[str, Any] = {}
        for index, (slide_title, role, goal) in enumerate(sections, start=1):
            result[slide_title] = {
                "id": f"slide_{index:02d}",
                "role": role,
                "goal": goal,
                "key_points": [goal.replace("한다.", ""), "핵심 내용 정리"],
                "tone": "informative" if role != "summary" else "closing",
                "description": f"{slide_title}에 맞는 핵심 내용을 일반 청중이 이해하기 쉽게 정리한다.",
                "page_size": 1,
                "preferred_variant": _pick_slide_variant({"role": role, "key_points": [goal]}),
            }
        response = {
            "title": str(title).strip() or "Presentation",
            "outline": result,
        }
        label = _normalize_request_label(request_label, "outline")
        _log_llm_text("prompt", label, prompt)
        _log_llm_text("response", label, _to_log_text(response))
        return response

    async def generate_slide(
        self,
        presentation_goal: str,
        target_audience: str,
        slide_info: dict[str, Any],
        content: str,
        language: str,
        previous_slide_summary: str = "",
        next_slide_goal: str = "",
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _GENERATE_SLIDE_PROMPT.format(
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            previous_slide_summary=previous_slide_summary or "(none)",
            next_slide_goal=next_slide_goal or "(none)",
            slide_info_json=json.dumps(slide_info, ensure_ascii=False),
            content=content[:5000],
            language=language,
            canonical_slide_variants=_CANONICAL_SLIDE_VARIANTS,
            slide_response_schema_json=_SLIDE_RESPONSE_PROMPT_SCHEMA,
            slots_schema_json=_SLOTS_PROMPT_SCHEMA,
            elements_schema_json=_ELEMENTS_PROMPT_SCHEMA,
        )
        display_title = str(slide_info["title"]).strip()
        bullets = [str(item).strip() for item in slide_info.get("key_points", []) if str(item).strip()][:5]
        if not bullets:
            bullets = [str(slide_info.get("goal") or slide_info.get("description") or display_title)]
        slide_variant = _pick_slide_variant(slide_info)
        theme = _pick_theme(slide_info)
        page_background = "#FFFDF8" if theme == "editorial" else "#0F172A" if theme == "bold_dark" else "#F8FAFC"
        slots: dict[str, Any] = {
            "eyebrow": str(slide_info.get("role", "")).replace("_", " ").title(),
            "headline": display_title,
            "body": str(slide_info.get("description", "")),
            "highlight": str(slide_info.get("goal", "")),
        }
        if slide_variant == "content_two_panel":
            midpoint = max(1, (len(bullets) + 1) // 2)
            slots["left_points"] = bullets[:midpoint]
            slots["right_points"] = bullets[midpoint:]
        else:
            slots["bullets"] = bullets
        page = {
            "background": page_background,
            "slots": slots,
            "elements": [
                {
                    "type": "text_box",
                    "text": display_title,
                    "x": 1.0,
                    "y": 0.5,
                    "w": 11.8,
                    "h": 1.0,
                    "font_name": "Malgun Gothic",
                    "font_size": 28,
                    "font_bold": False,
                    "font_color": "#0F172A",
                    "align": "left",
                },
                {
                    "type": "bullet_list",
                    "x": 1.0,
                    "y": 1.5,
                    "w": 11.8,
                    "h": 1.5,
                    "items": bullets,
                    "bullet_char": "-",
                    "bullet_color": "#2563EB",
                    "font_name": "Malgun Gothic",
                    "font_size": 16,
                    "font_color": "#1E293B",
                },
                {
                    "type": "text_box",
                    "text": slide_info["description"],
                    "x": 1.0,
                    "y": 3.0,
                    "w": 11.8,
                    "h": 1.0,
                    "font_name": "Malgun Gothic",
                    "font_size": 16,
                    "font_bold": False,
                    "font_color": "#0F172A",
                    "align": "left",
                },
            ],
        }
        response = {
            "title": slide_info["title"],
            "theme": theme,
            "slide_variant": slide_variant,
            "pages": [page],
        }
        label = _normalize_request_label(request_label, f"slide: {display_title}")
        _log_llm_text("prompt", label, prompt)
        _log_llm_text("response", label, _to_log_text(response))
        return response

    async def evaluate_slide(
        self,
        slide_title: str,
        slide_info: dict[str, Any],
        slide_output: dict[str, Any],
        previous_slide_summary: str,
        next_slide_goal: str,
        language: str,
    ) -> dict[str, Any]:
        bullet_count = len(_extract_slide_bullets(slide_output))
        issues: list[str] = []
        if bullet_count > 5:
            issues.append("bullet 수가 5개를 초과함")
        if not next_slide_goal and slide_info.get("role") == "summary":
            issues.append("다음 슬라이드로 이어질 흐름이 없음")
        return {
            "passed": bullet_count <= 5,
            "score": 5 if bullet_count <= 5 else 3,
            "checklist": [
                "slide_info.goal 달성 여부: 예",
                "key_points 반영 여부: 예",
                f"bullet 5개 이하 여부: {'예' if bullet_count <= 5 else '아니오'}",
                "이전 슬라이드와 중복 최소화 여부: 예",
                "비전공자도 이해 가능한 명확성: 예",
                f"다음 슬라이드로 이어질 흐름 존재 여부: {'예' if next_slide_goal or slide_info.get('role') == 'summary' else '아니오'}",
            ],
            "issues": issues,
            "feedback": "슬라이드 내용이 명확하고 목표에 부합합니다.",
        }

    async def generate_notes(
        self,
        slides: list[dict[str, Any]],
        outline: dict[str, Any],
        language: str,
        request_label: str = "",
    ) -> str:
        prompt = _GENERATE_NOTES_PROMPT.format(
            slides_json=json.dumps(slides, ensure_ascii=False)[:7000],
            outline_json=json.dumps(outline, ensure_ascii=False)[:4000],
            language=language,
        )
        lines: list[str] = []
        for slide in slides:
            bullets = _extract_slide_bullets(slide)
            if bullets:
                lines.append(f"{slide.get('title', '')}에서는 {', '.join(bullets)}를 중심으로 설명합니다.")
            else:
                lines.append(f"{slide.get('title', '')} 슬라이드를 설명합니다.")
        response = {"notes": " ".join(lines)}
        label = _normalize_request_label(request_label, "notes")
        _log_llm_text("prompt", label, prompt)
        _log_llm_text("response", label, _to_log_text(response))
        return str(response["notes"])

    async def update_outline(
        self,
        titles: list[str],
        content: str,
        language: str,
        presentation_goal: str,
        target_audience: str,
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _UPDATE_OUTLINE_PROMPT.format(
            titles="\n".join(f"- {title}" for title in titles),
            content=content[:7000],
            language=language,
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            canonical_slide_variants=_CANONICAL_SLIDE_VARIANTS,
            outline_schema_json=_OUTLINE_PROMPT_SCHEMA,
        )
        result: dict[str, Any] = {}
        for index, title in enumerate(titles, start=1):
            result[title] = {
                "id": f"slide_{index:02d}",
                "role": "detail",
                "goal": f"{title}의 핵심 내용을 전달한다.",
                "key_points": [f"{title} 핵심 포인트 1", f"{title} 핵심 포인트 2"],
                "tone": "informative",
                "description": f"{title}에 대한 설명 슬라이드",
                "page_size": 1,
                "preferred_variant": "content_box_list",
            }
        label = _normalize_request_label(request_label, "update_outline")
        _log_llm_text("prompt", label, prompt)
        _log_llm_text("response", label, _to_log_text(result))
        return result

    async def regenerate_slide(
        self,
        presentation_goal: str,
        target_audience: str,
        slide_info: dict[str, Any],
        content: str,
        language: str,
        user_request: str,
        current_slide: dict[str, Any],
        previous_slide_summary: str = "",
        next_slide_goal: str = "",
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _REGENERATE_SLIDE_PROMPT.format(
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            previous_slide_summary=previous_slide_summary or "(none)",
            next_slide_goal=next_slide_goal or "(none)",
            user_request=user_request or "(none)",
            slide_info_json=json.dumps(slide_info, ensure_ascii=False),
            current_slide_json=json.dumps(current_slide, ensure_ascii=False)[:5000],
            content=content[:5000],
            language=language,
            canonical_slide_variants=_CANONICAL_SLIDE_VARIANTS,
            slide_response_schema_json=_SLIDE_RESPONSE_PROMPT_SCHEMA,
            slots_schema_json=_SLOTS_PROMPT_SCHEMA,
            elements_schema_json=_ELEMENTS_PROMPT_SCHEMA,
        )
        if current_slide:
            response = current_slide
        else:
            response = await self.generate_slide(
                presentation_goal=presentation_goal,
                target_audience=target_audience,
                slide_info=slide_info,
                content=content,
                language=language,
                previous_slide_summary=previous_slide_summary,
                next_slide_goal=next_slide_goal,
                request_label=request_label,
            )
        label = _normalize_request_label(request_label, f"regenerate slide: {slide_info.get('title', '')}")
        _log_llm_text("prompt", label, prompt)
        _log_llm_text("response", label, _to_log_text(response))
        return response


class OpenAICompatibleLLMClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def _call_with_logging(self, prompt: str, request_label: str, fallback_label: str) -> str:
        label = _normalize_request_label(request_label, fallback_label)
        _log_llm_text("prompt", label, prompt)
        response = await self._call(prompt)
        _log_llm_text("response", label, response)
        return response

    async def _call(self, prompt: str) -> str:
        if not self._settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        url = self._settings.openai_base_url.rstrip("/") + "/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self._settings.openai_api_key}"}
        payload: dict[str, Any] = {
            "model": self._settings.openai_model,
            "messages": [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    async def clean_text(self, raw_text: str, language: str, request_label: str = "") -> str:
        prompt = _CLEAN_TEXT_PROMPT.format(language=language, raw_text=raw_text[:8000])
        result = _parse_json(await self._call_with_logging(prompt, request_label, "clean_text"))
        return str(result.get("content", raw_text))

    async def generate_outline(
        self,
        title: str,
        content: str,
        language: str,
        presentation_goal: str,
        target_audience: str,
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _GENERATE_OUTLINE_PROMPT.format(
            title=title,
            content=content[:7000],
            language=language,
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            canonical_slide_variants=_CANONICAL_SLIDE_VARIANTS,
            outline_schema_json=_OUTLINE_PROMPT_SCHEMA,
        )
        return _parse_json(await self._call_with_logging(prompt, request_label, "outline"))

    async def generate_slide(
        self,
        presentation_goal: str,
        target_audience: str,
        slide_info: dict[str, Any],
        content: str,
        language: str,
        previous_slide_summary: str = "",
        next_slide_goal: str = "",
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _GENERATE_SLIDE_PROMPT.format(
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            previous_slide_summary=previous_slide_summary or "(none)",
            next_slide_goal=next_slide_goal or "(none)",
            slide_info_json=json.dumps(slide_info, ensure_ascii=False),
            content=content[:5000],
            language=language,
            canonical_slide_variants=_CANONICAL_SLIDE_VARIANTS,
            slide_response_schema_json=_SLIDE_RESPONSE_PROMPT_SCHEMA,
            slots_schema_json=_SLOTS_PROMPT_SCHEMA,
            elements_schema_json=_ELEMENTS_PROMPT_SCHEMA,
        )
        return _parse_json(await self._call_with_logging(prompt, request_label, f"slide: {slide_info.get('title', '')}"))

    async def evaluate_slide(
        self,
        slide_title: str,
        slide_info: dict[str, Any],
        slide_output: dict[str, Any],
        previous_slide_summary: str,
        next_slide_goal: str,
        language: str,
    ) -> dict[str, Any]:
        prompt = _EVALUATE_SLIDE_PROMPT.format(
            language=language,
            previous_slide_summary=previous_slide_summary or "(none)",
            next_slide_goal=next_slide_goal or "(none)",
            slide_info_json=json.dumps(slide_info, ensure_ascii=False),
            slide_output_json=json.dumps(slide_output, ensure_ascii=False),
        )
        return _parse_json(await self._call_with_logging(prompt, f"evaluate slide: {slide_title}", f"evaluate slide: {slide_title}"))

    async def generate_notes(
        self,
        slides: list[dict[str, Any]],
        outline: dict[str, Any],
        language: str,
        request_label: str = "",
    ) -> str:
        prompt = _GENERATE_NOTES_PROMPT.format(
            slides_json=json.dumps(slides, ensure_ascii=False)[:7000],
            outline_json=json.dumps(outline, ensure_ascii=False)[:4000],
            language=language,
        )
        result = _parse_json(await self._call_with_logging(prompt, request_label, "notes"))
        return str(result.get("notes", ""))

    async def update_outline(
        self,
        titles: list[str],
        content: str,
        language: str,
        presentation_goal: str,
        target_audience: str,
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _UPDATE_OUTLINE_PROMPT.format(
            titles="\n".join(f"- {title}" for title in titles),
            content=content[:7000],
            language=language,
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            canonical_slide_variants=_CANONICAL_SLIDE_VARIANTS,
            outline_schema_json=_OUTLINE_PROMPT_SCHEMA,
        )
        return _parse_json(await self._call_with_logging(prompt, request_label, "update_outline"))

    async def regenerate_slide(
        self,
        presentation_goal: str,
        target_audience: str,
        slide_info: dict[str, Any],
        content: str,
        language: str,
        user_request: str,
        current_slide: dict[str, Any],
        previous_slide_summary: str = "",
        next_slide_goal: str = "",
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _REGENERATE_SLIDE_PROMPT.format(
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            previous_slide_summary=previous_slide_summary or "(none)",
            next_slide_goal=next_slide_goal or "(none)",
            user_request=user_request or "(none)",
            slide_info_json=json.dumps(slide_info, ensure_ascii=False),
            current_slide_json=json.dumps(current_slide, ensure_ascii=False)[:5000],
            content=content[:5000],
            language=language,
            canonical_slide_variants=_CANONICAL_SLIDE_VARIANTS,
            slide_response_schema_json=_SLIDE_RESPONSE_PROMPT_SCHEMA,
            slots_schema_json=_SLOTS_PROMPT_SCHEMA,
            elements_schema_json=_ELEMENTS_PROMPT_SCHEMA,
        )
        return _parse_json(await self._call_with_logging(prompt, request_label, f"regenerate slide: {slide_info.get('title', '')}"))


class GeminiLLMClient(OpenAICompatibleLLMClient):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                import google.generativeai as genai  # type: ignore[import]
            except ImportError as exc:
                raise RuntimeError("google-generativeai package is not installed.") from exc
            if not self._settings.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY is not set.")
            genai.configure(api_key=self._settings.gemini_api_key)
            self._model = genai.GenerativeModel(
                model_name=self._settings.gemini_model,
                generation_config={"temperature": 0.2, "response_mime_type": "application/json"},
            )
        return self._model

    async def _call(self, prompt: str) -> str:
        import asyncio

        model = self._get_model()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
        return response.text.strip()


class GeminiCLIClient(OpenAICompatibleLLMClient):
    """
    gemini-cli-server.py (CLI 브릿지 서버)에 HTTP로 프롬프트를 전달하여
    gemini CLI 응답을 받습니다.

    환경 변수:
        GEMINI_CLI_SERVER_URL: 브릿지 서버 주소 (기본값: http://localhost:5001)
    """

    async def _call(self, prompt: str) -> str:
        return await _call_cli_bridge(
            url_env_var="GEMINI_CLI_SERVER_URL",
            default_url="http://localhost:5001",
            prompt=prompt,
            bridge_name="Gemini CLI",
        )


class GptCLIClient(OpenAICompatibleLLMClient):
    """
    gemini-cli-server.py (CLI 브릿지 서버)에 HTTP로 프롬프트를 전달하여
    GPT CLI 응답을 받습니다.

    환경 변수:
        GPT_CLI_SERVER_URL: 브릿지 서버 주소 (기본값: http://localhost:5001)
    """

    async def _call(self, prompt: str) -> str:
        return await _call_cli_bridge(
            url_env_var="GPT_CLI_SERVER_URL",
            default_url="http://localhost:5001",
            prompt=prompt,
            bridge_name="GPT CLI",
        )


def create_llm_client(settings: Settings) -> LLMClient:
    mode = settings.llm_mode.lower().strip()

    if mode in ("mock", "mock-cli"):
        return MockLLMClient()
    if mode == "openai":
        return OpenAICompatibleLLMClient(settings)
    if mode == "gemini":
        return GeminiLLMClient(settings)
    if mode == "gemini-cli":
        return GeminiCLIClient(settings)
    if mode in ("gpt-cli", "openai-cli"):
        return GptCLIClient(settings)
    raise ValueError(f"Unsupported LLM_MODE: {settings.llm_mode}")

