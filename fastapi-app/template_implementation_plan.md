# Template 시스템 구현 계획서

## 목표

기존 PPTX 파일에서 elements JSON을 추출하여 템플릿으로 저장하고,
LLM이 생성한 슬라이드 콘텐츠를 해당 템플릿에 맞춰 재구성하는 시스템을 구축한다.

중요: **기존 1차 슬라이드 생성 로직은 그대로 유지**하고,
**모든 content slide의 elements JSON 생성이 끝난 뒤** 템플릿이 있을 때만
별도의 2차 LLM 단계에서 template adjustment를 수행한다.

## 전체 파이프라인

```
[사용자 PPTX 파일] → [template_extractor.py] → 템플릿 JSON (elements 형식) → template/{title}.json 저장

[slide_info + content] → [1차 LLM: 기존 slide 생성, elements.json 컨트랙트 기준]
                       → 모든 content slide의 Generated Slide JSON 생성 완료
                                                        ↓
                                   [2차 LLM: add_just_template / apply_template]
                                   (template_name이 있을 때만 실행)
                                   (각 Generated Slide + 모든 템플릿 페이지)
                                   → 가장 어울리는 템플릿 선택 + 콘텐츠 적용
                                                        ↓
                                              최종 SlideContent JSON → PPTX 렌더링
```

## 핵심 결정사항

- **템플릿 JSON 포맷**: 기존 elements JSON 스키마를 그대로 사용
- **기존 생성 로직 유지**: 1차 `generate_slide()` 로직은 수정하지 않고 그대로 사용
- **템플릿 적용 방식**: content slide 전체 생성 완료 후 별도 2차 LLM 호출 (Post-generation LLM adapter)
- **PPTX → JSON 추출**: python-pptx를 사용한 역변환
- **추출 범위**: 첫 페이지(표지), 목차 페이지, 마지막 2페이지(Q&A/감사 등) 제외 → **콘텐츠 슬라이드만** 추출
- **템플릿 저장**: `template/{title}.json` 파일로 저장
- **템플릿 선택**: LLM이 모든 템플릿 페이지를 보고 가장 어울리는 것을 **자동 선택**
- **템플릿 미지정 처리**: `template_name`이 `None`이거나 빈 문자열이면 템플릿 적용 단계는 즉시 `return`
- **템플릿 오류 처리**: `template_name`이 있는데 해당 템플릿 파일이 없으면 error 발생

---

## TASK 1: PPTX → JSON 추출 서비스

### 파일: `app/services/template_extractor.py` (NEW)

### 목적
사용자가 업로드한 PPTX 파일을 읽어서, **콘텐츠 슬라이드만** elements JSON으로 추출한다.
추출된 JSON은 기존 `elements.json` 프롬프트 컨트랙트와 **완전히 동일한 형식**을 따른다.

### 슬라이드 필터링 규칙

**제외 대상:**
- **첫 번째 슬라이드** (index 0): 표지 페이지
- **두 번째 슬라이드** (index 1): 목차 페이지
- **마지막 2개 슬라이드** (index -2, -1): Q&A / 감사 페이지

**포함 대상:**
- 나머지 모든 슬라이드 (index 2 ~ len-3) : 콘텐츠 슬라이드

예시: PPTX에 10장이 있으면 → index 2~7 (6장) 추출

### 기존 Pydantic 모델 (참고 — `app/schemas/generate.py`)

```python
class TextBoxElement(PositionedElement):
    type: Literal["text_box"] = "text_box"
    text: str
    font_name: str = "Malgun Gothic"
    font_size: int = 16
    font_bold: bool = False
    font_color: str = "#FFFFFF"
    align: Literal["left", "center", "right"] = "left"

class ShapeElement(PositionedElement):
    type: Literal["shape"] = "shape"
    shape_type: Literal["rectangle", "round_rectangle"] = "rectangle"
    fill_color: str = "#5B8DEF"

class BulletListElement(PositionedElement):
    type: Literal["bullet_list"] = "bullet_list"
    items: list[str]
    bullet_char: str = "-"
    bullet_color: str = "#5B8DEF"
    font_name: str = "Malgun Gothic"
    font_size: int = 16
    font_color: str = "#1E293B"

class PageLayout(BaseModel):
    background: str = "#FFFFFF"
    elements: list[SlideElement] = Field(default_factory=list)
    slots: dict[str, Any] = Field(default_factory=dict)

class SlideContent(BaseModel):
    title: str
    theme: Literal["clean_light", "bold_dark", "editorial"] = "clean_light"
    slide_variant: Literal[...] = "content_box_list"
    pages: list[PageLayout] = Field(default_factory=list)
```

