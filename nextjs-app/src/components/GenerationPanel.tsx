"use client";

import { useState } from "react";

import { apiClient } from "@/lib/api";
import { toErrorObject } from "@/lib/utils";
import { useApiTestStore } from "@/store/useApiTestStore";

const inputClass =
  "w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-gray-900 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100";

const secondaryBtn =
  "rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm font-medium text-gray-800 transition-colors hover:border-blue-200 hover:bg-blue-50/50 disabled:cursor-not-allowed disabled:opacity-50";

const primaryBtn =
  "rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-3 py-2.5 text-sm font-semibold text-white shadow-md transition-all hover:from-blue-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:from-gray-300 disabled:to-gray-300";

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
  const pid = projectId ? Number(projectId) : NaN;
  const validPid = Number.isFinite(pid) ? pid : null;

  const runOutline = async () => {
    if (validPid == null) return;
    const req = { project_id: validPid, language, tone, presentation_length_minutes: presentationLengthMinutes };
    setActionLoading("generateOutline", req);
    try {
      const res = await apiClient.generateOutline(baseUrl, { project_id: validPid });
      setOutlineResult(res);
      setActionSuccess("generateOutline", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("generateOutline", toErrorObject(error));
    }
  };

  const runSlides = async () => {
    if (validPid == null) return;
    const req = { project_id: validPid, max_slides: maxSlides, language, tone };
    setActionLoading("generateSlides", req);
    try {
      const res = await apiClient.generateSlides(baseUrl, { project_id: validPid, max_slides: maxSlides });
      setSlidesResult(res);
      setActionSuccess("generateSlides", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("generateSlides", toErrorObject(error));
    }
  };

  const runNotes = async () => {
    if (validPid == null) return;
    const req = { project_id: validPid, tone };
    setActionLoading("generateNotes", req);
    try {
      const res = await apiClient.generateNotes(baseUrl, { project_id: validPid });
      setNotesResult(res);
      setActionSuccess("generateNotes", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("generateNotes", toErrorObject(error));
    }
  };

  const runAll = async () => {
    if (validPid == null) return;
    const req = {
      project_id: validPid,
      max_slides: maxSlides,
      language,
      tone,
      presentation_length_minutes: presentationLengthMinutes,
    };
    setActionLoading("generateAll", req);
    try {
      const res = await apiClient.generateAll(baseUrl, { project_id: validPid, max_slides: maxSlides });
      setGenerateAllResult(res);
      setOutlineResult({ project_id: res.project_id, outline: res.outline });
      setSlidesResult({ project_id: res.project_id, slides: res.slides });
      setNotesResult({ project_id: res.project_id, notes: res.notes });
      setActionSuccess("generateAll", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("generateAll", toErrorObject(error));
    }
  };

  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-5 shadow-lg md:p-6">
      <h2 className="text-sm font-semibold text-gray-900">생성</h2>
      <p className="mt-1 text-xs text-gray-600">Ingest 후 같은 프로젝트 ID로 아웃라인 · 슬라이드 · 노트를 만듭니다.</p>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <input className={inputClass} value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="language" />
        <input className={inputClass} value={tone} onChange={(e) => setTone(e.target.value)} placeholder="tone" />
        <input
          type="number"
          className={inputClass}
          value={maxSlides}
          min={1}
          max={30}
          onChange={(e) => setMaxSlides(Number(e.target.value))}
          placeholder="max slides"
        />
        <input
          type="number"
          className={inputClass}
          value={presentationLengthMinutes}
          min={1}
          max={120}
          onChange={(e) => setPresentationLengthMinutes(Number(e.target.value))}
          placeholder="minutes"
        />
      </div>

      <p className="mt-3 text-xs text-gray-500">현재 project_id: {projectId || "(없음)"}</p>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <button type="button" className={secondaryBtn} disabled={!canCall || validPid == null || actionStatus.generateOutline === "loading"} onClick={runOutline}>
          {actionStatus.generateOutline === "loading" ? "생성 중…" : "아웃라인"}
        </button>
        <button type="button" className={secondaryBtn} disabled={!canCall || validPid == null || actionStatus.generateSlides === "loading"} onClick={runSlides}>
          {actionStatus.generateSlides === "loading" ? "생성 중…" : "슬라이드"}
        </button>
        <button type="button" className={secondaryBtn} disabled={!canCall || validPid == null || actionStatus.generateNotes === "loading"} onClick={runNotes}>
          {actionStatus.generateNotes === "loading" ? "생성 중…" : "노트"}
        </button>
        <button type="button" className={primaryBtn} disabled={!canCall || validPid == null || actionStatus.generateAll === "loading"} onClick={runAll}>
          {actionStatus.generateAll === "loading" ? "생성 중…" : "한 번에 생성"}
        </button>
      </div>
    </section>
  );
}
