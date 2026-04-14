from __future__ import annotations

import asyncio
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
    "content_split_band|content_compact|content_card_grid|content_steps|"
    "content_highlight_split|closing_page"
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


def _bridge_retry_attempts() -> int:
    try:
        return max(1, int(os.getenv("CLI_BRIDGE_MAX_ATTEMPTS", "6")))
    except ValueError:
        return 6


def _bridge_retry_delay_seconds() -> float:
    try:
        return max(0.25, float(os.getenv("CLI_BRIDGE_RETRY_DELAY_SECONDS", "2.0")))
    except ValueError:
        return 2.0


def _extract_bridge_error(response: httpx.Response) -> tuple[str, dict[str, Any] | None]:
    payload: dict[str, Any] | None = None
    detail = ""
    try:
        parsed = response.json()
        if isinstance(parsed, dict):
            payload = parsed
            detail_value = parsed.get("detail")
            if detail_value:
                detail = f": {detail_value}"
            elif parsed:
                detail = f": {json.dumps(parsed, ensure_ascii=False)[:300]}"
    except Exception:
        body = (response.text or "").strip()
        if body:
            detail = f": {body[:300]}"
    return detail, payload


async def _call_cli_bridge(
    *,
    url_env_var: str,
    default_url: str,
    prompt: str,
    bridge_name: str,
) -> str:
    url = os.getenv(url_env_var, default_url).rstrip("/")
    full_prompt = "Return only valid JSON. No explanation, no markdown fences.\n\n" + prompt
    max_attempts = _bridge_retry_attempts()
    retry_delay = _bridge_retry_delay_seconds()

    async with httpx.AsyncClient(timeout=300) as client:
        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.post(
                    f"{url}/generate",
                    json={"prompt": full_prompt},
                )
            except httpx.ConnectError as exc:
                if attempt < max_attempts:
                    logger.warning(
                        "%s bridge connection failed on attempt %s/%s; retrying in %.2fs",
                        bridge_name,
                        attempt,
                        max_attempts,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)
                    continue
                raise RuntimeError(
                    f"{bridge_name} bridge server connection failed: {url}/generate "
                    f"(set {url_env_var} or start the bridge server)"
                ) from exc

            if response.is_success:
                data = response.json()
                return str(data["response"])

            detail, payload = _extract_bridge_error(response)
            will_retry = bool(payload.get("willRetry")) if isinstance(payload, dict) else False
            retryable_status = response.status_code in {502, 503, 504}
            if retryable_status and attempt < max_attempts and (will_retry or response.status_code == 502):
                logger.warning(
                    "%s bridge returned %s on attempt %s/%s; retrying in %.2fs%s",
                    bridge_name,
                    response.status_code,
                    attempt,
                    max_attempts,
                    retry_delay,
                    detail,
                )
                await asyncio.sleep(retry_delay)
                continue

            raise RuntimeError(
                f"{bridge_name} bridge server returned {response.status_code} for "
                f"{url}/generate{detail}"
            )

    raise RuntimeError(f"{bridge_name} bridge request exhausted retries for {url}/generate")


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


def _format_slide_note_source(slide: dict[str, Any]) -> str:
    title = str(slide.get("title") or "Untitled Slide").strip() or "Untitled Slide"
    lines = [f"# {title}"]

    for page in slide.get("pages", []):
        slots = page.get("slots", {})
        for key in ("headline", "body", "highlight"):
            value = slots.get(key)
            if isinstance(value, str) and value.strip():
                lines.append(value.strip())

        for key in ("bullets", "left_points", "right_points", "people"):
            value = slots.get(key, [])
            if isinstance(value, list):
                for item in value:
                    text = str(item).strip()
                    if text:
                        lines.append(f"- {text}")

        for element in page.get("elements", []):
            element_type = str(element.get("type", "")).strip()
            if element_type in {"text_box", "quote_box"}:
                text = str(element.get("text", "")).strip()
                if text:
                    lines.append(text)
            elif element_type == "bullet_list":
                for item in element.get("items", []):
                    text = str(item).strip()
                    if text:
                        lines.append(f"- {text}")
            elif element_type == "image_placeholder":
                description = str(element.get("description", "")).strip()
                if description:
                    lines.append(f"- 시각 자료: {description}")

    if len(lines) == 1:
        bullets = _extract_slide_bullets(slide)
        if bullets:
            lines.extend(f"- {bullet}" for bullet in bullets)
        else:
            lines.append("- 슬라이드 내용을 바탕으로 발표 노트를 작성")

    return "\n".join(lines)


