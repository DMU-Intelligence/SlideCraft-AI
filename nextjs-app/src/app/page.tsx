"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

import { apiClient } from "@/lib/api";
import { toErrorObject } from "@/lib/utils";
import { useApiTestStore } from "@/store/useApiTestStore";
import { GeneratedResults } from "@/components/GeneratedResults";
import { UploadArea } from "@/components/UploadArea";

export default function Home() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [presentationTitle, setPresentationTitle] = useState("");
  const [isGenerated, setIsGenerated] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = useApiTestStore((s) => s.backendBaseUrl);
  const setCurrentProjectId = useApiTestStore((s) => s.setCurrentProjectId);
  const setIngestResult = useApiTestStore((s) => s.setIngestResult);
  const ingestResult = useApiTestStore((s) => s.ingestResult);

  const handleGenerate = async () => {
    if (!uploadedFile || !presentationTitle || isGenerating) return;

    setIsGenerating(true);
    setError(null);

    try {
      const response = await apiClient.ingestDocument(baseUrl, {
        file: uploadedFile,
        title: presentationTitle,
        language: "ko",
      });

      // Store에 결과 저장
      setCurrentProjectId(response.project_id);
      setIngestResult(response);
      setIsGenerated(true);
    } catch (err) {
      const errorObj = toErrorObject(err);
      const errorMessage = typeof errorObj.message === "string"
        ? errorObj.message
        : "업로드에 실패했습니다. 다시 시도해주세요.";
      setError(errorMessage);
      console.error("Ingest error:", err);
    } finally {
      setIsGenerating(false);
    }
  };

  if (isGenerated && ingestResult) {
    // ingest 결과의 content를 script로 사용
    const mockSlides = [
      { id: 1, title: "소개 및 개요" },
      { id: 2, title: "주요 내용 1" },
      { id: 3, title: "주요 내용 2" },
      { id: 4, title: "핵심 포인트" },
      { id: 5, title: "결론 및 다음 단계" },
    ];

    return (
      <GeneratedResults
        slides={mockSlides}
        script={ingestResult.content || ""}
        presentationTitle={presentationTitle}
        projectId={ingestResult.project_id}
        onBack={() => {
          setIsGenerated(false);
          setError(null);
        }}
      />
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50 p-6">
      <div className="w-full max-w-2xl">
        <header className="mb-12 text-center">
          <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 shadow-lg">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h1 className="mb-3 text-4xl font-bold text-gray-900">SlideCraft AI</h1>
          <p className="text-lg text-gray-600">문서를 업로드하면 발표 자료가 자동으로 생성됩니다.</p>
        </header>

        <section className="space-y-8 rounded-3xl border border-gray-100 bg-white p-10 shadow-xl">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          <div>
            <label className="mb-3 block text-sm font-semibold text-gray-700">PDF 문서 업로드</label>
            <UploadArea onFileSelect={setUploadedFile} selectedFile={uploadedFile} />
          </div>

          <div>
            <label htmlFor="title" className="mb-3 block text-sm font-semibold text-gray-700">
              발표 제목
            </label>
            <input
              id="title"
              type="text"
              value={presentationTitle}
              onChange={(e) => setPresentationTitle(e.target.value)}
              placeholder="발표 제목을 입력하세요..."
              className="w-full rounded-xl border border-gray-200 px-5 py-4 text-gray-900 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </div>

          <button
            type="button"
            onClick={handleGenerate}
            disabled={!uploadedFile || !presentationTitle || isGenerating}
            className="flex w-full items-center justify-center gap-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 text-lg font-semibold text-white shadow-lg transition-all duration-200 hover:from-blue-700 hover:to-indigo-700 hover:shadow-xl disabled:cursor-not-allowed disabled:from-gray-300 disabled:to-gray-300 disabled:shadow-none"
          >
            {isGenerating ? (
              <>
                <span className="h-5 w-5 animate-spin rounded-full border-[3px] border-white/30 border-t-white" />
                생성 중...
              </>
            ) : (
              <>
                <Sparkles className="h-5 w-5" />
                AI로 PPT 생성하기
              </>
            )}
          </button>

          <p className="text-center text-sm text-gray-500">AI가 문서를 분석하여 몇 초 안에 멋진 발표 자료를 만들어 드립니다</p>
        </section>

        <footer className="mt-8 text-center text-sm text-gray-500">고급 AI 기술로 제공됩니다</footer>
      </div>
    </main>
  );
}