### 추출 로직 상세

```python
from pptx import Presentation
from pptx.util import Inches, Emu
from pptx.enum.shapes import MSO_SHAPE_TYPE

class TemplateExtractor:
    """PPTX 파일에서 콘텐츠 슬라이드의 elements JSON을 추출한다."""

    def extract(self, pptx_path: str) -> list[dict]:
        """
        PPTX 파일을 읽고 콘텐츠 슬라이드별 elements 리스트를 반환한다.
        
        필터링: 첫 1장(표지), 두 번째 1장(목차), 마지막 2장(Q&A/감사) 제외.
        즉, slides[2:-2] 범위만 추출한다.
        
        PPTX 슬라이드 수가 5장 미만이면 필터링 없이 전체를 추출한다.

        Returns:
            list[dict] — 각 dict는 한 슬라이드의 정보:
            {
                "background": "#RRGGBB",
                "elements": [
                    {"type": "shape", ...},
                    {"type": "text_box", ...},
                    ...
                ]
            }
        """
        prs = Presentation(pptx_path)
        all_slides = list(prs.slides)
        
        # 슬라이드 필터링: 표지(1) + 목차(1) + 마지막(2) 제외
        if len(all_slides) >= 5:
            content_slides = all_slides[2:-2]
        else:
            content_slides = all_slides  # 5장 미만이면 전체
        
        result = []
        for slide in content_slides:
            page_data = self._extract_slide(slide)
            if page_data["elements"]:  # 빈 슬라이드는 건너뛰기
                result.append(page_data)
        return result
    
    def _extract_slide(self, slide) -> dict:
        """단일 슬라이드에서 background + elements 추출"""
        # ... 구현 ...
    
    def _extract_background(self, slide) -> str:
        """슬라이드 배경색 추출. solid fill이면 hex, 아니면 #FFFFFF"""
        # ... 구현 ...
    
    def _extract_shape_element(self, shape) -> list[dict]:
        """하나의 shape를 elements 리스트로 변환 (shape+text_box 분리 가능)"""
        # ... 구현 ...
```

### 변환 규칙

1. **좌표 변환**: python-pptx는 EMU(English Metric Units) 사용. `round(Emu(value).inches, 2)`로 변환하여 소수 2자리 반올림.
2. **배경색 추출**: `slide.background.fill`에서 solid fill인 경우 color 추출. 없으면 `"#FFFFFF"` 디폴트.
3. **Shape 처리**:
   - `shape.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE` → `"shape"` element로 변환
     - `shape.auto_shape_type`이 ROUNDED_RECTANGLE이면 `shape_type: "round_rectangle"`, 아니면 `"rectangle"`
     - txt가 비어있을 때(`shape.text_frame`에 텍스트 없거나 빈 문자열) → `"shape"` type
     - txt가 있을 때 → **텍스트 내용에 따라 판단**:
       - 불릿 형식(여러 줄)이면 `"bullet_list"`로 변환
       - 단일 텍스트이면 `"text_box"`로 변환하되 fill_color가 있으면 뒤에 `"shape"` element도 추가
   - `shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX` → `"text_box"` element로 변환
   - `shape.shape_type == MSO_SHAPE_TYPE.PLACEHOLDER` → 텍스트가 있으면 `"text_box"`, 없으면 무시
   - `shape.shape_type == MSO_SHAPE_TYPE.PICTURE` → **무시** (현재 스키마 미지원)
   - `shape.shape_type == MSO_SHAPE_TYPE.TABLE` → **무시**
   - `shape.shape_type == MSO_SHAPE_TYPE.GROUP` → **무시**