def _format_slides_for_notes_prompt(slides: list[dict[str, Any]]) -> str:
    return "\n\n".join(_format_slide_note_source(slide) for slide in slides)


_ALL_VARIANTS = {
    "title_page", "content_box_list", "content_two_panel", "content_sidebar",
    "content_split_band", "content_compact", "content_card_grid", "content_steps",
    "content_highlight_split", "closing_page",
}


def _pick_slide_variant(slide_info: dict[str, Any]) -> str:
    preferred_variant = str(slide_info.get("preferred_variant") or "").strip()
    if preferred_variant in _ALL_VARIANTS:
        return preferred_variant

    role = str(slide_info.get("role", "")).strip().lower()
    key_points = slide_info.get("key_points", [])
    n = len(key_points) if isinstance(key_points, list) else 0

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
        next_slide_summary: str = "",
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
        next_slide_summary: str = "",
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

Return at the top level:
- "title": concise presentation title
- "theme": one of "clean_light" | "bold_dark" | "editorial"
  All three themes use cool color palettes only.
  - "clean_light": professional, educational, or general-purpose content (light blue palette)
  - "bold_dark": high-impact, persuasive, or executive presentations (deep navy palette)
  - "editorial": academic, research, or technical deep-dives (indigo/slate palette)
- "outline": object keyed by slide title

Outline prompt contract:
{outline_schema_json}

Structure rules (mandatory):
- The outline MUST start with a cover slide: role="cover", tone="hook", preferred_variant="title_page".
- The outline MUST end with a closing slide: role="closing", tone="closing", preferred_variant="closing_page".
- All slides between cover and closing are content slides.
- Total slides including cover and closing: minimum 4, maximum 10.

Content constraints:
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

Elements prompt contract (includes variant_coordinate_templates and layout_grid):
{elements_schema_json}

Presentation context:
- Goal: {presentation_goal}
- Target audience: {target_audience}
- Previous slide summary: {previous_slide_summary}
- Next slide summary: {next_slide_summary}

Current slide contract:
{slide_info_json}

Rules:
- This is a fill-in task based on the slide contract, not a free rewrite.
- ALWAYS use elements as the primary representation. Do not use slots alone.
- Start from the variant_coordinate_templates entry that matches the chosen slide_variant. Use those x, y, w, h values as your baseline and adjust only when content length requires it.

LAYOUT DISCIPLINE — every generated page must satisfy ALL of the following:
1. Slide title text_box: y in [0.45, 0.95], h=0.55, x=0.75, font_size >= 22, font_bold=true.
2. No body element (bullet_list, shape, non-title text_box) may have y < 1.1.
3. All elements must be within safe_zone: x >= 0.75, x+w <= 12.58, y >= 0.45, y+h <= 7.1.
4. Text fit: every text_box must satisfy h >= font_size * line_count * 0.028 + 0.15. Estimate line_count by dividing character count by (w * 7) rounded up.
5. Bullet list fit: h >= items.length * 0.50. Truncate item text to 55 chars if needed.
6. Shape layering: shapes that act as panel backgrounds must appear BEFORE the text_box or bullet_list elements that sit on top of them in the elements array.
7. Left alignment: all left-edge elements share x=0.75 or x=1.05. Do not use arbitrary x values that break the column grid.
8. Two-column layouts: left column x=0.75 w=5.77, right column x=6.82 w=5.76. Maintain the 0.30 gap.

CONTENT RULES:
- Use one canonical slide_variant only. Reflect it in both metadata and the actual layout.
- Reflect the slide goal and key_points directly.
- Use only source-backed content.
- Keep wording easy for non-experts.
- Never exceed 5 bullet items in one bullet_list.
- Each bullet item: max 55 characters. Truncate if the source text is longer.
- Headline (title): max 45 characters.
- If the slide role is "cover" and people info exists, place people in a text_box at the bottom right.
- Do NOT include content from the previous or next slide in this slide's body.

WRITING STYLE — strictly enforced:
- Text must be readable and natural — not over-compressed. Write complete, informative phrases.
- NEVER end any text with formal polite endings: ~입니다, ~합니다, ~됩니다, ~있습니다, ~했습니다.
- Instead, use plain-form endings or noun-terminated phrases:
    OK: "피부 타입에 따라 관리 방법이 달라진다"
    OK: "수분 유지와 장벽 보호가 핵심"
    OK: "세 가지 원인으로 나눌 수 있다"
    NOT OK: "수분을 유지해야 합니다"
    NOT OK: "관리 방법이 달라집니다"
