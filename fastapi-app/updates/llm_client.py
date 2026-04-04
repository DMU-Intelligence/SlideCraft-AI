from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..core.config import Settings


# ══════════════════════════════════════════════════════════════════════════════
# Abstract base
# ══════════════════════════════════════════════════════════════════════════════

class LLMClient(ABC):

    @abstractmethod
    async def clean_text(self, raw_text: str, language: str) -> str:
        """PDF 추출 원문 → AI 정리 텍스트"""
        raise NotImplementedError

    @abstractmethod
    async def generate_outline(
        self, title: str, content: str, language: str
    ) -> dict[str, Any]:
        """문서 기반 outline 생성
        Returns: {"제목": {"description": "...", "page_size": N}, ...}
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_slide(
        self,
        slide_title: str,
        description: str,
        page_size: int,
        content: str,
        language: str,
        prev_title: str = "",
        next_title: str = "",
    ) -> dict[str, Any]:
        """슬라이드 1개 생성 (elements + layout 포함)
        Returns: {"title": "...", "pages": [...]}
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_notes(
        self, slides: list[dict[str, Any]], language: str
    ) -> str:
        """전체 슬라이드 기반 스피치 대본 (단일 str) 생성"""
        raise NotImplementedError

    @abstractmethod
    async def update_outline(
        self, titles: list[str], content: str, language: str
    ) -> dict[str, Any]:
        """사용자 지정 title 목록으로 outline 재생성"""
        raise NotImplementedError

    @abstractmethod
    async def regenerate_slide(
        self,
        slide_title: str,
        description: str,
        page_size: int,
        content: str,
        language: str,
        user_request: str,
        current_slide: dict[str, Any],
    ) -> dict[str, Any]:
        """사용자 요청 반영하여 슬라이드 재생성"""
        raise NotImplementedError


# ══════════════════════════════════════════════════════════════════════════════
# Prompt 상수
# ══════════════════════════════════════════════════════════════════════════════

_CLEAN_TEXT_PROMPT = """\
당신은 문서 정리 전문가입니다.
아래 텍스트는 PDF에서 추출한 원문입니다.
다음 규칙에 따라 정리해주세요:
1. 내용을 요약하지 마세요. 대부분의 원문 내용을 유지하세요.
2. 깨진 문자, 의미 없는 특수문자, 불필요한 반복 개행을 제거하세요.
3. 표(table) 데이터가 있다면 읽기 쉬운 텍스트 형태로 변환하세요.
4. 문단/섹션 구조를 논리적으로 재배치하세요.
5. 원문에 없는 내용을 추가하지 마세요.
6. 결과는 {language} 텍스트로 반환하세요.
7. JSON 형식으로만 반환하세요: {{"content": "정리된 텍스트"}}

원문:
{raw_text}"""

_GENERATE_OUTLINE_PROMPT = """\
당신은 프레젠테이션 구성 전문가입니다.
아래 정리된 문서 내용을 바탕으로 PPT 목차(outline)를 생성하세요.

규칙:
1. 각 목차 항목은 {{ "description": "이 슬라이드에서 다룰 내용 한줄 설명", "page_size": 페이지수 }} 형식
2. page_size는 해당 슬라이드에 필요한 페이지 수 (내용이 많으면 2~3, 적으면 1)
3. 전체 흐름이 자연스럽도록 순서를 배치하세요
4. 문서 내용에 있는 주제만 다루세요
5. 결과는 JSON 객체로: {{ "항목제목": {{ "description": "...", "page_size": N }}, ... }}

문서 제목: {title}
언어: {language}
정리된 내용:
{content}"""

