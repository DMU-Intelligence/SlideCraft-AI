from __future__ import annotations

import io
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from ..models.project_state import ProjectState
from ..schemas.generate import (
    BulletListElement,
    PageLayout,
    ShapeElement,
    SlideContent,
    SlideElement,
    TextBoxElement,
)

SLIDE_WIDTH = Inches(13.33)
SLIDE_HEIGHT = Inches(7.5)

_ALIGN_MAP: dict[str, Any] = {
    "left": PP_ALIGN.LEFT,
    "center": PP_ALIGN.CENTER,
    "right": PP_ALIGN.RIGHT,
}

_THEMES: dict[str, dict[str, str | int]] = {
    "clean_light": {
        "background": "#F8FAFC",
        "accent": "#2563EB",
        "text": "#0F172A",
        "muted": "#475569",
        "panel": "#FFFFFF",
        "panel_text": "#0F172A",
        "title_size": 28,
        "body_size": 16,
    },
    "bold_dark": {
        "background": "#0F172A",
        "accent": "#5B8DEF",
        "text": "#F8FAFC",
        "muted": "#CBD5E1",
        "panel": "#1E293B",
        "panel_text": "#F8FAFC",
        "title_size": 30,
        "body_size": 16,
    },
    "editorial": {
        "background": "#FFFDF8",
        "accent": "#B45309",
        "text": "#292524",
        "muted": "#57534E",
        "panel": "#F5F5F4",
        "panel_text": "#292524",
        "title_size": 28,
        "body_size": 16,
    },
}


def _hex_to_rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        h = "FFFFFF"
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _set_bg(slide: Any, hex_color: str) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = _hex_to_rgb(hex_color)


def _add_text_box(
    slide: Any,
    *,
    text: str,
    left: float,
    top: float,
    width: float,
    height: float,
    font_size: int,
    font_color: str,
    bold: bool = False,
    align: str = "left",
    font_name: str = "Malgun Gothic",
    vertical_anchor: MSO_ANCHOR = MSO_ANCHOR.TOP,
) -> None:
    if not text.strip():
        return
    text_box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = text_box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = vertical_anchor
    paragraph = frame.paragraphs[0]
    paragraph.alignment = _ALIGN_MAP.get(align, PP_ALIGN.LEFT)
    run = paragraph.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = _hex_to_rgb(font_color)


