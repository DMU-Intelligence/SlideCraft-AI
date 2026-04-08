from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..core.config import Settings

logger = logging.getLogger(__name__)


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
        "title",
        "section",
        "summary",
        "two_column",
    }:
        return preferred_variant

    role = str(slide_info.get("role", "")).strip().lower()
    key_points = slide_info.get("key_points", [])
    if role == "problem_intro":
        return "title"
    if role in {"summary", "solution"}:
        return "summary"
    if isinstance(key_points, list) and len(key_points) >= 4:
        return "two_column"
    return "section"


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
    async def clean_text(self, raw_text: str, language: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def generate_outline(
        self,
        title: str,
        content: str,
        language: str,
        presentation_goal: str,
        target_audience: str,
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
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def generate_notes(
        self,
        slides: list[dict[str, Any]],
        outline: dict[str, Any],
        language: str,
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
You are designing a presentation outline from a source document.
Return valid JSON only.

Context:
- Document title: {title}
- Language: {language}
- Presentation goal: {presentation_goal}
- Target audience: {target_audience}

Task:
- First create a concise presentation title suitable for the audience and source document.
- Then create slide-level outline entries, not section-only headings.
- Each outline entry value must include:
  id, role, goal, key_points, tone, description, page_size
- Use this JSON shape:
{{
  "title": "presentation title",
  "outline": {{
    "Slide Title": {{
      "id": "slide_01",
      "role": "problem_intro|detail|solution|summary|comparison|analysis",
      "goal": "one sentence",
      "key_points": ["...", "..."],
      "tone": "informative|analytical|persuasive|closing|hook",
      "description": "speaker-facing design description",
      "page_size": 1
    }}
  }}
}}

Constraints:
- Make the presentation title specific and natural, not just the raw filename.
- Keep the flow coherent for a general audience.
- Keep page_size between 1 and 2.
- Keep key_points concise and grounded in the source document.
- Do not include topics unsupported by the source.

Source document:
{content}
"""

_GENERATE_SLIDE_PROMPT = """
You create one presentation slide in JSON.
Return valid JSON only with this shape:
{{
  "title": "string",
  "theme": "clean_light|bold_dark|editorial",
  "slide_variant": "title_page|content_box_list|content_two_panel|content_sidebar|content_split_band|content_compact|closing_page",
  "pages": [
    {{
      "background": "#FFFFFF",
      "slots": {{
        "eyebrow": "optional short label",
        "headline": "main message",
        "body": "supporting sentence",
        "bullets": ["...", "..."],
        "left_points": ["...", "..."],
        "right_points": ["...", "..."],
        "highlight": "optional short callout",
        "people": ["presenter or team information when available"]
      }},
      "elements": [
        {{
          "type": "text_box",
          "text": "string",
          "x": 1.0,
          "y": 0.5,
          "w": 11.8,
          "h": 1.0,
          "font_name": "Malgun Gothic",
          "font_size": 28,
          "font_bold": false,
          "font_color": "#0F172A",
          "align": "left"
        }},
        {{
          "type": "bullet_list",
          "x": 1.0,
          "y": 1.5,
          "w": 11.8,
          "h": 1.8,
          "items": ["...", "..."],
          "bullet_char": "-",
          "bullet_color": "#2563EB",
          "font_name": "Malgun Gothic",
          "font_size": 16,
          "font_color": "#1E293B"
        }}
      ]
    }}
  ]
}}

Presentation context:
- Goal: {presentation_goal}
- Target audience: {target_audience}
- Previous slide summary: {previous_slide_summary}
- Next slide goal: {next_slide_goal}

Current slide contract:
{slide_info_json}

Rules:
- This is a fill-in task based on the contract above, not a free rewrite.
- Prefer `elements` as the primary representation.
- Use `slots` only as optional helper metadata.
- If you provide `elements`, use `x`, `y`, `w`, `h` for coordinates.
- Pick one `slide_variant` and keep the slide faithful to that variant.
- If the slide is the opening slide and speaker/team info is present in the contract, include it in `people`.
- Reflect the slide goal and key_points directly.
- Use at most 5 bullets per page.
- Keep wording easy for non-experts.
- Add one short supporting body or highlight when useful.
- Use only source-backed content.
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
id, role, goal, key_points, tone, description, page_size

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
- Do not exceed 5 bullets.
- Use only source-backed content.
- Write in {language}.

Source document:
{content}
"""


class MockLLMClient(LLMClient):
    async def clean_text(self, raw_text: str, language: str) -> str:
        return re.sub(r"\s+", " ", raw_text).strip()

    async def generate_outline(
        self,
        title: str,
        content: str,
        language: str,
        presentation_goal: str,
        target_audience: str,
    ) -> dict[str, Any]:
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
            }
        return {
            "title": str(title).strip() or "Presentation",
            "outline": result,
        }

    async def generate_slide(
        self,
        presentation_goal: str,
        target_audience: str,
        slide_info: dict[str, Any],
        content: str,
        language: str,
        previous_slide_summary: str = "",
        next_slide_goal: str = "",
    ) -> dict[str, Any]:
        display_title = str(slide_info["title"]).strip()
        bullets = slide_info.get("key_points", [])[:5]
        slide_variant = _pick_slide_variant(slide_info)
        theme = _pick_theme(slide_info)
        page_background = "#FFFDF8" if theme == "editorial" else "#0F172A" if theme == "bold_dark" else "#F8FAFC"
        slots: dict[str, Any] = {
            "eyebrow": str(slide_info.get("role", "")).replace("_", " ").title(),
            "headline": display_title,
            "body": str(slide_info.get("description", "")),
            "highlight": str(slide_info.get("goal", "")),
        }
        if slide_variant == "two_column":
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
        return {
            "title": slide_info["title"],
            "theme": theme,
            "slide_variant": slide_variant,
            "pages": [page],
        }

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
    ) -> str:
        lines: list[str] = []
        for slide in slides:
            bullets = _extract_slide_bullets(slide)
            if bullets:
                lines.append(f"{slide.get('title', '')}에서는 {', '.join(bullets)}를 중심으로 설명합니다.")
            else:
                lines.append(f"{slide.get('title', '')} 슬라이드를 설명합니다.")
        return " ".join(lines)

    async def update_outline(
        self,
        titles: list[str],
        content: str,
        language: str,
        presentation_goal: str,
        target_audience: str,
    ) -> dict[str, Any]:
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
            }
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
    ) -> dict[str, Any]:
        if current_slide:
            return current_slide
        return await self.generate_slide(
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            slide_info=slide_info,
            content=content,
            language=language,
            previous_slide_summary=previous_slide_summary,
            next_slide_goal=next_slide_goal,
        )


class OpenAICompatibleLLMClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

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

    async def clean_text(self, raw_text: str, language: str) -> str:
        prompt = _CLEAN_TEXT_PROMPT.format(language=language, raw_text=raw_text[:8000])
        result = _parse_json(await self._call(prompt))
        return str(result.get("content", raw_text))

    async def generate_outline(
        self,
        title: str,
        content: str,
        language: str,
        presentation_goal: str,
        target_audience: str,
    ) -> dict[str, Any]:
        prompt = _GENERATE_OUTLINE_PROMPT.format(
            title=title,
            content=content[:7000],
            language=language,
            presentation_goal=presentation_goal,
            target_audience=target_audience,
        )
        return _parse_json(await self._call(prompt))

    async def generate_slide(
        self,
        presentation_goal: str,
        target_audience: str,
        slide_info: dict[str, Any],
        content: str,
        language: str,
        previous_slide_summary: str = "",
        next_slide_goal: str = "",
    ) -> dict[str, Any]:
        prompt = _GENERATE_SLIDE_PROMPT.format(
            presentation_goal=presentation_goal,
            target_audience=target_audience,
            previous_slide_summary=previous_slide_summary or "(none)",
            next_slide_goal=next_slide_goal or "(none)",
            slide_info_json=json.dumps(slide_info, ensure_ascii=False),
            content=content[:5000],
            language=language,
        )
        return _parse_json(await self._call(prompt))

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
        return _parse_json(await self._call(prompt))

    async def generate_notes(
        self,
        slides: list[dict[str, Any]],
        outline: dict[str, Any],
        language: str,
    ) -> str:
        prompt = _GENERATE_NOTES_PROMPT.format(
            slides_json=json.dumps(slides, ensure_ascii=False)[:7000],
            outline_json=json.dumps(outline, ensure_ascii=False)[:4000],
            language=language,
        )
        result = _parse_json(await self._call(prompt))
        return str(result.get("notes", ""))

    async def update_outline(
        self,
        titles: list[str],
        content: str,
        language: str,
        presentation_goal: str,
        target_audience: str,
    ) -> dict[str, Any]:
        prompt = _UPDATE_OUTLINE_PROMPT.format(
            titles="\n".join(f"- {title}" for title in titles),
            content=content[:7000],
            language=language,
            presentation_goal=presentation_goal,
            target_audience=target_audience,
        )
        return _parse_json(await self._call(prompt))

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
        )
        return _parse_json(await self._call(prompt))


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
        url = os.getenv("GEMINI_CLI_SERVER_URL", "http://localhost:5001")
        full_prompt = "Return only valid JSON. No explanation, no markdown fences.\n\n" + prompt

        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{url}/generate",
                json={"prompt": full_prompt},
            )
            response.raise_for_status()
            data = response.json()
        return data["response"]


class GptCLIClient(OpenAICompatibleLLMClient):
    """
    gemini-cli-server.py (CLI 브릿지 서버)에 HTTP로 프롬프트를 전달하여
    GPT CLI 응답을 받습니다.

    환경 변수:
        GPT_CLI_SERVER_URL: 브릿지 서버 주소 (기본값: http://localhost:5001)
    """

    async def _call(self, prompt: str) -> str:
        url = os.getenv("GPT_CLI_SERVER_URL", "http://localhost:5001")
        full_prompt = "Return only valid JSON. No explanation, no markdown fences.\n\n" + prompt

        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{url}/generate",
                json={"prompt": full_prompt},
            )
            response.raise_for_status()
            data = response.json()
        return data["response"]


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