_GENERATE_SLIDE_PROMPT = """\
당신은 PPT 슬라이드 디자이너 겸 콘텐츠 작성자입니다.
아래 목차 항목에 대한 슬라이드를 내용 + 레이아웃 + 스타일 모두 포함하여 작성하세요.

## 작성할 슬라이드
- 제목: {slide_title}
- 설명: {slide_description}
- 페이지 수: {page_size}

## 전후 슬라이드 (흐름 참고)
- 이전: {prev_title}
- 다음: {next_title}

## 슬라이드 크기
- 가로: 13.33 inches, 세로: 7.5 inches

## 사용 가능한 element 타입

### 1. text_box — 텍스트 블럭
위치(left, top), 크기(width, height)는 inches 단위.
font_name, font_size(pt), font_bold, font_color(hex), align(left/center/right)
예시:
{{"type":"text_box","text":"내용","left":0.5,"top":0.5,"width":12.33,"height":1.0,"font_name":"Malgun Gothic","font_size":28,"font_bold":true,"font_color":"#FFFFFF","align":"left"}}

### 2. shape — 장식 도형 (사각형)
구분선, accent 바 등. fill_color(hex).
예시:
{{"type":"shape","shape_type":"rectangle","left":0,"top":0,"width":13.33,"height":0.08,"fill_color":"#5B8DEF"}}

### 3. bullet_list — 불릿 포인트 목록
items 배열에 3~5개 항목.
예시:
{{"type":"bullet_list","left":0.5,"top":1.75,"width":12.33,"height":5.2,"items":["항목1","항목2"],"bullet_char":"▸","bullet_color":"#5B8DEF","font_name":"Malgun Gothic","font_size":16,"font_color":"#D4D8E8"}}

## 디자인 가이드라인
1. 배경은 어두운 색 (#0F172A ~ #1A2744 범위)을 사용하세요.
2. 제목은 크고 굵게 (24~36pt, bold, 흰색 계열).
3. 본문은 읽기 쉬운 크기 (14~18pt, 밝은 회색 계열).
4. 상단에 accent 바(얇은 사각형)를 넣어 세련된 느낌을 주세요.
5. 제목과 본문 사이에 구분선(얇은 사각형)을 넣으세요.
6. elements는 겹치지 않게 배치하세요.
7. 좌표가 슬라이드 영역(13.33 x 7.5)을 벗어나지 않게 하세요.

## 콘텐츠 규칙
1. 정확히 {page_size}개의 페이지를 생성하세요.
2. 문서 내용에 근거한 내용만 작성하세요.
3. bullet은 한 문장으로 핵심만 담으세요.
4. {language}로 작성하세요.

## 참고 문서 내용
{content}

## 응답 형식 (JSON만)
{{"title":"슬라이드 제목","pages":[{{"background":"#hex색상","elements":[element 객체들]}}]}}"""

_GENERATE_NOTES_PROMPT = """\
당신은 프레젠테이션 발표 대본 작성 전문가입니다.
아래 모든 슬라이드 내용을 바탕으로 **하나의 연속적인 스피치 대본**을 작성하세요.

규칙:
1. 모든 슬라이드를 순서대로 커버하는 하나의 대본을 작성하세요
2. 슬라이드 간 자연스러운 전환 문구를 포함하세요
3. 청중에게 말하는 형태(구어체)로 작성하세요
4. 각 슬라이드의 핵심 포인트를 빠짐없이 포함하세요
5. 결과는 단일 문자열(str)로 반환하세요
6. 언어: {language}

슬라이드 목록:
{slides_json}

결과 JSON: {{ "notes": "전체 대본 내용..." }}"""

_UPDATE_OUTLINE_PROMPT = """\
당신은 프레젠테이션 구성 전문가입니다.
사용자가 지정한 목차 항목들에 맞게 PPT 목차(outline)를 생성하세요.

규칙:
1. 아래 제목 목록의 순서와 항목을 그대로 사용하세요 (제목 변경 금지)
2. 각 항목의 description과 page_size는 문서 내용을 참고하여 AI가 생성하세요
3. 결과는 JSON 객체로: {{ "항목제목": {{ "description": "...", "page_size": N }}, ... }}

지정된 목차 제목:
{titles}

언어: {language}
문서 내용:
{content}"""

_REGENERATE_SLIDE_PROMPT = """\
당신은 PPT 슬라이드 디자이너 겸 콘텐츠 작성자입니다.
기존 슬라이드를 사용자의 요청에 맞게 수정/재생성하세요.

## 슬라이드 정보
- 제목: {slide_title}
- 설명: {slide_description}
- 페이지 수: {page_size}

## 사용자 수정 요청
{user_request}

## 현재 슬라이드 내용 (참고용)
{current_slide}

## 슬라이드 크기
- 가로: 13.33 inches, 세로: 7.5 inches

## 사용 가능한 element 타입 (text_box / shape / bullet_list)
(generate_slide 와 동일한 element 규격 적용)

## 디자인 가이드라인
- 배경 어두운 색 (#0F172A ~ #1A2744)
- 제목 굵고 흰색, 본문 밝은 회색
- 상단 accent 바 + 구분선 포함

## 참고 문서 내용
{content}

## 언어: {language}

## 응답 형식 (JSON만)
{{"title":"슬라이드 제목","pages":[{{"background":"#hex색상","elements":[element 객체들]}}]}}"""


# ══════════════════════════════════════════════════════════════════════════════
# JSON 파싱 헬퍼
# ══════════════════════════════════════════════════════════════════════════════

def _parse_json(text: str) -> dict[str, Any]:
    text = re.sub(r"```(?:json)?", "", text).strip().replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"LLM이 유효한 JSON을 반환하지 않았습니다. 응답: {text[:300]}")
    return json.loads(text[start:end + 1])