4. **font 속성 추출**: 첫 번째 paragraph의 첫 번째 run에서 추출
   - `font.name` → `font_name` (없으면 `"Malgun Gothic"` 디폴트)
   - `font.size` → `font_size` (Pt 정수로 변환, 없으면 16 디폴트)
   - `font.bold` → `font_bold` (None이면 False)
   - `font.color.rgb` → `font_color` (`"#RRGGBB"` 형식, 없으면 `"#000000"`)
   - `paragraph.alignment` → `align` (PP_ALIGN 값을 `"left"`, `"center"`, `"right"` 문자열로 변환)
5. **fill color 추출**: `shape.fill.type`이 solid이면 `shape.fill.fore_color.rgb`에서 추출
6. **bullet_list 판별**: 하나의 text_frame에 paragraph가 2개 이상이고, 각 paragraph의 텍스트가 짧은 경우(~200자 이하) → `"bullet_list"`로 변환. items는 각 paragraph의 text.
7. **element 순서**: 원본 PPTX의 shape 순서(z-order)를 유지한다.
8. **슬라이드 외부 요소**: `x + w > 13.33` 이거나 `y + h > 7.5` 이면 캔버스 내부로 clamp한다.

### 출력 예시

입력 PPTX에 10장이 있을 때 → index 2~7 (6장) 추출:

```json
[
  {
    "background": "#F8FAFC",
    "elements": [
      {"type": "shape", "shape_type": "rectangle", "x": 0.9, "y": 1.72, "w": 11.5, "h": 4.95, "fill_color": "#FFFFFF"},
      {"type": "text_box", "text": "슬라이드 제목", "x": 1.0, "y": 0.55, "w": 8.8, "h": 0.85, "font_name": "Malgun Gothic", "font_size": 28, "font_bold": true, "font_color": "#0F172A", "align": "left"},
      {"type": "bullet_list", "x": 1.25, "y": 2.1, "w": 7.2, "h": 3.8, "items": ["항목 1", "항목 2", "항목 3"], "bullet_char": "-", "bullet_color": "#2563EB", "font_name": "Malgun Gothic", "font_size": 16, "font_color": "#1E293B"},
      {"type": "shape", "shape_type": "rectangle", "x": 9.1, "y": 2.05, "w": 2.8, "h": 2.4, "fill_color": "#E8EEF9"},
      {"type": "text_box", "text": "하이라이트 텍스트", "x": 9.45, "y": 2.35, "w": 2.15, "h": 1.7, "font_name": "Malgun Gothic", "font_size": 15, "font_bold": true, "font_color": "#0F172A", "align": "left"}
    ]
  },
  {
    "background": "#F8FAFC",
    "elements": [
      {"type": "shape", "shape_type": "rectangle", "x": 0.9, "y": 1.85, "w": 5.45, "h": 4.55, "fill_color": "#FFFFFF"},
      {"type": "shape", "shape_type": "rectangle", "x": 6.75, "y": 1.85, "w": 5.45, "h": 4.55, "fill_color": "#E8EEF9"},
      {"type": "text_box", "text": "비교 제목", "x": 1.0, "y": 0.55, "w": 8.8, "h": 0.85, "font_name": "Malgun Gothic", "font_size": 28, "font_bold": true, "font_color": "#0F172A", "align": "left"},
      {"type": "bullet_list", "x": 1.2, "y": 2.2, "w": 4.85, "h": 3.7, "items": ["왼쪽 1", "왼쪽 2"], "bullet_char": "-", "bullet_color": "#2563EB", "font_size": 16, "font_color": "#1E293B"},
      {"type": "bullet_list", "x": 7.05, "y": 2.2, "w": 4.85, "h": 3.7, "items": ["오른쪽 1", "오른쪽 2"], "bullet_char": "-", "bullet_color": "#2563EB", "font_size": 16, "font_color": "#1E293B"}
    ]
  }
]
```

---

## TASK 2: 템플릿 업로드 API 엔드포인트 (추출 + 저장만)

### 파일: `app/routers/template.py` (NEW)

