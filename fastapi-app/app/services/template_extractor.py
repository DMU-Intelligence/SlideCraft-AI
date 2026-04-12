from __future__ import annotations

from typing import Any

from pptx import Presentation
from pptx.enum.dml import MSO_FILL
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu

from ..schemas.generate import PageLayout, SLIDE_HEIGHT_INCHES, SLIDE_WIDTH_INCHES

_DEFAULT_BACKGROUND = "#FFFFFF"
_DEFAULT_FONT_NAME = "Malgun Gothic"
_DEFAULT_FONT_SIZE = 16
_DEFAULT_FONT_COLOR = "#000000"
_DEFAULT_BULLET_COLOR = "#2563EB"


def _rgb_to_hex(rgb: Any) -> str | None:
    if rgb is None:
        return None
    try:
        return f"#{int(rgb[0]):02X}{int(rgb[1]):02X}{int(rgb[2]):02X}"
    except Exception:
        text = str(rgb).strip()
        if len(text) == 6:
            return f"#{text.upper()}"
    return None


def _emu_to_inches(value: int) -> float:
    return round(Emu(value).inches, 2)


def _clamp_dimension(start: float, size: float, limit: float) -> tuple[float, float] | None:
    clamped_start = round(max(0.0, min(start, limit)), 2)
    if clamped_start >= limit:
        return None

    clamped_size = round(max(0.01, size), 2)
    if clamped_start + clamped_size > limit:
        clamped_size = round(limit - clamped_start, 2)
    if clamped_size <= 0:
        return None
    return clamped_start, clamped_size


