"use client";

import { ChevronLeft, Download } from "lucide-react";

export interface ResultSlide {
  id: number;
  title: string;
}

interface GeneratedResultsProps {
  slides: ResultSlide[];
  script: string;
  presentationTitle?: string;
  projectId?: number;
  onBack: () => void;
  onDownload?: () => void;
  downloadPending?: boolean;
}

export function GeneratedResults({
  slides,
  script,
  presentationTitle,
  projectId,
  onBack,
  onDownload,
  downloadPending,
}: GeneratedResultsProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <div className="border-b border-gray-200 bg-white/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-2 text-gray-600 transition-colors hover:text-gray-900"
          >
            <ChevronLeft className="h-5 w-5" />
            <span>워크플로로 돌아가기</span>
          </button>
          <div className="flex flex-col items-end gap-0.5">
            {presentationTitle ? (
              <span className="max-w-[min(100vw-12rem,28rem)] truncate text-sm font-medium text-gray-800">
                {presentationTitle}
              </span>
            ) : null}
            <button
              type="button"
              onClick={onDownload}
              disabled={downloadPending || !onDownload}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {downloadPending ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              PPT 다운로드
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">발표 슬라이드</h2>
            <div className="h-[calc(100vh-220px)] space-y-4 overflow-y-auto rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              {slides.map((slide) => (
                <div
                  key={slide.id}
                  className="group cursor-default overflow-hidden rounded-xl border border-gray-200 transition-all hover:border-blue-300 hover:shadow-md"
                >
                  <div className="relative flex aspect-video items-center justify-center bg-gradient-to-br from-blue-500 to-indigo-600">
                    <div className="absolute inset-0 bg-black/5" />
                    <div className="relative px-6 text-center">
                      <div className="mb-2 text-sm text-white/60">슬라이드 {slide.id}</div>
                      <h3 className="text-lg font-semibold text-white">{slide.title}</h3>
                    </div>
                  </div>
                  <div className="bg-gray-50 px-4 py-3 transition-colors group-hover:bg-blue-50">
                    <p className="text-sm font-medium text-gray-600">슬라이드 {slide.id}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">발표 스크립트</h2>
            <div className="h-[calc(100vh-220px)] overflow-y-auto rounded-2xl border border-gray-100 bg-white p-8 shadow-sm">
              <p className="whitespace-pre-line leading-relaxed text-gray-700">{script || "노트가 아직 없습니다."}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
