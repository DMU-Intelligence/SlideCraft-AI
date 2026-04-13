"use client";

import { Pen } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { usePPTGenerator } from "@/hooks/usePPTGenerator";
import { UploadArea } from "@/components/UploadArea";
import { BrushLoading } from "@/components/BrushLoading";
import { GeneratedResults } from "@/components/GeneratedResults";

export default function Home() {
  const {
    phase,
    uploadedFile,
    presentationTitle,
    slides,
    script,
    currentSlideIndex,
    generatePending,
    downloadPending,
    error,
    loadingMessage,
    setUploadedFile,
    setPresentationTitle,
    generate,
    download,
    reset,
    nextSlide,
    prevSlide,
  } = usePPTGenerator();

  return (
    <AnimatePresence mode="wait">
      {/* ── Phase A: The Dropzone ── */}
      {phase === "upload" && (
        <motion.main
          key="upload"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, x: -40 }}
          transition={{ duration: 0.4 }}
          className="flex min-h-screen items-center justify-center p-6"
        >
          <div className="w-full max-w-xl">
            <header className="mb-10 text-center">
              <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-full border border-border-subtle">
                <Pen className="h-5 w-5 text-ink" strokeWidth={1.5} />
              </div>
              <h1 className="mb-2 text-3xl font-medium tracking-tight text-ink">
                SlideCraft AI
              </h1>
              <p className="text-sm text-ink-light">
                문서를 업로드하면 발표 자료가 자동으로 생성됩니다.
              </p>
            </header>

            <section className="space-y-6 rounded-xl border border-border-subtle bg-white p-8">
              <div>
                <label className="mb-2 block text-sm font-medium text-ink">
                  PDF 문서 업로드
                </label>
                <UploadArea onFileSelect={setUploadedFile} selectedFile={uploadedFile} />
              </div>

              <div>
                <label
                  htmlFor="title"
                  className="mb-2 block text-sm font-medium text-ink"
                >
                  발표 제목
                </label>
                <input
                  id="title"
                  type="text"
                  value={presentationTitle}
                  onChange={(e) => setPresentationTitle(e.target.value)}
                  placeholder="발표 제목을 입력하세요..."
                  className="w-full rounded-lg border border-border-subtle bg-white px-4 py-3 text-ink outline-none transition-colors placeholder:text-ink-faint focus:border-accent"
                />
              </div>

              {error && (
                <p className="text-sm text-red-600">{error}</p>
              )}

              <button
                type="button"
                onClick={generate}
                disabled={!uploadedFile || !presentationTitle || generatePending}
                aria-label="AI로 PPT 생성하기"
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-accent bg-accent px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:border-border-subtle disabled:bg-muted disabled:text-ink-faint"
              >
                <Pen className="h-4 w-4" strokeWidth={1.5} />
                슬라이드 그리기
              </button>
            </section>
          </div>
        </motion.main>
      )}

      {/* ── Phase B: The Brush Drawing ── */}
      {phase === "loading" && (
        <BrushLoading key="loading" message={loadingMessage} />
      )}

      {/* ── Phase C: The Split Preview ── */}
      {phase === "result" && (
        <GeneratedResults
          key="result"
          slides={slides}
          script={script}
          presentationTitle={presentationTitle}
          currentSlideIndex={currentSlideIndex}
          onBack={reset}
          onDownload={download}
          onPrev={prevSlide}
          onNext={nextSlide}
          downloadPending={downloadPending}
        />
      )}
    </AnimatePresence>
  );
}