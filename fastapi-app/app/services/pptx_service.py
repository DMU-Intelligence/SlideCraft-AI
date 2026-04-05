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
        "background": "#F7F8FC",
        "accent": "#2563EB",
        "text": "#0F172A",
        "muted": "#475569",
        "panel": "#FFFFFF",
        "soft_panel": "#E8EEF9",
        "inverse_text": "#FFFFFF",
        "title_size": 27,
        "body_size": 16,
    },
    "bold_dark": {
        "background": "#0F172A",
        "accent": "#7AA2FF",
        "text": "#F8FAFC",
        "muted": "#CBD5E1",
        "panel": "#162235",
        "soft_panel": "#1E2F47",
        "inverse_text": "#FFFFFF",
        "title_size": 28,
        "body_size": 16,
    },
    "editorial": {
        "background": "#FFFDF8",
        "accent": "#B45309",
        "text": "#292524",
        "muted": "#57534E",
        "panel": "#F7F1E8",
        "soft_panel": "#EADBC8",
        "inverse_text": "#FFFFFF",
        "title_size": 27,
        "body_size": 16,
    },
}


def _hex_to_rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        h = "FFFFFF"
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _theme_for(name: str) -> dict[str, str | int]:
    return _THEMES.get(name, _THEMES["clean_light"])


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
    if not str(text).strip():
        return
    text_box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = text_box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = vertical_anchor
    paragraph = frame.paragraphs[0]
    paragraph.alignment = _ALIGN_MAP.get(align, PP_ALIGN.LEFT)
    run = paragraph.add_run()
    run.text = str(text)
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
    radius: bool = False,
) -> None:
    shape = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = _hex_to_rgb(fill_color)
    shape.line.fill.background()


def _add_title_box(slide: Any, title: str, theme: dict[str, str | int], *, top: float = 0.72) -> None:
    _add_panel(slide, left=0.75, top=top, width=4.1, height=0.62, fill_color=str(theme["accent"]), radius=False)
    _add_text_box(
        slide,
        text=title,
        left=1.0,
        top=top + 0.12,
        width=3.55,
        height=0.32,
        font_size=19,
        font_color=str(theme["inverse_text"]),
        bold=True,
    )


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
        radius=False,
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
        bullet.text = "•  "
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


