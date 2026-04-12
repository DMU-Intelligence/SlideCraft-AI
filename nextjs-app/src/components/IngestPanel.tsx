"use client";

import { useMemo, useState } from "react";

import { apiClient } from "@/lib/api";
import { toErrorObject, truncate } from "@/lib/utils";
import { useApiTestStore } from "@/store/useApiTestStore";
import { UploadArea } from "@/components/UploadArea";

const inputClass =
  "w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-gray-900 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100";

export function IngestPanel() {
  const baseUrl = useApiTestStore((s) => s.backendBaseUrl);
  const status = useApiTestStore((s) => s.actionStatus.ingest);
  const ingestResult = useApiTestStore((s) => s.ingestResult);
  const setActionLoading = useApiTestStore((s) => s.setActionLoading);
  const setActionSuccess = useApiTestStore((s) => s.setActionSuccess);
  const setActionError = useApiTestStore((s) => s.setActionError);
  const setIngestResult = useApiTestStore((s) => s.setIngestResult);
  const setCurrentProjectId = useApiTestStore((s) => s.setCurrentProjectId);

  const [file, setFile] = useState<File | null>(null);
  const [projectId, setProjectId] = useState("");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("ko");
  const [tone, setTone] = useState("professional");

  const ingestSummary = useMemo(() => {
    if (!ingestResult) return null;
    return {
      projectId: ingestResult.project_id,
      contentPreview: truncate(ingestResult.content ?? "", 220),
      fileType: ingestResult.metadata?.file_type ?? "",
    };
  }, [ingestResult]);

  const handleIngest = async () => {
    if (!file) return;
    const requestPayload = {
      project_id: projectId || undefined,
      title: title || undefined,
      language,
      tone,
      file_name: file.name,
    };

    setActionLoading("ingest", requestPayload);
    try {
      const res = await apiClient.ingestDocument(baseUrl, {
        file,
        projectId: projectId || undefined,
        title: title || undefined,
        language,
        tone,
      });
      setIngestResult(res);
      setCurrentProjectId(res.project_id);
      setActionSuccess("ingest", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("ingest", toErrorObject(error));
    }
  };

  const statusStyles =
    status === "loading"
      ? "bg-amber-100 text-amber-800"
      : status === "success"
        ? "bg-emerald-100 text-emerald-800"
        : status === "error"
          ? "bg-rose-100 text-rose-800"
          : "bg-gray-100 text-gray-700";

  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-5 shadow-lg md:p-6">
      <h2 className="text-sm font-semibold text-gray-900">문서 업로드 · Ingest</h2>
      <p className="mt-1 text-xs text-gray-600">POST /ingest/document (multipart)</p>

      <div className="mt-4 space-y-5">
        <div>
          <label className="mb-3 block text-sm font-semibold text-gray-700">문서 파일</label>
          <UploadArea onFileSelect={setFile} selectedFile={file} />
        </div>

        <div>
          <label htmlFor="ingest-project-id" className="mb-3 block text-sm font-semibold text-gray-700">
            프로젝트 ID (선택)
          </label>
          <input
            id="ingest-project-id"
            className={inputClass}
            placeholder="비우면 자동 생성"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="ingest-title" className="mb-3 block text-sm font-semibold text-gray-700">
            발표 제목 (선택)
          </label>
          <input
            id="ingest-title"
            className={inputClass}
            placeholder="비우면 파일명 사용"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="ingest-lang" className="mb-2 block text-sm font-semibold text-gray-700">
              언어
            </label>
            <input id="ingest-lang" className={inputClass} placeholder="ko / en" value={language} onChange={(e) => setLanguage(e.target.value)} />
          </div>
          <div>
            <label htmlFor="ingest-tone" className="mb-2 block text-sm font-semibold text-gray-700">
              톤
            </label>
            <input id="ingest-tone" className={inputClass} placeholder="professional" value={tone} onChange={(e) => setTone(e.target.value)} />
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-md transition-all hover:from-blue-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:from-gray-300 disabled:to-gray-300"
          disabled={!file || status === "loading"}
          onClick={handleIngest}
        >
          {status === "loading" ? "처리 중…" : "문서 반영하기"}
        </button>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusStyles}`}>{status}</span>
      </div>

      {ingestSummary && (
        <div className="mt-5 rounded-xl border border-gray-100 bg-gray-50/80 p-4 text-xs text-gray-800">
          <div>
            <span className="font-semibold text-gray-900">project_id:</span> {ingestSummary.projectId}
          </div>
          <div className="mt-1">
            <span className="font-semibold text-gray-900">file_type:</span> {ingestSummary.fileType || "(unknown)"}
          </div>
          <div className="mt-2">
            <span className="font-semibold text-gray-900">content 미리보기:</span> {ingestSummary.contentPreview}
          </div>
        </div>
      )}
    </section>
  );
}