### 목적
사용자가 PPTX 파일을 업로드하면 JSON 템플릿으로 추출하여 `template/{title}.json` 파일로 저장한다.
**프로젝트 state에는 저장하지 않는다.** 템플릿 적용은 generate endpoint에서 template_name을 받아 처리한다.

### API 설계

```
POST /template/upload
  - Form field: file (PPTX 파일)
  - Form field: title (str) — 템플릿 이름. "template/{title}.json"으로 저장됨
  - 동작:
    1. TemplateExtractor로 PPTX → JSON 변환 (표지/목차/마지막2장 제외)
    2. template/{title}.json 파일로 저장
  - 응답: { "template_name": str, "template_path": str, "template": list[dict], "slide_count": int }

GET /template/{template_name}
  - 저장된 템플릿 JSON 조회

GET /template
  - 저장된 모든 템플릿 목록 반환
```

### 구현 코드 구조

```python
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile

from ..services.template_extractor import TemplateExtractor
from ..utils.file_loader import save_upload_file

router = APIRouter(tags=["template"])
_extractor = TemplateExtractor()

# 템플릿 저장 디렉토리 (프로젝트 root 기준)
_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "template"


def load_template(template_name: str) -> list[dict] | None:
    """템플릿 이름으로 JSON 파일을 로드한다. 없으면 None 반환."""
    template_path = _TEMPLATE_DIR / f"{template_name}.json"
    if not template_path.exists():
        return None
    return json.loads(template_path.read_text(encoding="utf-8"))


@router.post("/template/upload")
async def upload_template(
    file: UploadFile,
    title: str = Form(...),
    request: Request = ...,
):
    """
    PPTX 파일을 업로드하여 템플릿 JSON으로 추출하고 저장한다.
    
    - 표지(1장), 목차(1장), 마지막 2장을 제외한 콘텐츠 슬라이드만 추출
    - template/{title}.json 파일로 저장
    - 프로젝트 state에는 저장하지 않음 (적용은 generate 시 template_name으로)
    """
    # PPTX 파일을 임시 경로에 저장
    os.makedirs(_TEMPLATE_DIR, exist_ok=True)
    temp_path = _TEMPLATE_DIR / "_temp_upload.pptx"
    await save_upload_file(file, str(temp_path))
    
    # PPTX → JSON 추출
    try:
        template_data = _extractor.extract(str(temp_path))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PPTX 파싱 실패: {exc}")
    finally:
        if temp_path.exists():
            temp_path.unlink()  # 임시 파일 삭제
    
    if not template_data:
        raise HTTPException(status_code=400, detail="추출된 콘텐츠 슬라이드가 없습니다.")
    
    # template/{title}.json 저장
    safe_title = title.strip().replace("/", "_").replace("\\", "_")
    template_path = _TEMPLATE_DIR / f"{safe_title}.json"
    template_path.write_text(
        json.dumps(template_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    
    return {
        "template_name": safe_title,
        "template_path": str(template_path),
        "template": template_data,
        "slide_count": len(template_data),
    }


@router.get("/template/{template_name}")
async def get_template(template_name: str):
    """저장된 템플릿 JSON을 조회한다."""
    data = load_template(template_name)
    if data is None:
        raise HTTPException(status_code=404, detail=f"템플릿 '{template_name}'을 찾을 수 없습니다.")
    return {"template_name": template_name, "template": data, "slide_count": len(data)}


@router.get("/template")
async def list_templates():
    """저장된 모든 템플릿 목록을 반환한다."""
    if not _TEMPLATE_DIR.exists():
        return {"templates": []}
    templates = []
    for path in sorted(_TEMPLATE_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue  # 임시 파일 제외
        data = json.loads(path.read_text(encoding="utf-8"))
        templates.append({
            "template_name": path.stem,
            "slide_count": len(data),
        })
    return {"templates": templates}
```

### main.py 수정

```python
# 추가 import
from .routers.template import router as template_router

# router 등록 (기존 router들 뒤에 추가)
app.include_router(template_router)
```

---

## TASK 3: 2차 LLM 호출 — apply_template 메서드