# ══════════════════════════════════════════════════════════════════════════════
# Mock (개발/테스트용)
# ══════════════════════════════════════════════════════════════════════════════

class MockLLMClient(LLMClient):

    async def clean_text(self, raw_text: str, language: str) -> str:
        return re.sub(r"\s+", " ", raw_text).strip()

    async def generate_outline(
        self, title: str, content: str, language: str
    ) -> dict[str, Any]:
        sections = ["도입", "주요 내용", "세부 사항", "결론"]
        return {
            s: {"description": f"{s}에 관한 내용을 다룹니다.", "page_size": 1}
            for s in sections
        }

    async def generate_slide(
        self,
        slide_title: str,
        description: str,
        page_size: int,
        content: str,
        language: str,
        prev_title: str = "",
        next_title: str = "",
    ) -> dict[str, Any]:
        pages = []
        for i in range(page_size):
            suffix = f" ({i + 1}/{page_size})" if page_size > 1 else ""
            pages.append({
                "background": "#0F172A",
                "elements": [
                    {"type": "shape", "shape_type": "rectangle",
                     "left": 0.0, "top": 0.0, "width": 13.33, "height": 0.08,
                     "fill_color": "#5B8DEF"},
                    {"type": "text_box", "text": f"{slide_title}{suffix}",
                     "left": 0.5, "top": 0.5, "width": 12.33, "height": 1.0,
                     "font_name": "Malgun Gothic", "font_size": 28, "font_bold": True,
                     "font_color": "#FFFFFF", "align": "left"},
                    {"type": "shape", "shape_type": "rectangle",
                     "left": 0.5, "top": 1.55, "width": 12.33, "height": 0.03,
                     "fill_color": "#5B8DEF"},
                    {"type": "bullet_list",
                     "left": 0.5, "top": 1.75, "width": 12.33, "height": 5.2,
                     "items": [description, "Mock 항목 2", "Mock 항목 3"],
                     "bullet_char": "▸", "bullet_color": "#5B8DEF",
                     "font_name": "Malgun Gothic", "font_size": 16,
                     "font_color": "#D4D8E8"},
                ],
            })
        return {"title": slide_title, "pages": pages}

    async def generate_notes(
        self, slides: list[dict[str, Any]], language: str
    ) -> str:
        parts = ["안녕하세요. 지금부터 발표를 시작하겠습니다.\n"]
        for slide in slides:
            t = slide.get("title", "")
            parts.append(f"다음은 '{t}' 슬라이드입니다. {t}에 대해 설명드리겠습니다.")
        parts.append("\n이상으로 발표를 마치겠습니다. 감사합니다.")
        return " ".join(parts)

    async def update_outline(
        self, titles: list[str], content: str, language: str
    ) -> dict[str, Any]:
        return {
            t: {"description": f"{t}에 관한 내용을 다룹니다.", "page_size": 1}
            for t in titles
        }

    async def regenerate_slide(
        self,
        slide_title: str,
        description: str,
        page_size: int,
        content: str,
        language: str,
        user_request: str,
        current_slide: dict[str, Any],
    ) -> dict[str, Any]:
        return await self.generate_slide(
            slide_title, description, page_size, content, language
        )


