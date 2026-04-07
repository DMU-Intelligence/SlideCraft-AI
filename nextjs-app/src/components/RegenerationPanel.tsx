"use client";

import { useState } from "react";

import { apiClient } from "@/lib/api";
import { toErrorObject } from "@/lib/utils";
import { useApiTestStore } from "@/store/useApiTestStore";

const inputClass =
  "w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-gray-900 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100";

const secondaryBtn =
  "rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm font-medium text-gray-800 transition-colors hover:border-blue-200 hover:bg-blue-50/50 disabled:cursor-not-allowed disabled:opacity-50";

export function RegenerationPanel() {
  const baseUrl = useApiTestStore((s) => s.backendBaseUrl);
  const projectId = useApiTestStore((s) => s.currentProjectId);
  const actionStatus = useApiTestStore((s) => s.actionStatus);
  const setActionLoading = useApiTestStore((s) => s.setActionLoading);
  const setActionSuccess = useApiTestStore((s) => s.setActionSuccess);
  const setActionError = useApiTestStore((s) => s.setActionError);
  const setRegenerateSlideResult = useApiTestStore((s) => s.setRegenerateSlideResult);
  const setRegenerateNotesResult = useApiTestStore((s) => s.setRegenerateNotesResult);

  const [slideTitle, setSlideTitle] = useState("서론");
  const [userRequest, setUserRequest] = useState("");

  const pid = projectId ? Number(projectId) : NaN;
  const validPid = Number.isFinite(pid) ? pid : null;

  const runRegenerateSlide = async () => {
    if (validPid == null || !slideTitle) return;
    const req = { project_id: validPid, slide_title: slideTitle, user_request: userRequest };
    setActionLoading("regenerateSlide", req);
    try {
      const res = await apiClient.regenerateSlide(baseUrl, {
        project_id: validPid,
        slide_title: slideTitle,
        user_request: userRequest || undefined,
      });
      setRegenerateSlideResult(res);
      setActionSuccess("regenerateSlide", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("regenerateSlide", toErrorObject(error));
    }
  };

  const runRegenerateNotes = async () => {
    if (validPid == null) return;
    const req = { project_id: validPid };
    setActionLoading("regenerateNotes", req);
    try {
      const res = await apiClient.regenerateNotes(baseUrl, {
        project_id: validPid,
      });
      setRegenerateNotesResult(res);
      setActionSuccess("regenerateNotes", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("regenerateNotes", toErrorObject(error));
    }
  };

  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-5 shadow-lg md:p-6">
      <h2 className="text-sm font-semibold text-gray-900">재생성</h2>
      <p className="mt-1 text-xs text-gray-600">특정 슬라이드 또는 발표 노트만 다시 만듭니다.</p>

      <div className="mt-4 space-y-3">
        <input className={inputClass} placeholder="slide_title" value={slideTitle} onChange={(e) => setSlideTitle(e.target.value)} />
        <input
          className={inputClass}
          placeholder="요청 사항 (선택)"
          value={userRequest}
          onChange={(e) => setUserRequest(e.target.value)}
        />
      </div>

      <p className="mt-3 text-xs text-gray-500">현재 project_id: {projectId || "(없음)"}</p>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <button
          type="button"
          className={secondaryBtn}
          disabled={validPid == null || !slideTitle || actionStatus.regenerateSlide === "loading"}
          onClick={runRegenerateSlide}
        >
          {actionStatus.regenerateSlide === "loading" ? "처리 중…" : "슬라이드 재생성"}
        </button>
        <button
          type="button"
          className={secondaryBtn}
          disabled={validPid == null || actionStatus.regenerateNotes === "loading"}
          onClick={runRegenerateNotes}
        >
          {actionStatus.regenerateNotes === "loading" ? "처리 중…" : "노트 재생성"}
        </button>
      </div>
    </section>
  );
}
