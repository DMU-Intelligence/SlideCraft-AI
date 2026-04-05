"use client";

import { useMemo, useState } from "react";

import { apiClient } from "@/lib/api";
import { toErrorObject, truncate } from "@/lib/utils";
import { useApiTestStore } from "@/store/useApiTestStore";

export function IngestPanel() {
  const baseUrl = useApiTestStore((s) => s.backendBaseUrl);
  const status = useApiTestStore((s) => s.actionStatus.ingest);
  const ingestResult = useApiTestStore((s) => s.ingestResult);
  const setActionLoading = useApiTestStore((s) => s.setActionLoading);
  const setActionSuccess = useApiTestStore((s) => s.setActionSuccess);
  const setActionError = useApiTestStore((s) => s.setActionError);
  const setIngestResult = useApiTestStore((s) => s.setIngestResult);

  const [file, setFile] = useState<File | null>(null);
  const [projectId, setProjectId] = useState("");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("en");
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
      setActionSuccess("ingest", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("ingest", toErrorObject(error));
    }
  };

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-zinc-900">File Upload / Ingest</h2>
      <p className="mt-1 text-xs text-zinc-600">Calls POST /ingest/document with multipart form-data.</p>

      <div className="mt-3 space-y-2">
        <input
          type="file"
          className="w-full text-sm"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <input
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
          placeholder="project_id (optional)"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
        />
        <input
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
          placeholder="title (optional)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-2">
          <input
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm"
            placeholder="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          />
          <input
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm"
            placeholder="tone"
            value={tone}
            onChange={(e) => setTone(e.target.value)}
          />
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <button
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          disabled={!file || status === "loading"}
          onClick={handleIngest}
        >
          {status === "loading" ? "Ingesting..." : "Ingest Document"}
        </button>
        <span className="rounded-full bg-zinc-100 px-2 py-1 text-xs text-zinc-700">{status}</span>
      </div>

      {ingestSummary && (
        <div className="mt-4 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-800">
          <div>
            <span className="font-semibold">project_id:</span> {ingestSummary.projectId}
          </div>
          <div>
            <span className="font-semibold">file_type:</span> {ingestSummary.fileType || "(unknown)"}
          </div>
          <div className="mt-1">
            <span className="font-semibold">content preview:</span> {ingestSummary.contentPreview}
          </div>
        </div>
      )}
    </section>
  );
}
