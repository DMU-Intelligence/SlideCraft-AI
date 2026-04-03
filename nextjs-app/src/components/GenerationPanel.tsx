"use client";

import { useState } from "react";

import { apiClient } from "@/lib/api";
import { toErrorObject } from "@/lib/utils";
import { useApiTestStore } from "@/store/useApiTestStore";

export function GenerationPanel() {
  const baseUrl = useApiTestStore((s) => s.backendBaseUrl);
  const projectId = useApiTestStore((s) => s.currentProjectId);
  const actionStatus = useApiTestStore((s) => s.actionStatus);

  const setActionLoading = useApiTestStore((s) => s.setActionLoading);
  const setActionSuccess = useApiTestStore((s) => s.setActionSuccess);
  const setActionError = useApiTestStore((s) => s.setActionError);

  const setOutlineResult = useApiTestStore((s) => s.setOutlineResult);
  const setSlidesResult = useApiTestStore((s) => s.setSlidesResult);
  const setNotesResult = useApiTestStore((s) => s.setNotesResult);
  const setGenerateAllResult = useApiTestStore((s) => s.setGenerateAllResult);

  const [language, setLanguage] = useState("en");
  const [tone, setTone] = useState("professional");
  const [maxSlides, setMaxSlides] = useState(8);
  const [presentationLengthMinutes, setPresentationLengthMinutes] = useState(10);

  const canCall = Boolean(projectId);

  const runOutline = async () => {
    if (!projectId) return;
    const req = { project_id: projectId, language, tone, presentation_length_minutes: presentationLengthMinutes };
    setActionLoading("generateOutline", req);
    try {
      const res = await apiClient.generateOutline(baseUrl, { project_id: projectId });
      setOutlineResult(res);
      setActionSuccess("generateOutline", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("generateOutline", toErrorObject(error));
    }
  };

  const runSlides = async () => {
    if (!projectId) return;
    const req = { project_id: projectId, max_slides: maxSlides, language, tone };
    setActionLoading("generateSlides", req);
    try {
      const res = await apiClient.generateSlides(baseUrl, { project_id: projectId, max_slides: maxSlides });
      setSlidesResult(res);
      setActionSuccess("generateSlides", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("generateSlides", toErrorObject(error));
    }
  };

  const runNotes = async () => {
    if (!projectId) return;
    const req = { project_id: projectId, tone };
    setActionLoading("generateNotes", req);
    try {
      const res = await apiClient.generateNotes(baseUrl, { project_id: projectId });
      setNotesResult(res);
      setActionSuccess("generateNotes", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("generateNotes", toErrorObject(error));
    }
  };

  const runAll = async () => {
    if (!projectId) return;
    const req = {
      project_id: projectId,
      max_slides: maxSlides,
      language,
      tone,
      presentation_length_minutes: presentationLengthMinutes,
    };
    setActionLoading("generateAll", req);
    try {
      const res = await apiClient.generateAll(baseUrl, { project_id: projectId, max_slides: maxSlides });
      setGenerateAllResult(res);
      setOutlineResult({ project_id: res.project_id, outline: res.outline, summary: res.summary });
      setSlidesResult({ project_id: res.project_id, slides: res.slides });
      setNotesResult({ project_id: res.project_id, notes: res.notes });
      setActionSuccess("generateAll", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("generateAll", toErrorObject(error));
    }
  };

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-zinc-900">Generation Panel</h2>
      <p className="mt-1 text-xs text-zinc-600">Uses the current project_id from ingestion state.</p>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <input
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          placeholder="language"
        />
        <input
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm"
          value={tone}
          onChange={(e) => setTone(e.target.value)}
          placeholder="tone"
        />
        <input
          type="number"
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm"
          value={maxSlides}
          min={1}
          max={30}
          onChange={(e) => setMaxSlides(Number(e.target.value))}
        />
        <input
          type="number"
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm"
          value={presentationLengthMinutes}
          min={1}
          max={120}
          onChange={(e) => setPresentationLengthMinutes(Number(e.target.value))}
        />
      </div>

      <div className="mt-2 text-xs text-zinc-500">Current project_id: {projectId || "(none)"}</div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <button
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:opacity-50"
          disabled={!canCall || actionStatus.generateOutline === "loading"}
          onClick={runOutline}
        >
          {actionStatus.generateOutline === "loading" ? "Generating..." : "Generate Outline"}
        </button>
        <button
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:opacity-50"
          disabled={!canCall || actionStatus.generateSlides === "loading"}
          onClick={runSlides}
        >
          {actionStatus.generateSlides === "loading" ? "Generating..." : "Generate Slides"}
        </button>
        <button
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:opacity-50"
          disabled={!canCall || actionStatus.generateNotes === "loading"}
          onClick={runNotes}
        >
          {actionStatus.generateNotes === "loading" ? "Generating..." : "Generate Notes"}
        </button>
        <button
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm text-white disabled:opacity-50"
          disabled={!canCall || actionStatus.generateAll === "loading"}
          onClick={runAll}
        >
          {actionStatus.generateAll === "loading" ? "Generating..." : "Generate All"}
        </button>
      </div>
    </section>
  );
}

