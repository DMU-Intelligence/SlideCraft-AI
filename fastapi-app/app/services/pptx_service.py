from __future__ import annotations

"""PPTX 생성 서비스 — python-pptx 기반

ProjectState의 slides / notes 데이터를 받아
실제 .pptx 파일을 생성합니다.

슬라이드 레이아웃:
  - 표지 슬라이드 (제목 + 부제목)
  - 콘텐츠 슬라이드 (제목 + 불릿 리스트)
  - 발표자 노트 삽입 (각 슬라이드 하단)
"""

import io
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from ..models.project_state import ProjectState
from ..schemas.generate import Slide, SlideNotes


# ── 디자인 상수 ────────────────────────────────────────────────────────────────

# 슬라이드 크기: 와이드스크린 16:9
SLIDE_WIDTH = Inches(13.33)
SLIDE_HEIGHT = Inches(7.5)

# 색상
COLOR_BG = RGBColor(0x0F, 0x17, 0x2A)        # 진한 네이비 배경
COLOR_ACCENT = RGBColor(0x5B, 0x8D, 0xEF)    # 파란 포인트
COLOR_TITLE = RGBColor(0xFF, 0xFF, 0xFF)      # 흰색 제목
COLOR_BODY = RGBColor(0xD4, 0xD8, 0xE8)      # 연한 회색 본문
COLOR_BULLET_DOT = RGBColor(0x5B, 0x8D, 0xEF)

# 폰트
FONT_TITLE = "Malgun Gothic"  # 한글 지원, 없으면 시스템 기본값 사용
FONT_BODY = "Malgun Gothic"


# ── 헬퍼 함수 ──────────────────────────────────────────────────────────────────

def _set_bg_color(slide: Any, color: RGBColor) -> None:
    """슬라이드 배경색 설정"""
    from pptx.oxml.ns import qn
    from lxml import etree

    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_text_box(
    slide: Any,
    text: str,
    left: float,
    top: float,
    width: float,
    height: float,
    font_size: int,
    bold: bool = False,
    color: RGBColor = COLOR_TITLE,
    font_name: str = FONT_TITLE,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    word_wrap: bool = True,
) -> Any:
    """텍스트 박스를 슬라이드에 추가하고 반환"""
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = txBox.text_frame
    tf.word_wrap = word_wrap

    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text

    run.font.name = font_name
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color

    return txBox


def _add_accent_bar(slide: Any) -> None:
    """슬라이드 상단에 포인트 색상 바 추가"""
    from pptx.util import Emu
    bar = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(0), Inches(0),
        SLIDE_WIDTH, Inches(0.08),
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = COLOR_ACCENT
    bar.line.fill.background()


# ── 슬라이드 빌더 ──────────────────────────────────────────────────────────────

def _build_cover_slide(prs: Presentation, title: str, subtitle: str) -> None:
    """표지 슬라이드 생성"""
    slide_layout = prs.slide_layouts[6]  # 빈 레이아웃
    slide = prs.slides.add_slide(slide_layout)
    _set_bg_color(slide, COLOR_BG)
    _add_accent_bar(slide)

    # 중앙 제목
    _add_text_box(
        slide, title,
        left=1.0, top=2.2, width=11.33, height=1.8,
        font_size=40, bold=True,
        color=COLOR_TITLE,
        align=PP_ALIGN.CENTER,
    )

    # 구분선 (얇은 사각형)
    line = slide.shapes.add_shape(
        1, Inches(4.5), Inches(4.2), Inches(4.33), Inches(0.04)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_ACCENT
    line.line.fill.background()

    # 부제목
    _add_text_box(
        slide, subtitle,
        left=1.0, top=4.4, width=11.33, height=0.9,
        font_size=18, bold=False,
        color=COLOR_BODY,
        align=PP_ALIGN.CENTER,
    )


def _build_content_slide(
    prs: Presentation,
    slide_data: Slide,
    notes_text: str = "",
    slide_number: int = 1,
    total_slides: int = 1,
) -> None:
    """콘텐츠 슬라이드 생성 (제목 + 불릿 포인트)"""
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)
    _set_bg_color(slide, COLOR_BG)
    _add_accent_bar(slide)

    # 슬라이드 번호 (우상단)
    _add_text_box(
        slide, f"{slide_number} / {total_slides}",
        left=11.5, top=0.15, width=1.6, height=0.4,
        font_size=10, bold=False,
        color=RGBColor(0x88, 0x99, 0xBB),
        align=PP_ALIGN.RIGHT,
    )

    # 제목
    _add_text_box(
        slide, slide_data.title,
        left=0.5, top=0.5, width=12.33, height=1.0,
        font_size=28, bold=True,
        color=COLOR_TITLE,
    )

    # 구분선
    line = slide.shapes.add_shape(
        1, Inches(0.5), Inches(1.55), Inches(12.33), Inches(0.03)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_ACCENT
    line.line.fill.background()

    # 불릿 포인트 영역
    if slide_data.bullets:
        left_in = Inches(0.5)
        top_in = Inches(1.75)
        width_in = Inches(12.33)
        height_in = Inches(5.2)

        txBox = slide.shapes.add_textbox(left_in, top_in, width_in, height_in)
        tf = txBox.text_frame
        tf.word_wrap = True

        for i, bullet in enumerate(slide_data.bullets):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()

            p.space_before = Pt(6)
            p.space_after = Pt(4)

            # 불릿 기호 run
            dot_run = p.add_run()
            dot_run.text = "▸  "
            dot_run.font.name = FONT_BODY
            dot_run.font.size = Pt(16)
            dot_run.font.color.rgb = COLOR_ACCENT
            dot_run.font.bold = True

            # 본문 run
            body_run = p.add_run()
            body_run.text = bullet
            body_run.font.name = FONT_BODY
            body_run.font.size = Pt(16)
            body_run.font.color.rgb = COLOR_BODY
            body_run.font.bold = False

    # 발표자 노트 삽입
    if notes_text:
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        tf.text = notes_text


# ── 공개 인터페이스 ────────────────────────────────────────────────────────────

class PptxGenerator:
    """ProjectState → .pptx 바이트 변환기"""

    def generate(self, state: ProjectState) -> bytes:
        """
        슬라이드와 노트를 포함한 PPTX 파일을 생성하고
        바이트 데이터로 반환합니다.
        """
        prs = Presentation()
        prs.slide_width = SLIDE_WIDTH
        prs.slide_height = SLIDE_HEIGHT

        # 노트를 slide_id → text 딕셔너리로 변환
        notes_map: dict[str, str] = {
            n.slide_id: n.notes for n in state.notes
        }

        total = len(state.slides)

        # 표지 슬라이드
        subtitle = state.outline.presentation_objective if state.outline else ""
        _build_cover_slide(prs, state.title, subtitle)

        # 콘텐츠 슬라이드
        for idx, slide_data in enumerate(state.slides, start=1):
            notes_text = notes_map.get(slide_data.slide_id, "")
            _build_content_slide(
                prs,
                slide_data=slide_data,
                notes_text=notes_text,
                slide_number=idx,
                total_slides=total,
            )

        # 메모리 버퍼에 저장 후 바이트 반환
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)
        return buf.read()