def _render_bullets(
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


def _render_people(
    slide: Any,
    people: list[str],
    *,
    left: float,
    top: float,
    width: float,
    theme: dict[str, str | int],
    align: str = "left",
) -> None:
    if not people:
        return
    _add_text_box(
        slide,
        text="\n".join(people),
        left=left,
        top=top,
        width=width,
        height=1.2,
        font_size=15,
        font_color=str(theme["muted"]),
        align=align,
    )


def _render_title_page(slide: Any, slots: dict[str, Any], theme: dict[str, str | int]) -> None:
    _add_panel(slide, left=0.7, top=0.7, width=0.18, height=5.9, fill_color=str(theme["accent"]))
    _add_text_box(
        slide,
        text=str(slots.get("eyebrow", "")),
        left=1.1,
        top=1.0,
        width=3.4,
        height=0.35,
        font_size=13,
        font_color=str(theme["accent"]),
        bold=True,
    )
    _add_text_box(
        slide,
        text=str(slots.get("headline", "")),
        left=1.1,
        top=1.55,
        width=8.8,
        height=1.45,
        font_size=int(theme["title_size"]) + 8,
        font_color=str(theme["text"]),
        bold=True,
    )
    _add_text_box(
        slide,
        text=str(slots.get("body", "")),
        left=1.1,
        top=3.25,
        width=7.8,
        height=0.8,
        font_size=int(theme["body_size"]) + 1,
        font_color=str(theme["muted"]),
    )
    _render_people(
        slide,
        _coerce_list(slots.get("people")),
        left=1.1,
        top=4.55,
        width=5.5,
        theme=theme,
    )


def _render_content_box_list(slide: Any, slots: dict[str, Any], theme: dict[str, str | int]) -> None:
    _add_title_box(slide, str(slots.get("title_box_label") or slots.get("headline", "")), theme)
    _add_text_box(
        slide,
        text=str(slots.get("body", "")),
        left=5.1,
        top=0.87,
        width=6.7,
        height=0.45,
        font_size=14,
        font_color=str(theme["muted"]),
    )
    _add_panel(slide, left=0.9, top=1.72, width=11.5, height=4.95, fill_color=str(theme["panel"]))
    _render_bullets(
        slide,
        _coerce_list(slots.get("bullets")),
        left=1.25,
        top=2.1,
        width=7.4,
        height=4.0,
        theme=theme,
    )
    _add_panel(slide, left=9.15, top=2.05, width=2.8, height=2.4, fill_color=str(theme["soft_panel"]))
    _add_text_box(
        slide,
        text=str(slots.get("highlight", "")),
        left=9.45,
        top=2.35,
        width=2.15,
        height=1.7,
        font_size=15,
        font_color=str(theme["text"]),
        bold=True,
        vertical_anchor=MSO_ANCHOR.MIDDLE,
    )


def _render_content_two_panel(slide: Any, slots: dict[str, Any], theme: dict[str, str | int]) -> None:
    _add_title_box(slide, str(slots.get("title_box_label") or slots.get("headline", "")), theme)
    _add_panel(slide, left=0.9, top=1.85, width=5.45, height=4.55, fill_color=str(theme["panel"]))
    _add_panel(slide, left=6.75, top=1.85, width=5.45, height=4.55, fill_color=str(theme["soft_panel"]))
    _render_bullets(
        slide,
        _coerce_list(slots.get("left_points") or slots.get("bullets")),
        left=1.2,
        top=2.2,
        width=4.85,
        height=3.7,
        theme=theme,
    )
    _render_bullets(
        slide,
        _coerce_list(slots.get("right_points")),
        left=7.05,
        top=2.2,
        width=4.85,
        height=3.7,
        theme=theme,
    )


def _render_content_sidebar(slide: Any, slots: dict[str, Any], theme: dict[str, str | int]) -> None:
    _add_title_box(slide, str(slots.get("title_box_label") or slots.get("headline", "")), theme)
    _add_panel(slide, left=0.9, top=1.7, width=2.55, height=4.95, fill_color=str(theme["accent"]))
    _add_text_box(
        slide,
        text=str(slots.get("highlight", "")) or str(slots.get("body", "")),
        left=1.2,
        top=2.0,
        width=1.95,
        height=4.2,
        font_size=16,
        font_color=str(theme["inverse_text"]),
        bold=True,
        vertical_anchor=MSO_ANCHOR.MIDDLE,
    )
    _add_panel(slide, left=3.75, top=1.7, width=8.45, height=4.95, fill_color=str(theme["panel"]))
    _render_bullets(
        slide,
        _coerce_list(slots.get("bullets")),
        left=4.1,
        top=2.05,
        width=7.75,
        height=3.9,
        theme=theme,
    )


def _render_content_split_band(slide: Any, slots: dict[str, Any], theme: dict[str, str | int]) -> None:
    _add_title_box(slide, str(slots.get("title_box_label") or slots.get("headline", "")), theme)
    _add_panel(slide, left=0.9, top=1.85, width=11.2, height=1.15, fill_color=str(theme["soft_panel"]))
    _add_text_box(
        slide,
        text=str(slots.get("body", "")),
        left=1.2,
        top=2.18,
        width=10.6,
        height=0.45,
        font_size=15,
        font_color=str(theme["text"]),
        bold=True,
        align="center",
    )
    _add_panel(slide, left=0.9, top=3.35, width=5.35, height=3.15, fill_color=str(theme["panel"]))
    _add_panel(slide, left=6.75, top=3.35, width=5.35, height=3.15, fill_color=str(theme["panel"]))
    _render_bullets(
        slide,
        _coerce_list(slots.get("left_points") or slots.get("bullets")),
        left=1.2,
        top=3.7,
        width=4.75,
        height=2.4,
        theme=theme,
    )
    _render_bullets(
        slide,
        _coerce_list(slots.get("right_points")),
        left=7.05,
        top=3.7,
        width=4.75,
        height=2.4,
        theme=theme,
    )


def _render_content_compact(slide: Any, slots: dict[str, Any], theme: dict[str, str | int]) -> None:
    _add_title_box(slide, str(slots.get("title_box_label") or slots.get("headline", "")), theme)
    _add_panel(slide, left=0.9, top=1.8, width=11.2, height=4.85, fill_color=str(theme["panel"]))
    _render_bullets(
        slide,
        _coerce_list(slots.get("bullets")),
        left=1.2,
        top=2.15,
        width=6.4,
        height=3.9,
        theme=theme,
    )
    _add_panel(slide, left=8.2, top=2.15, width=3.25, height=3.75, fill_color=str(theme["soft_panel"]))
    _add_text_box(
        slide,
        text=str(slots.get("highlight", "")) or str(slots.get("body", "")),
        left=8.5,
        top=2.55,
        width=2.65,
        height=2.9,
        font_size=15,
        font_color=str(theme["text"]),
        bold=True,
        vertical_anchor=MSO_ANCHOR.MIDDLE,
    )


def _render_closing_page(slide: Any, slots: dict[str, Any], theme: dict[str, str | int]) -> None:
    _add_panel(slide, left=0.9, top=1.0, width=11.5, height=5.2, fill_color=str(theme["panel"]))
    _add_panel(slide, left=0.9, top=1.0, width=11.5, height=0.2, fill_color=str(theme["accent"]))
    _add_text_box(
        slide,
        text=str(slots.get("headline", "감사합니다")),
        left=1.35,
        top=2.0,
        width=10.4,
        height=0.9,
        font_size=int(theme["title_size"]) + 10,
        font_color=str(theme["text"]),
        bold=True,
        align="center",
    )
    _add_text_box(
        slide,
        text=str(slots.get("body", "")),
        left=2.0,
        top=3.15,
        width=9.1,
        height=0.5,
        font_size=16,
        font_color=str(theme["muted"]),
        align="center",
    )
    _render_people(
        slide,
        _coerce_list(slots.get("people")),
        left=2.2,
        top=4.2,
        width=8.8,
        theme=theme,
        align="center",
    )


def _render_slots(slide: Any, slide_content: SlideContent, page: PageLayout) -> None:
    theme = _theme_for(slide_content.theme)
    slots = page.slots
    if not slots:
        return

    _set_bg(slide, page.background or str(theme["background"]))

    variant = slide_content.slide_variant
    if variant == "title_page":
        _render_title_page(slide, slots, theme)
    elif variant == "content_box_list":
        _render_content_box_list(slide, slots, theme)
    elif variant == "content_two_panel":
        _render_content_two_panel(slide, slots, theme)
    elif variant == "content_sidebar":
        _render_content_sidebar(slide, slots, theme)
    elif variant == "content_split_band":
        _render_content_split_band(slide, slots, theme)
    elif variant == "content_compact":
        _render_content_compact(slide, slots, theme)
    elif variant == "closing_page":
        _render_closing_page(slide, slots, theme)


def _build_page(prs: Presentation, slide_content: SlideContent, page: PageLayout) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    theme = _theme_for(slide_content.theme)
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
