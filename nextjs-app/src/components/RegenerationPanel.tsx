"use client";

import { useState } from "react";

import { apiClient } from "@/lib/api";
import { toErrorObject } from "@/lib/utils";
import { useApiTestStore } from "@/store/useApiTestStore";

export function RegenerationPanel() {
  const baseUrl = useApiTestStore((s) => s.backendBaseUrl);
  const projectId = useApiTestStore((s) => s.currentProjectId);
  const actionStatus = useApiTestStore((s) => s.actionStatus);
  const setActionLoading = useApiTestStore((s) => s.setActionLoading);
  const setActionSuccess = useApiTestStore((s) => s.setActionSuccess);
  const setActionError = useApiTestStore((s) => s.setActionError);
  const setRegenerateSlideResult = useApiTestStore((s) => s.setRegenerateSlideResult);
  const setRegenerateNotesResult = useApiTestStore((s) => s.setRegenerateNotesResult);

  const [slideId, setSlideId] = useState("slide_01");
  const [force, setForce] = useState(false);
  const [tone, setTone] = useState("professional");

  const runRegenerateSlide = async () => {
    if (!projectId || !slideId) return;
    const req = { project_id: projectId, slide_id: slideId, force, tone };
    setActionLoading("regenerateSlide", req);
    try {
      const res = await apiClient.regenerateSlide(baseUrl, {
        project_id: projectId,
        slide_id: slideId,
        force,
      });
      setRegenerateSlideResult(res);
      setActionSuccess("regenerateSlide", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("regenerateSlide", toErrorObject(error));
    }
  };

  const runRegenerateNotes = async () => {
    if (!projectId) return;
    const req = { project_id: projectId, slide_id: slideId || undefined, tone };
    setActionLoading("regenerateNotes", req);
    try {
      const res = await apiClient.regenerateNotes(baseUrl, {
        project_id: projectId,
        slide_id: slideId || undefined,
      });
      setRegenerateNotesResult(res);
      setActionSuccess("regenerateNotes", res as unknown as Record<string, unknown>);
    } catch (error) {
      setActionError("regenerateNotes", toErrorObject(error));
    }
  };

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-zinc-900">Regeneration Panel</h2>
      <p className="mt-1 text-xs text-zinc-600">Regenerate one slide or slide notes.</p>

      <div className="mt-3 space-y-2">
        <input
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
          placeholder="slide_id"
          value={slideId}
          onChange={(e) => setSlideId(e.target.value)}
        />
        <input
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
          placeholder="tone"
          value={tone}
          onChange={(e) => setTone(e.target.value)}
        />
        <label className="flex items-center gap-2 text-sm text-zinc-700">
          <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
          force
        </label>
      </div>

      <div className="mt-2 text-xs text-zinc-500">Current project_id: {projectId || "(none)"}</div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <button
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:opacity-50"
          disabled={!projectId || !slideId || actionStatus.regenerateSlide === "loading"}
          onClick={runRegenerateSlide}
        >
          {actionStatus.regenerateSlide === "loading" ? "Running..." : "Regenerate Slide"}
        </button>
        <button
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:opacity-50"
          disabled={!projectId || actionStatus.regenerateNotes === "loading"}
          onClick={runRegenerateNotes}
        >
          {actionStatus.regenerateNotes === "loading" ? "Running..." : "Regenerate Notes"}
        </button>
      </div>
    </section>
  );
}