class TemplateExtractor:
    """PPTX 파일에서 콘텐츠 슬라이드의 elements JSON을 추출한다."""

    def extract(self, pptx_path: str) -> list[dict[str, Any]]:
        prs = Presentation(pptx_path)
        all_slides = list(prs.slides)

        if len(all_slides) >= 5:
            content_slides = all_slides[2:-2]
        else:
            content_slides = all_slides

        result: list[dict[str, Any]] = []
        for slide in content_slides:
            page_data = self._extract_slide(slide)
            if page_data["elements"]:
                result.append(page_data)
        return result

    def _extract_slide(self, slide: Any) -> dict[str, Any]:
        page_data: dict[str, Any] = {
            "background": self._extract_background(slide),
            "elements": [],
        }

        for shape in slide.shapes:
            page_data["elements"].extend(self._extract_shape_element(shape))

        if not page_data["elements"]:
            return page_data

        return PageLayout.model_validate(page_data).model_dump(exclude={"slots"}, exclude_none=True)

    def _extract_background(self, slide: Any) -> str:
        fill = slide.background.fill
        if fill is not None and fill.type == MSO_FILL.SOLID:
            color = _rgb_to_hex(getattr(fill.fore_color, "rgb", None))
            if color:
                return color
        return _DEFAULT_BACKGROUND

    def _extract_shape_element(self, shape: Any) -> list[dict[str, Any]]:
        shape_type = shape.shape_type

        if shape_type in {
            MSO_SHAPE_TYPE.PICTURE,
            MSO_SHAPE_TYPE.TABLE,
            MSO_SHAPE_TYPE.GROUP,
            MSO_SHAPE_TYPE.CHART,
            MSO_SHAPE_TYPE.MEDIA,
            MSO_SHAPE_TYPE.DIAGRAM,
            MSO_SHAPE_TYPE.CANVAS,
        }:
            return []

        if shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE:
            return self._extract_auto_shape(shape)

        if shape_type == MSO_SHAPE_TYPE.TEXT_BOX:
            return self._extract_text_only_shape(shape)

        if shape_type == MSO_SHAPE_TYPE.PLACEHOLDER:
            return self._extract_text_only_shape(shape)

        return []

    def _extract_auto_shape(self, shape: Any) -> list[dict[str, Any]]:
        elements: list[dict[str, Any]] = []
        fill_color = self._extract_fill_color(shape)
        text_payload = self._extract_text_payload(shape)

        if not text_payload:
            shape_element = self._build_shape_element(shape, fill_color or _DEFAULT_BACKGROUND)
            return [shape_element] if shape_element else []

        shape_element = self._build_shape_element(shape, fill_color) if fill_color else None
        if shape_element:
            elements.append(shape_element)
        elements.append(text_payload)
        return elements

    def _extract_text_only_shape(self, shape: Any) -> list[dict[str, Any]]:
        text_payload = self._extract_text_payload(shape)
        return [text_payload] if text_payload else []

    def _extract_text_payload(self, shape: Any) -> dict[str, Any] | None:
        if not getattr(shape, "has_text_frame", False):
            return None

        text_frame = shape.text_frame
        paragraphs = self._text_paragraphs(text_frame)
        if not paragraphs:
            return None

        if self._is_bullet_list(paragraphs):
            return self._build_bullet_list_element(shape, paragraphs)
        return self._build_text_box_element(shape, "\n".join(paragraphs), text_frame)

    def _build_shape_element(self, shape: Any, fill_color: str | None) -> dict[str, Any] | None:
        bounds = self._extract_bounds(shape)
        if bounds is None:
            return None

        shape_type = "rectangle"
        if getattr(shape, "auto_shape_type", None) == MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE:
            shape_type = "round_rectangle"

        return {
            "type": "shape",
            "shape_type": shape_type,
            **bounds,
            "fill_color": fill_color or _DEFAULT_BACKGROUND,
        }

    def _build_text_box_element(self, shape: Any, text: str, text_frame: Any) -> dict[str, Any] | None:
        bounds = self._extract_bounds(shape)
        if bounds is None:
            return None

        font_data = self._extract_font_data(text_frame)
        return {
            "type": "text_box",
            **bounds,
            "text": text.strip(),
            **font_data,
        }

    def _build_bullet_list_element(self, shape: Any, paragraphs: list[str]) -> dict[str, Any] | None:
        bounds = self._extract_bounds(shape)
        if bounds is None:
            return None

        text_frame = shape.text_frame
        font_data = self._extract_font_data(text_frame)
        return {
            "type": "bullet_list",
            **bounds,
            "items": paragraphs[:5],
            "bullet_char": "-",
            "bullet_color": _DEFAULT_BULLET_COLOR,
            "font_name": font_data["font_name"],
            "font_size": font_data["font_size"],
            "font_color": font_data["font_color"],
        }

    def _extract_bounds(self, shape: Any) -> dict[str, float] | None:
        x = _emu_to_inches(shape.left)
        y = _emu_to_inches(shape.top)
        w = _emu_to_inches(shape.width)
        h = _emu_to_inches(shape.height)

        clamped_x = _clamp_dimension(x, w, SLIDE_WIDTH_INCHES)
        clamped_y = _clamp_dimension(y, h, SLIDE_HEIGHT_INCHES)
        if clamped_x is None or clamped_y is None:
            return None

        return {
            "x": clamped_x[0],
            "y": clamped_y[0],
            "w": clamped_x[1],
            "h": clamped_y[1],
        }

    def _extract_fill_color(self, shape: Any) -> str | None:
        fill = getattr(shape, "fill", None)
        if fill is None or fill.type != MSO_FILL.SOLID:
            return None
        return _rgb_to_hex(getattr(fill.fore_color, "rgb", None))

    def _extract_font_data(self, text_frame: Any) -> dict[str, Any]:
        paragraph, run = self._find_first_text_run(text_frame)
        font = run.font if run is not None else getattr(paragraph, "font", None)

        font_name = getattr(font, "name", None) or _DEFAULT_FONT_NAME
        font_size = getattr(font, "size", None)
        font_size_value = int(round(font_size.pt)) if font_size is not None else _DEFAULT_FONT_SIZE
        font_bold = bool(getattr(font, "bold", False))
        font_color = _rgb_to_hex(getattr(getattr(font, "color", None), "rgb", None)) or _DEFAULT_FONT_COLOR
        alignment = self._extract_alignment(paragraph)

        return {
            "font_name": font_name,
            "font_size": font_size_value,
            "font_bold": font_bold,
            "font_color": font_color,
            "align": alignment,
        }

    def _find_first_text_run(self, text_frame: Any) -> tuple[Any, Any | None]:
        for paragraph in text_frame.paragraphs:
            paragraph_text = (paragraph.text or "").strip()
            if paragraph.runs:
                for run in paragraph.runs:
                    if (run.text or "").strip():
                        return paragraph, run
            if paragraph_text:
                return paragraph, None
        return text_frame.paragraphs[0], None

    def _extract_alignment(self, paragraph: Any) -> str:
        alignment = getattr(paragraph, "alignment", None)
        if alignment == PP_ALIGN.CENTER:
            return "center"
        if alignment == PP_ALIGN.RIGHT:
            return "right"
        return "left"

    def _text_paragraphs(self, text_frame: Any) -> list[str]:
        return [
            text
            for text in ((paragraph.text or "").strip() for paragraph in text_frame.paragraphs)
            if text
        ]

    def _is_bullet_list(self, paragraphs: list[str]) -> bool:
        return len(paragraphs) >= 2 and all(len(text) <= 200 for text in paragraphs)