### 파일: `app/services/llm_client.py` (MODIFY)

### 목적
LLM이 생성한 슬라이드 JSON과 **모든 템플릿 페이지**를 받아서:
1. 생성된 콘텐츠에 가장 어울리는 템플릿 페이지를 **선택**
2. 선택한 템플릿의 레이아웃(좌표, 스타일, element 구성)을 유지하면서 콘텐츠를 채워 넣은 최종 JSON을 반환

### 프롬프트 설계

```python
_APPLY_TEMPLATE_PROMPT = """
You select the best matching template and merge generated slide content into it.
Return valid JSON only.

You are given two JSON inputs:
1) Generated Slide: contains the content (text, bullets, etc.) produced by a previous LLM step.
2) Template Pages: a list of available template page layouts extracted from an existing PPTX file.
   Each template page defines a different layout with different numbers of elements, positions, and styles.

Your task:
Step 1 - SELECT the best template:
- Examine the Generated Slide's content structure (number of text items, number of bullet lists, content density).
- Compare with each Template Page's element structure (how many text_box, bullet_list, shape elements it has).
- Choose the Template Page whose structure best matches the Generated Slide's content.
- Consider: a slide with many bullet points fits a template with bullet_list elements; a slide with a title + body fits a simpler template; a comparison slide fits a template with two columns.

Step 2 - FILL the selected template:
- Use the selected Template Page's elements structure as-is (same number of elements, same types, same order).
- For each "text_box" element in the Template, replace its "text" field with appropriate content from the Generated Slide.
- For each "bullet_list" element in the Template, replace its "items" field with appropriate content from the Generated Slide.
- For each "shape" element in the Template, keep it completely unchanged (these are decorative).
- NEVER change x, y, w, h coordinates.
- NEVER change font_size, font_color, font_bold, font_name, fill_color, bullet_color, bullet_char, align, shape_type.
- ONLY change "text" fields in text_box elements and "items" fields in bullet_list elements.
- If the Generated Slide has more content than the Template can hold, summarize or merge content to fit.
- If the Generated Slide has less content, use what is available. Do not invent new content.
- Keep the "background" from the selected Template Page.

Response schema:
{{
  "selected_template_index": 0,
  "title": "string",
  "theme": "clean_light|bold_dark|editorial",
  "slide_variant": "{canonical_slide_variants}",
  "pages": [
    {{
      "background": "#RRGGBB",
      "elements": [... same structure as selected Template Page's elements but with filled content ...]
    }}
  ]
}}

Generated Slide:
{generated_slide_json}

Template Pages (choose the best one by index):
{template_pages_json}

Write in {language}.
"""
```

### abstract 메서드 추가 (LLMClient 클래스)

```python
class LLMClient(ABC):
    # ... 기존 메서드들 ...

    @abstractmethod
    async def apply_template(
        self,
        generated_slide: dict[str, Any],
        template_pages: list[dict[str, Any]],
        language: str,
        request_label: str = "",
    ) -> dict[str, Any]:
        """
        generated_slide: 1차 LLM이 생성한 SlideContent dict
        template_pages: 모든 템플릿 페이지 리스트 (각 페이지는 {background, elements})
        language: 언어 코드
        
        Returns: 템플릿이 적용된 SlideContent dict
        """
        raise NotImplementedError
```

### OpenAICompatibleLLMClient 구현

```python
async def apply_template(
    self,
    generated_slide: dict[str, Any],
    template_pages: list[dict[str, Any]],
    language: str,
    request_label: str = "",
) -> dict[str, Any]:
    prompt = _APPLY_TEMPLATE_PROMPT.format(
        generated_slide_json=json.dumps(generated_slide, ensure_ascii=False),
        template_pages_json=json.dumps(template_pages, ensure_ascii=False),
        language=language,
        canonical_slide_variants=_CANONICAL_SLIDE_VARIANTS,
    )
    result = _parse_json(
        await self._call_with_logging(prompt, request_label, "apply_template")
    )
    # selected_template_index는 로깅용, SlideContent에는 불필요하므로 제거
    result.pop("selected_template_index", None)
    return result
```

