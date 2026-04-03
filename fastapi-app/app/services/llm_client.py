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

        # Ensure deterministic size: keep slide outline aligned with chunk-derived limit if provided.
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
            # Deterministic fallback: take earliest sentences.
            for s in sentences:
                cleaned = re.sub(r"\s+", " ", s).strip()
                if cleaned and cleaned not in picked:
                    picked.append(cleaned)
                if len(picked) >= max_bullets:
                    break

        return [p[:160] for p in picked[:max_bullets]]

    def _generate_slide(self, data: dict[str, Any]) -> dict[str, Any]:
        slide_number = int(data["slide_number"])
        outline_item = data.get("outline_item") or {}
        slide_id = _safe_get_text(data.get("slide_id")) or f"slide_{slide_number:02d}"
        title = _safe_get_text(outline_item.get("title")) or f"Slide {slide_number}"
        goal = _safe_get_text(outline_item.get("goal")) or ""

        chunks = data.get("chunks") or []
        if not isinstance(chunks, list):
            chunks = []

        keywords = extract_top_keywords(f"{title} {goal}", top_n=8)
        prev_title = _safe_get_text(data.get("prev_title"))
        next_title = _safe_get_text(data.get("next_title"))
        if prev_title:
            keywords += extract_top_keywords(prev_title, top_n=3)
        if next_title:
            keywords += extract_top_keywords(next_title, top_n=3)
        # Deduplicate deterministically while preserving order.
        seen: set[str] = set()
        keywords = [k for k in keywords if not (k in seen or seen.add(k))]  # type: ignore
        keywords = keywords[:8]

        scored: list[tuple[int, dict[str, Any]]] = []
        for c in chunks:
            cid = _safe_get_text(c.get("chunk_id"))
            c_text = _safe_get_text(c.get("text"))[:6000]
            score = self._score_chunk(c_text, keywords)
            scored.append((score, {"chunk_id": cid, "text": c_text}))
        scored.sort(key=lambda x: (-x[0], x[1]["chunk_id"]))
        top = [s for s in scored[:3] if s[0] > 0] or scored[:2]

        source_chunk_ids = [t[1]["chunk_id"] for t in top[:2] if t[1]["chunk_id"]]

        # Build bullets from the highest scoring chunk(s).
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
        # Regeneration uses current slide + neighbor titles to bias bullets.
        data = dict(data)
        slide_number = int(data["slide_number"])
        outline_item = data.get("outline_item") or {}
        data["outline_item"] = outline_item
        # Add neighbor content bias via prompt data.
        prev_title = _safe_get_text(data.get("prev_title"))
        next_title = _safe_get_text(data.get("next_title"))
        data["prev_title"] = prev_title
        data["next_title"] = next_title
        return self._generate_slide(data)

    def _regenerate_notes(self, data: dict[str, Any]) -> dict[str, Any]:
        slide = data["slide"]
        return self._generate_notes({"slide": slide})


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
                {"role": "system", "content": "Return only valid JSON."},
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
        content = _safe_get_text(content).strip()
        # Best-effort JSON extraction.
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError("Model did not return JSON content.")
        raw_json = content[start : end + 1]
        return json.loads(raw_json)


def create_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_mode == "mock":
        return MockLLMClient()
    return OpenAICompatibleLLMClient(settings)

