from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..core.config import Settings
from ..utils.token_utils import extract_top_keywords, split_sentences, tokenize_words


class LLMClient(ABC):
    @abstractmethod
    async def generate_json(self, prompt: str, response_schema: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def _extract_task_and_data(prompt: str) -> tuple[str, dict[str, Any]]:
    task_match = re.search(r"^\s*TASK\s*:\s*([A-Za-z0-9_\-]+)\s*$", prompt, flags=re.MULTILINE)
    if not task_match:
        raise ValueError("Prompt does not contain TASK: <task_name> line.")
    task = task_match.group(1).strip()

    idx = prompt.find("DATA_JSON:")
    if idx == -1:
        raise ValueError("Prompt does not contain DATA_JSON: marker.")
    data_str = prompt[idx + len("DATA_JSON:") :].strip()
    data = json.loads(data_str)
    if not isinstance(data, dict):
        raise ValueError("DATA_JSON must be a JSON object.")
    return task, data


def _safe_get_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


# ──────────────────────────────────────────────────────────────────────────────
# Mock client (개발·테스트용)
# ──────────────────────────────────────────────────────────────────────────────

class MockLLMClient(LLMClient):
    async def generate_json(self, prompt: str, response_schema: dict[str, Any]) -> dict[str, Any]:
        task, data = _extract_task_and_data(prompt)

        if task == "generate_outline":
            return self._generate_outline(data)
        if task == "generate_slide":
            return self._generate_slide(data)
        if task == "generate_notes":
            return self._generate_notes(data)
        if task == "regenerate_slide":
            return self._regenerate_slide(data)
        if task == "regenerate_notes":
            return self._regenerate_notes(data)

        raise ValueError(f"Unsupported TASK: {task}")

    def _generate_outline(self, data: dict[str, Any]) -> dict[str, Any]:
        title = _safe_get_text(data.get("title"))
        summary = _safe_get_text(data.get("summary"))
        language = _safe_get_text(data.get("language")) or "en"
        tone = _safe_get_text(data.get("tone")) or "neutral"
        max_slides = int(data.get("max_slides") or 8)

        keywords = extract_top_keywords(summary or title, top_n=10) or ["overview", "key", "insights", "impact"]
        deck_title = title.strip() if title.strip() else f"SlideCraft AI: {keywords[0].title()}"
        deck_title = deck_title[:80]

        objective = f"Deliver a {tone} {language} deck that explains {', '.join(keywords[:3])} with clear structure and actionable takeaways."

        n_slides = max(4, min(max_slides, 6 + (len(keywords) % 3) - 1))
        slide_outline: list[dict[str, Any]] = []
        for i in range(n_slides):
            kw = keywords[i % len(keywords)]
            slide_outline.append(
                {
                    "slide_number": i + 1,
                    "title": f"{deck_title} - {kw.title()}",
                    "goal": f"Explain {kw} in a way that supports the overall objective and helps the audience decide what to do next.",
                }
            )

        if isinstance(data.get("slide_count_hint"), int):
            hint = int(data["slide_count_hint"])
            slide_outline = slide_outline[: max(1, hint)]

        return {
            "deck_title": deck_title,
            "presentation_objective": objective,
            "slide_outline": slide_outline,
        }

    def _score_chunk(self, chunk_text: str, keywords: list[str]) -> int:
        if not keywords:
            return 0
        lowered = chunk_text.lower()
        score = 0
        for kw in keywords:
            score += lowered.count(kw.lower())
        return score

    def _extract_bullets(self, chunk_text: str, keywords: list[str], max_bullets: int = 4) -> list[str]:
        sentences = split_sentences(chunk_text)
        kw_set = {k.lower() for k in keywords if k}
        picked: list[str] = []
        for s in sentences:
            ls = s.lower()
            if any(kw in ls for kw in kw_set):
                cleaned = re.sub(r"\s+", " ", s).strip()
                if cleaned and cleaned not in picked:
                    picked.append(cleaned)
            if len(picked) >= max_bullets:
                break

        if len(picked) < max_bullets:
            for s in sentences:
                cleaned = re.sub(r"\s+", " ", s).strip()
                if cleaned and cleaned not in picked:
                    picked.append(cleaned)
                if len(picked) >= max_bullets:
                    break

        return picked[:max_bullets]

    def _generate_slide(self, data: dict[str, Any]) -> dict[str, Any]:
        slide_number = int(data.get("slide_number") or 1)
        slide_id = _safe_get_text(data.get("slide_id")) or f"slide_{slide_number:02d}"
        outline_item = data.get("outline_item") or {}
        title = _safe_get_text(outline_item.get("title")) or f"Slide {slide_number}"
        goal = _safe_get_text(outline_item.get("goal")) or ""

        chunks = data.get("chunks") or []
        keywords = extract_top_keywords(f"{title} {goal}", top_n=8) or tokenize_words(title)[:5]

        scored: list[tuple[int, dict[str, Any]]] = []
        for c in chunks:
            text = _safe_get_text(c.get("text"))
            score = self._score_chunk(text, keywords)
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:3]
        source_chunk_ids = [_safe_get_text(c.get("chunk_id")) for _, c in top if c.get("chunk_id")]

        bullets: list[str] = []
        for _, c in top[:2]:
            bullets = self._extract_bullets(c["text"], keywords, max_bullets=4)
            if bullets:
                break
        if not bullets:
            bullets = [f"Key point about {keywords[0].title()}" if keywords else "Key point"] * 3

        return {
            "slide_id": slide_id,
            "title": title,
            "goal": goal,
            "bullets": bullets[:4],
            "source_chunk_ids": source_chunk_ids,
        }

    def _generate_notes(self, data: dict[str, Any]) -> dict[str, Any]:
        slide = data["slide"]
        slide_id = _safe_get_text(slide.get("slide_id"))
        title = _safe_get_text(slide.get("title"))
        goal = _safe_get_text(slide.get("goal"))
        bullets = slide.get("bullets") or []
        if not isinstance(bullets, list):
            bullets = []

        keywords = extract_top_keywords(f"{title} {goal}", top_n=6)
        elaborations: list[str] = []
        for b in bullets:
            b_clean = re.sub(r"\s+", " ", _safe_get_text(b)).strip()
            if not b_clean:
                continue
            kw = keywords[0] if keywords else "key concept"
            elaborations.append(f"When presenting this, connect it to {kw}: {b_clean}")

        body = " ".join(elaborations)
        if len(body) > 900:
            body = body[:900].rsplit(" ", 1)[0] + "..."

        opening = f"Today, we'll cover: {title}. The goal is to help the audience understand and apply it ({goal})."
        notes = f"{opening}\n\n{body}"
        notes = notes.strip()

        return {"slide_id": slide_id, "notes": notes}

    def _regenerate_slide(self, data: dict[str, Any]) -> dict[str, Any]:
        data = dict(data)
        slide_number = int(data["slide_number"])
        outline_item = data.get("outline_item") or {}
        data["outline_item"] = outline_item
        prev_title = _safe_get_text(data.get("prev_title"))
        next_title = _safe_get_text(data.get("next_title"))
        data["prev_title"] = prev_title
        data["next_title"] = next_title
        return self._generate_slide(data)

    def _regenerate_notes(self, data: dict[str, Any]) -> dict[str, Any]:
        slide = data["slide"]
        return self._generate_notes({"slide": slide})