- Headlines: 10–40 chars, specific and descriptive, not a generic label.
- Bullets: 20–55 chars each, informative enough to stand alone without context.
- Body text: 1 sentence, plain-form or noun-terminated, max 90 chars.
- Do NOT use "표지", "마무리", "목차" as eyebrow or headline text.

BULLET CHARACTER — vary the bullet_char to match the slide tone:
- "•" for neutral informative content (default)
- "▸" for step-by-step or sequential points
- "◆" for key findings or conclusions
- "–" for comparisons or contrasts
- "›" for sub-points or supporting details
Use one character consistently within a single bullet_list.

IMAGE PLACEHOLDER — add an image_placeholder element when the content would benefit from a visual:
- Use it for diagrams, process flows, comparison charts, photographs, or data visualizations.
- Place it where the image would naturally appear in the layout (e.g. right half of a two-panel slide).
- Set description to a concise instruction for the user (e.g. "조직도 이미지", "데이터 비교 그래프").
- Do not add a placeholder just to fill space — only use it when a visual genuinely aids understanding.
- image_placeholder counts toward the layout but does not contain text content.

- Write in {language}.

Source document:
{content}
"""

_GENERATE_NOTES_PROMPT = """
You write presentation speaker notes from generated slides.
Return valid JSON only: {{"notes": "..."}}.

Rules:
- The notes are a speaking script that explains the slides.
- Write in a natural, presentation-like speaking tone.
- Use the actual generated slide output as the primary source.
- Do not invent a new structure unrelated to the slides.
- You may add smooth transitions, but stay tightly coupled to slide titles and bullets.
- Split the notes by slide.
- Start each slide section with exactly `# {{slide title}}`.
- Add a blank line between slide sections.
- Under each heading, write that slide's speaker notes in {language}.

Outline:
{outline_json}

Slides JSON:
{slides_json}

Slides Sectioned Reference:
{slides_markdown}
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

Elements prompt contract (includes variant_coordinate_templates and layout_grid):
{elements_schema_json}

Presentation goal: {presentation_goal}
Target audience: {target_audience}
Previous slide summary: {previous_slide_summary}
Next slide summary: {next_slide_summary}
User request:
{user_request}

Slide contract:
{slide_info_json}

Current slide:
{current_slide_json}

Rules:
- Preserve the slide contract. Apply the user request without breaking the flow.
- ALWAYS use elements as the primary representation.
- Re-apply the variant_coordinate_templates for the chosen slide_variant as your coordinate baseline.

LAYOUT DISCIPLINE — every generated page must satisfy ALL of the following:
1. Slide title text_box: y in [0.45, 0.95], h=0.55, x=0.75, font_size >= 22, font_bold=true.
2. No body element may have y < 1.1.
3. All elements must be within safe_zone: x >= 0.75, x+w <= 12.58, y >= 0.45, y+h <= 7.1.
4. Text fit: h >= font_size * line_count * 0.028 + 0.15.
5. Bullet list fit: h >= items.length * 0.50.
6. Shapes acting as panel backgrounds must appear BEFORE text/bullet elements on top of them.
7. Left-edge elements share x=0.75 or x=1.05.
8. Two-column layouts: left x=0.75 w=5.77, right x=6.82 w=5.76, gap=0.30.

CONTENT RULES:
- Do not exceed 5 bullets.
- Each bullet item: max 55 characters.
- Headline (title): max 45 characters.
- Use only source-backed content.
- Do NOT include content from the previous or next slide in this slide's body.

WRITING STYLE — strictly enforced:
- Write complete, readable phrases. NEVER use ~입니다, ~합니다, ~됩니다, ~있습니다.
- Use plain-form endings (e.g. ~다, ~된다) or noun-terminated phrases.
- Do NOT use "표지", "마무리", "목차" as eyebrow or headline.

BULLET CHARACTER — vary bullet_char to match tone: "•" neutral, "▸" sequential, "◆" key findings, "–" contrast, "›" sub-points.

IMAGE PLACEHOLDER — add image_placeholder when a visual (diagram, photo, chart) would genuinely aid understanding. Set description to a concise user instruction.