# ══════════════════════════════════════════════════════════════════════════════
# OpenAI 호환 클라이언트
# ══════════════════════════════════════════════════════════════════════════════

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
                {"role": "system", "content": "Return only valid JSON. No markdown, no code blocks."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    async def clean_text(self, raw_text: str, language: str) -> str:
        prompt = _CLEAN_TEXT_PROMPT.format(language=language, raw_text=raw_text[:8000])
        result = _parse_json(await self._call(prompt))
        return result.get("content", raw_text)

    async def generate_outline(
        self, title: str, content: str, language: str
    ) -> dict[str, Any]:
        prompt = _GENERATE_OUTLINE_PROMPT.format(
            title=title, language=language, content=content[:6000]
        )
        return _parse_json(await self._call(prompt))

    async def generate_slide(
        self,
        slide_title: str,
        description: str,
        page_size: int,
        content: str,
        language: str,
        prev_title: str = "",
        next_title: str = "",
    ) -> dict[str, Any]:
        prompt = _GENERATE_SLIDE_PROMPT.format(
            slide_title=slide_title,
            slide_description=description,
            page_size=page_size,
            prev_title=prev_title or "(없음)",
            next_title=next_title or "(없음)",
            language=language,
            content=content[:4000],
        )
        return _parse_json(await self._call(prompt))

    async def generate_notes(
        self, slides: list[dict[str, Any]], language: str
    ) -> str:
        prompt = _GENERATE_NOTES_PROMPT.format(
            language=language,
            slides_json=json.dumps(slides, ensure_ascii=False)[:6000],
        )
        result = _parse_json(await self._call(prompt))
        return result.get("notes", "")

    async def update_outline(
        self, titles: list[str], content: str, language: str
    ) -> dict[str, Any]:
        titles_str = "\n".join(f"- {t}" for t in titles)
        prompt = _UPDATE_OUTLINE_PROMPT.format(
            titles=titles_str, language=language, content=content[:6000]
        )
        return _parse_json(await self._call(prompt))

    async def regenerate_slide(
        self,
        slide_title: str,
        description: str,
        page_size: int,
        content: str,
        language: str,
        user_request: str,
        current_slide: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = _REGENERATE_SLIDE_PROMPT.format(
            slide_title=slide_title,
            slide_description=description,
            page_size=page_size,
            user_request=user_request,
            current_slide=json.dumps(current_slide, ensure_ascii=False)[:2000],
            language=language,
            content=content[:4000],
        )
        return _parse_json(await self._call(prompt))


# ══════════════════════════════════════════════════════════════════════════════
# Gemini 클라이언트
# ══════════════════════════════════════════════════════════════════════════════

class GeminiLLMClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                import google.generativeai as genai  # type: ignore[import]
            except ImportError as e:
                raise RuntimeError("google-generativeai 패키지가 설치되지 않았습니다.") from e
            if not self._settings.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다.")
            genai.configure(api_key=self._settings.gemini_api_key)
            self._model = genai.GenerativeModel(
                model_name=self._settings.gemini_model,
                generation_config={
                    "temperature": 0.2,
                    "response_mime_type": "application/json",
                },
            )
        return self._model

    async def _call(self, prompt: str) -> str:
        import asyncio
        model = self._get_model()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: model.generate_content(prompt)
        )
        return response.text.strip()

    async def clean_text(self, raw_text: str, language: str) -> str:
        prompt = _CLEAN_TEXT_PROMPT.format(language=language, raw_text=raw_text[:8000])
        result = _parse_json(await self._call(prompt))
        return result.get("content", raw_text)

    async def generate_outline(
        self, title: str, content: str, language: str
    ) -> dict[str, Any]:
        prompt = _GENERATE_OUTLINE_PROMPT.format(
            title=title, language=language, content=content[:6000]
        )
        return _parse_json(await self._call(prompt))

    async def generate_slide(
        self,
        slide_title: str,
        description: str,
        page_size: int,
        content: str,
        language: str,
        prev_title: str = "",
        next_title: str = "",
    ) -> dict[str, Any]:
        prompt = _GENERATE_SLIDE_PROMPT.format(
            slide_title=slide_title,
            slide_description=description,
            page_size=page_size,
            prev_title=prev_title or "(없음)",
            next_title=next_title or "(없음)",
            language=language,
            content=content[:4000],
        )
        return _parse_json(await self._call(prompt))

    async def generate_notes(
        self, slides: list[dict[str, Any]], language: str
    ) -> str:
        prompt = _GENERATE_NOTES_PROMPT.format(
            language=language,
            slides_json=json.dumps(slides, ensure_ascii=False)[:6000],
        )
        result = _parse_json(await self._call(prompt))
        return result.get("notes", "")

    async def update_outline(
        self, titles: list[str], content: str, language: str
    ) -> dict[str, Any]:
        titles_str = "\n".join(f"- {t}" for t in titles)
        prompt = _UPDATE_OUTLINE_PROMPT.format(
            titles=titles_str, language=language, content=content[:6000]
        )
        return _parse_json(await self._call(prompt))

    async def regenerate_slide(
        self,
        slide_title: str,
        description: str,
        page_size: int,
        content: str,
        language: str,
        user_request: str,
        current_slide: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = _REGENERATE_SLIDE_PROMPT.format(
            slide_title=slide_title,
            slide_description=description,
            page_size=page_size,
            user_request=user_request,
            current_slide=json.dumps(current_slide, ensure_ascii=False)[:2000],
            language=language,
            content=content[:4000],
        )
        return _parse_json(await self._call(prompt))


# ══════════════════════════════════════════════════════════════════════════════
# 팩토리
# ══════════════════════════════════════════════════════════════════════════════

def create_llm_client(settings: Settings) -> LLMClient:
    mode = settings.llm_mode
    if mode == "gemini":
        return GeminiLLMClient(settings)
    if mode == "openai":
        return OpenAICompatibleLLMClient(settings)
    if mode == "mock":
        return MockLLMClient()
    raise ValueError(
        f"알 수 없는 LLM_MODE: '{mode}'. 지원 값: 'mock', 'openai', 'gemini'"
    )