# ──────────────────────────────────────────────────────────────────────────────
# OpenAI 호환 클라이언트 (GPT-4o 등)
# ──────────────────────────────────────────────────────────────────────────────

class OpenAICompatibleLLMClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate_json(self, prompt: str, response_schema: dict[str, Any]) -> dict[str, Any]:
        if not self._settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        url = self._settings.openai_base_url.rstrip("/") + "/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self._settings.openai_api_key}"}

        payload: dict[str, Any] = {
            "model": self._settings.openai_model,
            "messages": [
                {"role": "system", "content": "Return only valid JSON. Do not include markdown code blocks or any text outside the JSON object."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return _parse_json_from_text(_safe_get_text(content))


# ──────────────────────────────────────────────────────────────────────────────
# Gemini 클라이언트
# ──────────────────────────────────────────────────────────────────────────────

class GeminiLLMClient(LLMClient):
    """Google Gemini API 클라이언트 (google-generativeai 패키지 사용)"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any = None

    def _get_client(self) -> Any:
        """지연 초기화 — import는 한 번만"""
        if self._client is None:
            try:
                import google.generativeai as genai  # type: ignore[import]
            except ImportError as e:
                raise RuntimeError(
                    "google-generativeai 패키지가 설치되지 않았습니다. "
                    "pip install google-generativeai 를 실행하세요."
                ) from e

            if not self._settings.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

            genai.configure(api_key=self._settings.gemini_api_key)
            self._client = genai.GenerativeModel(
                model_name=self._settings.gemini_model,
                generation_config={
                    "temperature": 0.2,
                    "response_mime_type": "application/json",  # JSON 모드 강제
                },
            )
        return self._client

    async def generate_json(self, prompt: str, response_schema: dict[str, Any]) -> dict[str, Any]:
        import asyncio

        model = self._get_client()
        system_instruction = (
            "You are a presentation assistant. "
            "Always respond with a single valid JSON object only. "
            "Do not include any markdown, code blocks, or explanatory text."
        )
        full_prompt = f"{system_instruction}\n\n{prompt}"

        # google-generativeai의 동기 API를 비동기로 래핑
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: model.generate_content(full_prompt)
        )

        raw_text = response.text.strip()
        return _parse_json_from_text(raw_text)


# ──────────────────────────────────────────────────────────────────────────────
# 공통 JSON 파싱 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _parse_json_from_text(text: str) -> dict[str, Any]:
    """LLM 응답 텍스트에서 JSON 객체를 추출합니다."""
    # 마크다운 코드블록 제거
    text = re.sub(r"```(?:json)?", "", text).strip()
    text = text.replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"LLM이 유효한 JSON을 반환하지 않았습니다. 응답: {text[:200]}")

    raw_json = text[start : end + 1]
    return json.loads(raw_json)


# ──────────────────────────────────────────────────────────────────────────────
# 팩토리 함수
# ──────────────────────────────────────────────────────────────────────────────

def create_llm_client(settings: Settings) -> LLMClient:
    """LLM_MODE 환경 변수에 따라 적절한 클라이언트를 반환합니다."""
    mode = settings.llm_mode

    if mode == "gemini":
        return GeminiLLMClient(settings)
    if mode == "openai":
        return OpenAICompatibleLLMClient(settings)
    if mode == "mock":
        return MockLLMClient()

    raise ValueError(
        f"알 수 없는 LLM_MODE: '{mode}'. "
        "지원 값: 'mock', 'openai', 'gemini'"
    )