def _add_panel(
    slide: Any,
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    fill_color: str,
    radius: bool = True,
) -> None:
    shape_type = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    shape = slide.shapes.add_shape(
        shape_type,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = _hex_to_rgb(fill_color)
    shape.line.fill.background()


def _render_text_box(slide: Any, elem: TextBoxElement) -> None:
    _add_text_box(
        slide,
        text=elem.text,
        left=elem.left,
        top=elem.top,
        width=elem.width,
        height=elem.height,
        font_size=elem.font_size,
        font_color=elem.font_color,
        bold=elem.font_bold,
        align=elem.align,
        font_name=elem.font_name,
    )


def _render_shape(slide: Any, elem: ShapeElement) -> None:
    _add_panel(
        slide,
        left=elem.left,
        top=elem.top,
        width=elem.width,
        height=elem.height,
        fill_color=elem.fill_color,
        radius=elem.shape_type != "rectangle",
    )


def _render_bullet_list(slide: Any, elem: BulletListElement) -> None:
    text_box = slide.shapes.add_textbox(Inches(elem.left), Inches(elem.top), Inches(elem.width), Inches(elem.height))
    frame = text_box.text_frame
    frame.word_wrap = True
    bullet_rgb = _hex_to_rgb(elem.bullet_color)
    font_rgb = _hex_to_rgb(elem.font_color)

    for index, item_text in enumerate(elem.items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.space_before = Pt(4)
        paragraph.space_after = Pt(3)

        bullet = paragraph.add_run()
        bullet.text = f"{elem.bullet_char}  "
        bullet.font.name = elem.font_name
        bullet.font.size = Pt(elem.font_size)
        bullet.font.color.rgb = bullet_rgb
        bullet.font.bold = True

        body = paragraph.add_run()
        body.text = item_text
        body.font.name = elem.font_name
        body.font.size = Pt(elem.font_size)
        body.font.color.rgb = font_rgb


def _render_element(slide: Any, element: SlideElement) -> None:
    if isinstance(element, TextBoxElement):
        _render_text_box(slide, element)
    elif isinstance(element, ShapeElement):
        _render_shape(slide, element)
    elif isinstance(element, BulletListElement):
        _render_bullet_list(slide, element)


def _coerce_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _render_slot_bullets(
    slide: Any,
    items: list[str],
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    theme: dict[str, str | int],
) -> None:
    if not items:
        return
    _render_bullet_list(
        slide,
        BulletListElement(
            left=left,
            top=top,
            width=width,
            height=height,
            items=items[:5],
            bullet_char="•",
            bullet_color=str(theme["accent"]),
            font_color=str(theme["text"]),
            font_size=int(theme["body_size"]),
        ),
    )


def _render_title_variant(slide: Any, slots: dict[str, Any], theme: dict[str, str | int]) -> None:
    _add_panel(slide, left=0.65, top=0.5, width=12.0, height=6.0, fill_color=str(theme["panel"]))
    _add_panel(slide, left=0.65, top=0.5, width=0.16, height=6.0, fill_color=str(theme["accent"]), radius=False)
    _add_text_box(
        slide,
        text=str(slots.get("eyebrow", "")),
        left=1.1,
        top=1.0,
        width=8.5,
        height=0.5,
        font_size=14,
        font_color=str(theme["accent"]),
        bold=True,
    )
    _add_text_box(
        slide,
        text=str(slots.get("headline", "")),
        left=1.1,
        top=1.6,
        width=9.5,
        height=1.6,
        font_size=int(theme["title_size"]) + 6,
        font_color=str(theme["text"]),
        bold=True,
    )
    _add_text_box(
        slide,
        text=str(slots.get("body", "")),
        left=1.1,
        top=3.45,
        width=8.8,
        height=1.1,
        font_size=int(theme["body_size"]) + 1,
        font_color=str(theme["muted"]),
    )
    highlight = str(slots.get("highlight", ""))
    if highlight:
        _add_panel(slide, left=9.95, top=1.55, width=2.1, height=2.1, fill_color=str(theme["accent"]))
        _add_text_box(
            slide,
            text=highlight,
            left=10.2,
            top=1.85,
            width=1.6,
            height=1.5,
            font_size=14,
            font_color="#FFFFFF",
            bold=True,
            align="center",
            vertical_anchor=MSO_ANCHOR.MIDDLE,
        )


def _render_section_variant(slide: Any, slots: dict[str, Any], theme: dict[str, str | int]) -> None:
    _add_panel(slide, left=0.75, top=0.7, width=11.8, height=0.12, fill_color=str(theme["accent"]), radius=False)
    _add_text_box(
        slide,
        text=str(slots.get("eyebrow", "")),
        left=0.95,
        top=0.95,
        width=3.0,
        height=0.4,
        font_size=12,
        font_color=str(theme["accent"]),
        bold=True,
    )
    _add_text_box(
        slide,
        text=str(slots.get("headline", "")),
        left=0.95,
        top=1.35,
        width=11.0,
        height=0.8,
        font_size=int(theme["title_size"]),
        font_color=str(theme["text"]),
        bold=True,
    )
    _add_text_box(
        slide,
        text=str(slots.get("body", "")),
        left=0.95,
        top=2.15,
        width=10.8,
        height=0.8,
        font_size=int(theme["body_size"]),
        font_color=str(theme["muted"]),
    )
    _render_slot_bullets(
        slide,
        _coerce_list(slots.get("bullets")),
        left=0.95,
        top=3.0,
        width=10.2,
        height=2.6,
        theme=theme,
    )
    if str(slots.get("highlight", "")).strip():
        _add_panel(slide, left=10.6, top=3.0, width=1.9, height=2.1, fill_color=str(theme["panel"]))
        _add_text_box(
            slide,
            text=str(slots.get("highlight", "")),
            left=10.85,
            top=3.25,
            width=1.4,
            height=1.6,
            font_size=13,
            font_color=str(theme["panel_text"]),
            bold=True,
            align="center",
            vertical_anchor=MSO_ANCHOR.MIDDLE,
        )


def _render_summary_variant(slide: Any, slots: dict[str, Any], theme: dict[str, str | int]) -> None:
    _add_text_box(
        slide,
        text=str(slots.get("headline", "")),
        left=0.85,
        top=0.8,
        width=8.8,
        height=0.9,
        font_size=int(theme["title_size"]),
        font_color=str(theme["text"]),
        bold=True,
    )
    _add_panel(slide, left=0.85, top=1.95, width=8.1, height=4.2, fill_color=str(theme["panel"]))
    _render_slot_bullets(
        slide,
        _coerce_list(slots.get("bullets")),
        left=1.15,
        top=2.35,
        width=7.5,
        height=3.2,
        theme=theme,
    )
    _add_panel(slide, left=9.35, top=1.95, width=2.8, height=4.2, fill_color=str(theme["accent"]))
    _add_text_box(
        slide,
        text=str(slots.get("highlight", "")) or str(slots.get("body", "")),
        left=9.7,
        top=2.35,
        width=2.1,
        height=3.0,
        font_size=16,
        font_color="#FFFFFF",
        bold=True,
        vertical_anchor=MSO_ANCHOR.MIDDLE,
    )


def _render_two_column_variant(slide: Any, slots: dict[str, Any], theme: dict[str, str | int]) -> None:
    _add_text_box(
        slide,
        text=str(slots.get("eyebrow", "")),
        left=0.85,
        top=0.8,
        width=4.5,
        height=0.35,
        font_size=12,
        font_color=str(theme["accent"]),
        bold=True,
    )
    _add_text_box(
        slide,
        text=str(slots.get("headline", "")),
        left=0.85,
        top=1.15,
        width=11.2,
        height=0.8,
        font_size=int(theme["title_size"]),
        font_color=str(theme["text"]),
        bold=True,
    )
    _add_panel(slide, left=0.85, top=2.2, width=5.65, height=3.9, fill_color=str(theme["panel"]))
    _add_panel(slide, left=6.8, top=2.2, width=5.65, height=3.9, fill_color=str(theme["panel"]))
    _render_slot_bullets(
        slide,
        _coerce_list(slots.get("left_points")),
        left=1.15,
        top=2.55,
        width=5.0,
        height=3.1,
        theme=theme,
    )
    _render_slot_bullets(
        slide,
        _coerce_list(slots.get("right_points")),
        left=7.1,
        top=2.55,
        width=5.0,
        height=3.1,
        theme=theme,
    )
    _add_text_box(
        slide,
        text=str(slots.get("body", "")),
        left=0.85,
        top=6.35,
        width=9.2,
        height=0.45,
        font_size=int(theme["body_size"]) - 1,
        font_color=str(theme["muted"]),
    )


def _render_slots(slide: Any, slide_content: SlideContent, page: PageLayout) -> None:
    theme = _THEMES.get(slide_content.theme, _THEMES["clean_light"])
    slots = page.slots
    if not slots:
        return

    background = page.background or str(theme["background"])
    _set_bg(slide, background)

    variant = slide_content.slide_variant
    if variant == "title":
        _render_title_variant(slide, slots, theme)
    elif variant == "section":
        _render_section_variant(slide, slots, theme)
    elif variant == "two_column":
        _render_two_column_variant(slide, slots, theme)
    else:
        _render_summary_variant(slide, slots, theme)


def _build_page(prs: Presentation, slide_content: SlideContent, page: PageLayout) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    theme = _THEMES.get(slide_content.theme, _THEMES["clean_light"])
    _set_bg(slide, page.background or str(theme["background"]))

    if page.slots:
        _render_slots(slide, slide_content, page)
    else:
        for element in page.elements:
            _render_element(slide, element)


class PptxGenerator:
    def generate(self, state: ProjectState) -> bytes:
        prs = Presentation()
        prs.slide_width = SLIDE_WIDTH
        prs.slide_height = SLIDE_HEIGHT

        for slide_content in state.slides:
            for page in slide_content.pages:
                _build_page(prs, slide_content, page)

        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)
        return buf.read()
