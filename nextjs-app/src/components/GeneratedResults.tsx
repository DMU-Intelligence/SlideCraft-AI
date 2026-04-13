"use client";

import { ChevronLeft, ChevronRight, Download, ArrowLeft } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useCallback } from "react";
import type { ResultSlide } from "@/types/api";
import { SlidePreview } from "@/components/SlideRenderer";

interface GeneratedResultsProps {
  slides: ResultSlide[];
  script: string;
  presentationTitle?: string;
  currentSlideIndex: number;
  onBack: () => void;
  onDownload?: () => void;
  onPrev: () => void;
  onNext: () => void;
  downloadPending?: boolean;
}

export function GeneratedResults({
  slides,
  script,
  presentationTitle,
  currentSlideIndex,
  onBack,
  onDownload,
  onPrev,
  onNext,
  downloadPending,
}: GeneratedResultsProps) {
  const currentSlide = slides[currentSlideIndex];

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") onPrev();
      if (e.key === "ArrowRight") onNext();
    },
    [onPrev, onNext]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="flex h-screen flex-col overflow-hidden"
    >
      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-border-subtle px-8 py-4">
        <button
          type="button"
          onClick={onBack}
          aria-label="\uCC98\uC74C\uC73C\uB85C \uB3CC\uC544\uAC00\uAE30"
          className="flex items-center gap-2 text-base text-ink-light transition-colors hover:text-ink"
        >
          <ArrowLeft className="h-5 w-5" strokeWidth={1.5} />
          <span>{"\uCC98\uC74C\uC73C\uB85C"}</span>
        </button>

        {presentationTitle && (
          <h1 className="absolute left-1/2 -translate-x-1/2 text-base font-medium tracking-tight text-ink">
            {presentationTitle}
          </h1>
        )}

        <button
          type="button"
          onClick={onDownload}
          disabled={downloadPending || !onDownload}
          aria-label="PPT \uB2E4\uC6B4\uB85C\uB4DC"
          className="flex items-center gap-2 rounded-lg border border-border-subtle bg-white px-5 py-2 text-base font-medium text-ink transition-colors hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
        >
          {downloadPending ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-ink-faint border-t-ink" />
          ) : (
            <Download className="h-4 w-4" strokeWidth={1.5} />
          )}
          {"PPT \uB2E4\uC6B4\uB85C\uB4DC"}
        </button>
      </header>

      {/* Main content */}
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        {/* Left: Slide area (60%) */}
        <div className="flex min-h-0 flex-1 flex-col lg:w-[60%] lg:flex-none">
          {/* Slide preview */}
          <div className="relative flex min-h-0 flex-1 items-center justify-center px-8 py-6 lg:px-12 lg:py-8">
            <AnimatePresence mode="wait">
              {currentSlide && (
                <motion.div
                  key={currentSlide.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.25 }}
                  className="w-full max-w-3xl"
                >
                  <SlidePreview slide={currentSlide} />
                  <div className="mt-3 flex items-baseline justify-between">
                    <p className="text-sm font-medium tracking-tight text-ink">
                      {currentSlide.title}
                    </p>
                    <span className="text-xs tabular-nums text-ink-faint">
                      {currentSlideIndex + 1} / {slides.length}
                    </span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Prev / Next overlays */}
            <button
              type="button"
              onClick={onPrev}
              disabled={currentSlideIndex === 0}
              aria-label="\uC774\uC804 \uC2AC\uB77C\uC774\uB4DC"
              className="absolute left-3 top-1/2 -translate-y-1/2 rounded-full border border-border-subtle bg-white/80 p-3 text-ink-light backdrop-blur-sm transition-all hover:border-ink-faint hover:text-ink disabled:pointer-events-none disabled:opacity-0"
            >
              <ChevronLeft className="h-6 w-6" strokeWidth={1.5} />
            </button>
            <button
              type="button"
              onClick={onNext}
              disabled={currentSlideIndex === slides.length - 1}
              aria-label="\uB2E4\uC74C \uC2AC\uB77C\uC774\uB4DC"
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full border border-border-subtle bg-white/80 p-3 text-ink-light backdrop-blur-sm transition-all hover:border-ink-faint hover:text-ink disabled:pointer-events-none disabled:opacity-0"
            >
              <ChevronRight className="h-6 w-6" strokeWidth={1.5} />
            </button>
          </div>
        </div>

        {/* Right: Script (40%) */}
        <div className="flex min-h-0 flex-col border-t border-border-subtle lg:w-[40%] lg:border-l lg:border-t-0">
          <div className="flex items-center justify-between border-b border-border-subtle px-6 py-2.5">
            <h2 className="text-sm font-medium tracking-tight text-ink">{"\uBC1C\uD45C \uB300\uBCF8"}</h2>
            <span className="text-xs text-ink-faint">
              {"\uC2AC\uB77C\uC774\uB4DC"} {currentSlideIndex + 1}
            </span>
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-5 lg:px-8 lg:py-6">
            <div className="prose-analog">
              <p className="whitespace-pre-line text-lg leading-[1.9] tracking-tight text-ink/80">
                {script || "\uB178\uD2B8\uAC00 \uC544\uC9C1 \uC5C6\uC2B5\uB2C8\uB2E4."}
              </p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}