---

## TASK 4: generate endpoint 수정 — 생성 단계와 template 후처리 단계 분리

### 파일: `app/schemas/generate.py` (MODIFY)

`GenerateSlidesRequest`와 `GenerateAllRequest`에 optional `template_name` 필드를 추가한다.

```python
# 기존
class GenerateSlidesRequest(BaseModel):
    project_id: int

class GenerateAllRequest(BaseModel):
    project_id: int

# 변경 후
class GenerateSlidesRequest(BaseModel):
    project_id: int
    template_name: str | None = None  # 템플릿 이름 (없으면 템플릿 미적용)

class GenerateAllRequest(BaseModel):
    project_id: int
    template_name: str | None = None  # 템플릿 이름 (없으면 템플릿 미적용)
```

### 파일: `app/routers/generate.py` (MODIFY)

generate endpoint는 더 이상 템플릿을 미리 로드해서 `generate_slides()` 안으로 넘기지 않는다.
반드시 아래 순서를 지킨다:

1. 먼저 `generate_slides()`로 **모든 content slide JSON을 생성**
2. 그 다음 `add_just_template()`를 별도로 호출
3. `template_name`이 비어 있으면 `add_just_template()`는 즉시 return
4. `template_name`이 있는데 파일이 없으면 error

```python
@router.post("/generate/slides", response_model=GenerateSlidesResponse)
async def generate_slides(req: GenerateSlidesRequest, request: Request) -> GenerateSlidesResponse:
    repo = request.app.state.project_repository
    slide_generator = request.app.state.slide_generator

    state: ProjectState | None = await repo.get(req.project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")

    try:
        slides = await slide_generator.generate_slides(state)
        slides = await slide_generator.add_just_template(state, slides, req.template_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"템플릿 '{req.template_name}'을 찾을 수 없습니다.")
    except ValueError as exc:
        state.touch()
        await repo.upsert(state)
        raise HTTPException(status_code=400, detail=str(exc))
    state.slides = slides
    state.touch()
    await repo.upsert(state)
    return GenerateSlidesResponse(project_id=state.project_id, slides=slides)


# generate_all도 동일하게 수정
@router.post("/generate/all", response_model=GenerateAllResponse)
async def generate_all(req: GenerateAllRequest, request: Request) -> GenerateAllResponse:
    repo = request.app.state.project_repository
    outline_generator = request.app.state.outline_generator
    slide_generator = request.app.state.slide_generator
    notes_generator = request.app.state.notes_generator

    state: ProjectState | None = await repo.get(req.project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")

    outline_result = await outline_generator.generate_outline(state)
    state.title = outline_result.title
    state.outline = outline_result.outline
    state.metadata["presentation_goal"] = f"문서 '{state.title}'의 핵심 내용을 청중이 이해하기 쉽게 발표 자료로 구성한다."

    try:
        slides = await slide_generator.generate_slides(state)
        slides = await slide_generator.add_just_template(state, slides, req.template_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"템플릿 '{req.template_name}'을 찾을 수 없습니다.")
    except ValueError as exc:
        state.touch()
        await repo.upsert(state)
        raise HTTPException(status_code=400, detail=str(exc))
    state.slides = slides

    notes = await notes_generator.generate_notes(state)
    state.notes = notes

    state.touch()
    await repo.upsert(state)
    return GenerateAllResponse(
        project_id=state.project_id,
        title=state.title,
        outline=state.outline,
        slides=slides,
        notes=notes,
        stats={},
    )
```

---

## TASK 5: slide_generator.py 수정 — 생성 단계와 템플릿 단계 완전 분리

### 파일: `app/services/slide_generator.py` (MODIFY)

### 변경 내용

`generate_slides()` 메서드는 **오직 1차 LLM 생성만 담당**한다.
템플릿 적용은 절대 같은 `for` 루프에서 하지 않는다.

새로운 후처리 메서드 `add_just_template()`를 추가해서:

1. `template_name`이 `None` 또는 빈 문자열이면 즉시 `return`
2. 값이 있으면 템플릿 파일을 로드
3. 존재하지 않으면 error
4. 모든 content slide에 대해 **모든 템플릿 페이지**를 넘겨 `apply_template()` 호출

즉, 흐름은 다음 두 단계로 고정한다:

- 1단계: `for each slide -> generate_slide()`
- 2단계: `add_just_template(template_name)` 내부에서 `for each slide -> apply_template()`

### 변경 후 코드 구조

```python
from ..services.template_store import load_template, sanitize_template_name


class SlideGenerator:
    ...

    async def generate_slides(self, state: ProjectState) -> list[SlideContent]:
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

        return [SlideContent.model_validate(slide) for slide in raw_slides]

    async def add_just_template(
        self,
        state: ProjectState,
        slides: list[SlideContent],
        template_name: str | None,
    ) -> list[SlideContent]:
        if template_name is None or not template_name.strip():
            return slides

        template_pages = load_template(sanitize_template_name(template_name))
        raw_slides = [slide.model_dump() for slide in slides]

        # title / closing 슬라이드는 템플릿 적용 대상이 아님
        for index in range(1, len(raw_slides) - 1):
            slide_title = str(raw_slides[index].get("title", ""))
            raw_slides[index] = await self._llm_client.apply_template(
                generated_slide=raw_slides[index],
                template_pages=template_pages,
                language=state.language,
                request_label=f"apply_template slide {index} project {state.project_id}: {slide_title}",
            )

        return [SlideContent.model_validate(slide) for slide in raw_slides]
```

### 분리 이유

- `previous_slide_summary`가 템플릿 보정 결과에 오염되지 않고, **순수 생성 결과 기준**으로 유지된다.
- 기존 `generate_slide()` 루프를 거의 그대로 보존할 수 있다.
- 템플릿 단계만 독립적으로 on/off 가능하다.

### 주의: title/closing 슬라이드에는 템플릿 적용하지 않음

템플릿에서 표지/목차/마지막 2장을 이미 제외했으므로, `_build_title_slide()`과 `_build_closing_slide()`에는 템플릿을 적용하지 않는다.
이들은 기존 하드코딩 레이아웃을 그대로 사용한다.

---

## TASK 6: regeneration_service.py 수정

### 파일: `app/services/regeneration_service.py` (MODIFY)

`regenerate_slide()` 에서도 같은 원칙을 적용한다.
즉, **재생성 1단계**와 **템플릿 후처리 2단계**를 분리한다.

- 1단계: `generate_slide()` 또는 `regenerate_slide()`로 raw slide 생성
- 2단계: `template_name`이 있을 때만 모든 template pages를 넘겨 `apply_template()` 실행
- `template_name`이 비어 있으면 즉시 return
- `template_name`이 있는데 template 파일이 없으면 error

```python
normalized = _normalize_slide(raw, slide_info)
updated = SlideContent.model_validate(normalized)

if template_name and template_name.strip():
    template_pages = load_template(sanitize_template_name(template_name))
    updated = SlideContent.model_validate(
        await self._llm_client.apply_template(
            generated_slide=updated.model_dump(),
            template_pages=template_pages,
            language=state.language,
            request_label=f"apply_template regenerate slide {idx + 1} project {state.project_id}: {slide_title}",
        )
    )
```

### 파일: `app/routers/regenerate.py` (MODIFY)

regenerate endpoint의 Request에도 optional `template_name` 추가:

```python
# regenerate slide request에 template_name 추가
class RegenerateSlideRequest(BaseModel):
    project_id: int
    slide_title: str
    user_request: str = ""
    template_name: str | None = None  # 템플릿 이름

# endpoint는 template_name만 service에 전달하고,
# 실제 로드/적용은 재생성 2단계에서 처리
slide = await regeneration_service.regenerate_slide(
    state,
    slide_title=req.slide_title,
    user_request=req.user_request,
    template_name=req.template_name,
)
```

---

## 구현 순서 요약

