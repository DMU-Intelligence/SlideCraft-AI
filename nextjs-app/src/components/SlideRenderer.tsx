"use client";

import type { SlideElement } from "@/types/api";
import type { ResultSlide } from "@/types/api";

// ── Canvas constants ──────────────────────────────────────────────────────────

const CANVAS_W = 13.33;
const CANVAS_H = 7.5;

const THEME_BG: Record<string, string> = {
  clean_light: "#F7F8FC",
  bold_dark: "#0F172A",
  editorial: "#FFFDF8",
};

function pW(val: number) {
  return `${(val / CANVAS_W) * 100}%`;
}
function pH(val: number) {
  return `${(val / CANVAS_H) * 100}%`;
}
function fontCqw(pt: number) {
  return `${(pt / 72 / CANVAS_W) * 100}cqw`;
}

// ── Element renderer ──────────────────────────────────────────────────────────

function renderElement(el: SlideElement, i: number) {
  if (el.type === "shape") {
    return (
      <div
        key={i}
        className="absolute"
        style={{
          left: pW(el.x),
          top: pH(el.y),
          width: pW(el.w),
          height: pH(el.h),
          backgroundColor: el.fill_color,
          borderRadius: el.shape_type === "round_rectangle" ? "6%" : 0,
        }}
      />
    );
  }

  if (el.type === "text_box") {
    return (
      <div
        key={i}
        className="absolute overflow-hidden leading-snug"
        style={{
          left: pW(el.x),
          top: pH(el.y),
          width: pW(el.w),
          height: pH(el.h),
          color: el.font_color,
          fontWeight: el.font_bold ? "bold" : "normal",
          textAlign: el.align,
          fontSize: fontCqw(el.font_size),
          letterSpacing: "-0.01em",
        }}
      >
        {el.text}
      </div>
    );
  }

  if (el.type === "bullet_list") {
    return (
      <div
        key={i}
        className="absolute overflow-hidden"
        style={{
          left: pW(el.x),
          top: pH(el.y),
          width: pW(el.w),
          height: pH(el.h),
          fontSize: fontCqw(el.font_size),
          color: el.font_color,
          lineHeight: 1.5,
        }}
      >
        {el.items.map((item, j) => (
          <div key={j} className="flex" style={{ gap: "0.4em", marginBottom: "0.2em" }}>
            <span style={{ color: el.bullet_color, flexShrink: 0 }}>
              {el.bullet_char}
            </span>
            <span>{item}</span>
          </div>
        ))}
      </div>
    );
  }

  return null;
}

// ── Slide preview (full size) ─────────────────────────────────────────────────

export function SlidePreview({ slide }: { slide: ResultSlide }) {
  const page = slide.pages?.[0];
  if (!page) {
    return (
      <div className="relative flex aspect-video w-full items-center justify-center rounded-lg border border-border-subtle bg-muted">
        <h3 className="px-4 text-center text-sm font-medium text-ink">
          {slide.title}
        </h3>
      </div>
    );
  }

  const bg = page.background || THEME_BG[slide.theme] || "#F7F8FC";

  return (
    <div
      className="relative w-full overflow-hidden rounded-lg border border-border-subtle"
      style={{
        aspectRatio: `${CANVAS_W} / ${CANVAS_H}`,
        backgroundColor: bg,
        containerType: "inline-size",
      }}
    >
      {page.elements.map((el, i) => renderElement(el, i))}
    </div>
  );
}

// ── Slide thumbnail (small strip) ─────────────────────────────────────────────

export function SlideThumbnail({
  slide,
  isActive,
  index,
  onClick,
}: {
  slide: ResultSlide;
  isActive: boolean;
  index: number;
  onClick: () => void;
}) {
  const page = slide.pages?.[0];
  const bg = page?.background || THEME_BG[slide.theme] || "#F7F8FC";

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`슬라이드 ${index + 1}: ${slide.title}`}
      className={`group relative flex-shrink-0 overflow-hidden rounded-md border transition-all ${
        isActive
          ? "border-accent ring-2 ring-accent/20"
          : "border-border-subtle hover:border-ink-faint"
      }`}
      style={{ width: 96 }}
    >
      {page ? (
        <div
          className="relative overflow-hidden"
          style={{
            aspectRatio: `${CANVAS_W} / ${CANVAS_H}`,
            backgroundColor: bg,
            containerType: "inline-size",
          }}
        >
          <div
            className="pointer-events-none"
            style={{ transform: "scale(1)", transformOrigin: "top left" }}
          >
            {page.elements.map((el, i) => renderElement(el, i))}
          </div>
        </div>
      ) : (
        <div
          className="flex items-center justify-center bg-muted"
          style={{ aspectRatio: `${CANVAS_W} / ${CANVAS_H}` }}
        >
          <span className="text-[8px] text-ink-faint">{slide.title}</span>
        </div>
      )}
      <div
        className={`absolute inset-x-0 bottom-0 px-1 py-0.5 text-center text-[10px] leading-tight ${
          isActive ? "bg-accent text-white" : "bg-white/80 text-ink-light"
        }`}
      >
        {index + 1}
      </div>
    </button>
  );
}
