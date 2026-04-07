"use client";

import { useMemo, useState } from "react";
import { Sparkles } from "lucide-react";

import { ApiConfigPanel } from "@/components/ApiConfigPanel";
import { GenerationPanel } from "@/components/GenerationPanel";
import { GeneratedResults } from "@/components/GeneratedResults";
import { IngestPanel } from "@/components/IngestPanel";
import { JsonViewer } from "@/components/JsonViewer";
import { LogsStatusViewer } from "@/components/LogsStatusViewer";
import { ProjectStateViewer } from "@/components/ProjectStateViewer";
import { RegenerationPanel } from "@/components/RegenerationPanel";
import { exportPptx } from "@/lib/api";
import { useApiTestStore } from "@/store/useApiTestStore";

export default function Home() {
  const [showResults, setShowResults] = useState(false);
  const [downloadPending, setDownloadPending] = useState(false);

  const baseUrl = useApiTestStore((s) => s.backendBaseUrl);
  const currentProjectId = useApiTestStore((s) => s.currentProjectId);
  const ingestResult = useApiTestStore((s) => s.ingestResult);
  const latestRequest = useApiTestStore((s) => s.latestRequest);
  const latestResponse = useApiTestStore((s) => s.latestResponse);
  const latestError = useApiTestStore((s) => s.latestError);
  const outlineResult = useApiTestStore((s) => s.outlineResult);
  const slidesResult = useApiTestStore((s) => s.slidesResult);
  const notesResult = useApiTestStore((s) => s.notesResult);
  const generateAllResult = useApiTestStore((s) => s.generateAllResult);
  const regenerateSlideResult = useApiTestStore((s) => s.regenerateSlideResult);
  const regenerateNotesResult = useApiTestStore((s) => s.regenerateNotesResult);

  const { resultSlides, resultScript, presentationTitle, hasSlides, projectIdNumber } = useMemo(() => {
    const slides =
      generateAllResult?.slides ??
      slidesResult?.slides ??
      (regenerateSlideResult?.slide ? [regenerateSlideResult.slide] : []);
    const script =
      (typeof generateAllResult?.notes === "string" ? generateAllResult.notes : "") ||
      (typeof notesResult?.notes === "string" ? notesResult.notes : "") ||
      (typeof regenerateNotesResult?.notes === "string" ? regenerateNotesResult.notes : "");
    const pid = currentProjectId ? Number(currentProjectId) : NaN;
    return {
      resultSlides: slides.map((s, i) => ({ id: i + 1, title: s.title || `슬라이드 ${i + 1}` })),
      resultScript: script,
      presentationTitle: ingestResult?.title,
      hasSlides: slides.length > 0,
      projectIdNumber: Number.isFinite(pid) ? pid : null,
    };
  }, [
    currentProjectId,
    generateAllResult,
    ingestResult?.title,
    notesResult?.notes,
    regenerateNotesResult?.notes,
    regenerateSlideResult?.slide,
    slidesResult?.slides,
  ]);

  const handleDownloadPptx = async () => {
    if (projectIdNumber == null) return;
    setDownloadPending(true);
    try {
      const blob = await exportPptx(baseUrl, {
        projectId: projectIdNumber,
        filename: presentationTitle ? `${presentationTitle}.pptx` : undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = presentationTitle ? `${presentationTitle.replace(/[\\/:*?"<>|]/g, "_")}.pptx` : "presentation.pptx";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Errors surface in store logs when using other actions; export is fire-and-forget here.
    } finally {
      setDownloadPending(false);
    }
  };

  if (showResults && hasSlides) {
    return (
      <GeneratedResults
        slides={resultSlides}
        script={resultScript}
        presentationTitle={presentationTitle}
        onBack={() => setShowResults(false)}
        onDownload={handleDownloadPptx}
        downloadPending={downloadPending}
      />
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 p-4 md:p-6">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 text-center">
          <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 shadow-lg">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 md:text-4xl">SlideCraft AI</h1>
          <p className="mx-auto mt-3 max-w-xl text-base text-gray-600 md:text-lg">문서를 업로드하면 발표 자료를 만들고, API로 단계별 생성을 테스트할 수 있습니다.</p>
          {hasSlides ? (
            <button
              type="button"
              onClick={() => setShowResults(true)}
              className="mt-6 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-lg transition-all hover:from-blue-700 hover:to-indigo-700"
            >
              슬라이드 &amp; 대본 보기
            </button>
          ) : null}
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:gap-8">
          <div className="space-y-6">
            <ApiConfigPanel />
            <IngestPanel />
            <GenerationPanel />
            <RegenerationPanel />
          </div>

          <div className="space-y-6">
            <ProjectStateViewer />
            <LogsStatusViewer />
            <JsonViewer title="Outline JSON" data={outlineResult} />
            <JsonViewer title="Slides JSON" data={slidesResult} />
            <JsonViewer title="Notes JSON" data={notesResult} />
            <JsonViewer title="Latest Request JSON" data={latestRequest} />
            <JsonViewer title="Latest Response JSON" data={latestResponse} />
            <JsonViewer title="Latest Error JSON" data={latestError} />
          </div>
        </div>

        <p className="mt-10 text-center text-sm text-gray-500">FastAPI 백엔드와 연동되는 개발용 클라이언트입니다.</p>
      </div>
    </main>
  );
}