- Write in {language}.

Source document:
{content}
"""

_EVALUATE_SLIDE_PROMPT = """
You evaluate one generated presentation slide.
Return valid JSON only with keys: passed, score, checklist, issues, feedback.

Language: {language}
Previous slide summary: {previous_slide_summary}
Next slide summary: {next_slide_summary}
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
            ("발표 시작", "cover", "hook", "title_page"),
            ("서론", "problem_intro", "informative", "content_box_list"),
            ("피부 타입 분석", "detail", "informative", "content_box_list"),
            ("나의 피부 타입", "detail", "informative", "content_sidebar"),
            ("피부 타입에 따른 원인 분석", "analysis", "analytical", "content_split_band"),
            ("피부 관리 방법 설계", "solution", "informative", "content_compact"),
            ("결론", "summary", "persuasive", "content_two_panel"),
            ("마무리", "closing", "closing", "closing_page"),
        ]
        result: dict[str, Any] = {}
        for index, (slide_title, role, tone, variant) in enumerate(sections, start=1):
            result[slide_title] = {
                "id": f"slide_{index:02d}",
                "role": role,
                "goal": f"{slide_title} 핵심 내용 전달",
                "key_points": ["핵심 포인트 1", "핵심 포인트 2"],
                "tone": tone,
                "description": f"{slide_title} 슬라이드",
                "page_size": 1,
                "preferred_variant": variant,
            }
        response = {
            "title": str(title).strip() or "Presentation",
            "theme": "clean_light",
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
        next_slide_summary: str = "",
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _GENERATE_SLIDE_PROMPT.format(
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            previous_slide_summary=previous_slide_summary or "(none)",
            next_slide_summary=next_slide_summary or "(none)",
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
        next_slide_summary: str,
        language: str,
    ) -> dict[str, Any]:
        bullet_count = len(_extract_slide_bullets(slide_output))
        issues: list[str] = []
        if bullet_count > 5:
            issues.append("bullet 수가 5개를 초과함")
        if not next_slide_summary and slide_info.get("role") == "summary":
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
                f"다음 슬라이드로 이어질 흐름 존재 여부: {'예' if next_slide_summary or slide_info.get('role') == 'summary' else '아니오'}",
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
        slides_markdown = _format_slides_for_notes_prompt(slides)
        prompt = _GENERATE_NOTES_PROMPT.format(
            slides_json=json.dumps(slides, ensure_ascii=False)[:7000],
            slides_markdown=slides_markdown[:7000],
            outline_json=json.dumps(outline, ensure_ascii=False)[:4000],
            language=language,
        )
        sections: list[str] = []
        for slide in slides:
            title = str(slide.get("title", "")).strip() or "Untitled Slide"
            bullets = _extract_slide_bullets(slide)
            if bullets:
                body = f"{title}에서는 {', '.join(bullets)}를 중심으로 설명합니다."
            else:
                body = f"{title} 슬라이드를 설명합니다."
            sections.append(f"# {title}\n{body}")
        response = {"notes": "\n\n".join(sections)}
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
        next_slide_summary: str = "",
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _REGENERATE_SLIDE_PROMPT.format(
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            previous_slide_summary=previous_slide_summary or "(none)",
            next_slide_summary=next_slide_summary or "(none)",
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
                next_slide_summary=next_slide_summary,
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
        next_slide_summary: str = "",
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _GENERATE_SLIDE_PROMPT.format(
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            previous_slide_summary=previous_slide_summary or "(none)",
            next_slide_summary=next_slide_summary or "(none)",
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
        next_slide_summary: str,
        language: str,
    ) -> dict[str, Any]:
        prompt = _EVALUATE_SLIDE_PROMPT.format(
            language=language,
            previous_slide_summary=previous_slide_summary or "(none)",
            next_slide_summary=next_slide_summary or "(none)",
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
        slides_markdown = _format_slides_for_notes_prompt(slides)
        prompt = _GENERATE_NOTES_PROMPT.format(
            slides_json=json.dumps(slides, ensure_ascii=False)[:7000],
            slides_markdown=slides_markdown[:7000],
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
        next_slide_summary: str = "",
        request_label: str = "",
    ) -> dict[str, Any]:
        prompt = _REGENERATE_SLIDE_PROMPT.format(
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            previous_slide_summary=previous_slide_summary or "(none)",
            next_slide_summary=next_slide_summary or "(none)",
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

