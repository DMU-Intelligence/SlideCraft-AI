"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

import { GeneratedResults } from "@/components/GeneratedResults";
import { UploadArea } from "@/components/UploadArea";

interface Slide {
  id: number;
  title: string;
}

export default function Home() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [presentationTitle, setPresentationTitle] = useState("");
  const [isGenerated, setIsGenerated] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // API 상태 관리
  const [projectId, setProjectId] = useState<number | null>(null);
  const [slides, setSlides] = useState<Slide[]>([]);
  const [script, setScript] = useState("");
  const [downloadPending, setDownloadPending] = useState(false);

  // API 호출 공통 래퍼 (에러 핸들링 강화)
  const safeFetch = async (url: string, options: RequestInit) => {
    const res = await fetch(url, options);
    if (!res.ok) {
      const errorText = await res.text();
      // "Server action..." 등의 에러 메시지를 콘솔에 출력하여 원인 파악
      throw new Error(`API Error (${res.status}): ${errorText.slice(0, 100)}`);
    }
    return res.json();
  };

  const handleGenerate = async () => {
    if (!uploadedFile || !presentationTitle || isGenerating) return;

    setIsGenerating(true);

    try {
      // 1. PDF 업로드 (엔드포인트 경로 앞에 /api 추가 여부 확인 필요)
      const formData = new FormData();
      formData.append("file", uploadedFile);
      formData.append("title", presentationTitle);
      formData.append("language", "ko");

      // 경로를 /api/ingest/document 로 시도해 보세요 (프로젝트 구조에 따라 수정)
      const ingestData = await safeFetch("/api/ingest/document", {
        method: "POST",
        body: formData,
      });
      
      const newProjectId = ingestData.project_id;
      setProjectId(newProjectId);

      // 2. 결과 생성 요청
      const generateData = await safeFetch("/api/generate/all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: newProjectId }),
      });

      // 3. 데이터 변환 및 저장
      const formattedSlides = generateData.slides.map((slide: any, index: number) => ({
        id: index + 1,
        title: slide.title,
      }));

      setSlides(formattedSlides);
      setScript(generateData.notes);
      setIsGenerated(true);

    } catch (error) {
      console.error("발생한 에러:", error);
      alert("데이터를 가져오는 중 문제가 발생했습니다. 콘솔을 확인해 주세요.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async () => {
    if (!projectId || downloadPending) return;

    setDownloadPending(true);
    try {
      const response = await fetch("/api/export/pptx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId }),
      });

      if (!response.ok) throw new Error("다운로드 실패");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${presentationTitle || "presentation"}.pptx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download error:", error);
      alert("다운로드 중 에러가 발생했습니다.");
    } finally {
      setDownloadPending(false);
    }
  };

  if (isGenerated) {
    return (
      <GeneratedResults
        slides={slides}
        script={script}
        presentationTitle={presentationTitle}
        onBack={() => setIsGenerated(false)}
        onDownload={handleDownload}
        downloadPending={downloadPending}
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
          <div>
            <label className="mb-3 block text-sm font-semibold text-gray-700">PDF 문서 업로드</label>
            <UploadArea onFileSelect={setUploadedFile} selectedFile={uploadedFile} />
          </div>

          <div>
            <label htmlFor="title" className="mb-3 block text-sm font-semibold text-gray-700">발표 제목</label>
            <input
              id="title"
              type="text"
              value={presentationTitle}
              onChange={(e) => setPresentationTitle(e.target.value)}
              placeholder="발표 제목을 입력하세요..."
              className="w-full rounded-xl border border-gray-200 px-5 py-4 text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </div>

          <button
            type="button"
            onClick={handleGenerate}
            disabled={!uploadedFile || !presentationTitle || isGenerating}
            className="flex w-full items-center justify-center gap-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 text-lg font-semibold text-white shadow-lg transition-all hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-300 disabled:to-gray-300"
          >
            {isGenerating ? (
              <><span className="h-5 w-5 animate-spin rounded-full border-[3px] border-white/30 border-t-white" /> 생성 중...</>
            ) : (
              <><Sparkles className="h-5 w-5" /> AI로 PPT 생성하기</>
            )}
          </button>
        </section>
      </div>
    </main>
  );
}