| 순서 | TASK | 파일 | 유형 |
|------|------|------|------|
| 1 | PPTX → JSON 추출 (콘텐츠 슬라이드만) | `app/services/template_extractor.py` | NEW |
| 2 | 템플릿 업로드/조회 API (추출+저장만) | `app/routers/template.py` | NEW |
| 3 | main.py에 router 등록 | `app/main.py` | MODIFY |
| 4 | generate endpoint를 2단계 호출 구조로 수정 | `app/schemas/generate.py`, `app/routers/generate.py` | MODIFY |
| 5 | apply_template 프롬프트 + 실제 LLM 메서드만 유지 | `app/services/llm_client.py` | MODIFY |
| 6 | `generate_slides()`와 `add_just_template()` 분리 | `app/services/slide_generator.py` | MODIFY |
| 7 | regeneration도 동일한 2단계 구조로 통합 | `app/services/regeneration_service.py`, `app/routers/regenerate.py` | MODIFY |

## 핵심 흐름 정리

```
1. POST /template/upload (file + title)
   → PPTX에서 콘텐츠 슬라이드 추출 → template/{title}.json 저장
   → 프로젝트 state에는 저장하지 않음

2. POST /generate/slides (project_id + template_name?)
   → 먼저 slide_generator.generate_slides()로 모든 content slide 생성
   → 그 다음 slide_generator.add_just_template(template_name) 실행
   → template_name이 없으면 add_just_template() 즉시 return
   → template_name이 있는데 파일이 없으면 error
   → template_name이 있으면 각 content slide마다 모든 템플릿 페이지를 넘겨 2차 LLM(apply_template) 실행

3. POST /regenerate/slide (project_id + slide_title + template_name?)
   → 먼저 재생성 1단계 수행
   → 그 다음 template_name이 있으면 2차 LLM(apply_template) 수행
```

## 주의사항

1. **기존 기능 보존**: `template_name`이 없으면 기존 동작과 100% 동일해야 한다.
2. **EMU → Inches 변환**: python-pptx의 모든 좌표는 EMU. `round(Emu(value).inches, 2)`로 변환.
3. **bullet_list items 제한**: 추출 시에도 `items`는 최대 5개. 초과 시 앞 5개만.
4. **SlideContent validation**: `apply_template` 출력도 `SlideContent.model_validate()` 통과해야 한다. `selected_template_index` 필드는 SlideContent에 없으므로 pop 해야 한다.
5. **python-pptx는 이미 requirements.txt에 포함**: `python-pptx>=1.0.2`
6. **`_CANONICAL_SLIDE_VARIANTS`**: `"title_page|content_box_list|content_two_panel|content_sidebar|content_split_band|content_compact|closing_page"`
7. **template 디렉토리**: 프로젝트 root (`fastapi-app/template/`)에 자동 생성.
8. **슬라이드 필터링**: PPTX 5장 미만이면 필터링 없이 전체 추출.
9. **title/closing 슬라이드**: 템플릿 적용 대상이 아님 (기존 하드코딩 유지).
10. **템플릿 적용 함수 분리**: `generate_slides()` 안에서 `apply_template()`를 직접 호출하지 않는다.
11. **template_name 처리 규칙**: `None`/빈 문자열이면 skip, 값이 있는데 파일이 없으면 error.

## 기존 파일 참조 경로 (절대 경로)

- `app/services/llm_client.py` — LLM 클라이언트 (모든 LLM 호출 메서드 정의)
- `app/services/slide_generator.py` — 슬라이드 생성 파이프라인
- `app/services/pptx_service.py` — PPTX 렌더링 (elements → 실제 PPTX)
- `app/services/regeneration_service.py` — 슬라이드/노트 재생성
- `app/schemas/generate.py` — Pydantic 모델 (SlideContent, PageLayout, elements, Request/Response)
- `app/models/project_state.py` — ProjectState 모델
- `app/routers/generate.py` — 생성 API 엔드포인트
- `app/routers/regenerate.py` — 재생성 API 엔드포인트
- `app/routers/ingest.py` — 문서 업로드 API (참고용)
- `app/main.py` — FastAPI 앱 진입점 (라우터 등록)
- `app/core/config.py` — 설정
- `elements.json` — elements 프롬프트 컨트랙트 (프로젝트 root)
