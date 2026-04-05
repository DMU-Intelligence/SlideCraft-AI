"use client";

import { truncate } from "@/lib/utils";
import { useApiTestStore } from "@/store/useApiTestStore";

export function ProjectStateViewer() {
  const projectId = useApiTestStore((state) => state.currentProjectId);
  const ingest = useApiTestStore((state) => state.ingestResult);
  const outline = useApiTestStore((state) => state.outlineResult);
  const slides = useApiTestStore((state) => state.slidesResult);
  const notes = useApiTestStore((state) => state.notesResult);
  const generateAll = useApiTestStore((state) => state.generateAllResult);
  const regenSlide = useApiTestStore((state) => state.regenerateSlideResult);

  const effectiveOutline = generateAll?.outline ?? outline?.outline ?? {};
  const effectiveSlides = generateAll?.slides ?? slides?.slides ?? (regenSlide?.slide ? [regenSlide.slide] : []);
  const effectiveNotes = generateAll?.notes ?? notes?.notes ?? "";
  const outlineTitles = Object.keys(effectiveOutline);

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-zinc-900">State Viewer</h2>
      <div className="mt-3 space-y-2 text-sm text-zinc-800">
        <div>
          <span className="font-semibold">project_id:</span> {projectId || "(none)"}
        </div>
        <div>
          <span className="font-semibold">title:</span> {ingest?.title || "(none)"}
        </div>
        <div>
          <span className="font-semibold">content preview:</span>{" "}
          {truncate(ingest?.content ?? "", 200) || "(empty)"}
        </div>
        <div>
          <span className="font-semibold">outline titles:</span>{" "}
          {outlineTitles.length ? outlineTitles.join(" | ") : "(none)"}
        </div>
        <div>
          <span className="font-semibold">slides:</span> {effectiveSlides.length}
        </div>
        <div>
          <span className="font-semibold">notes preview:</span>{" "}
          {truncate(typeof effectiveNotes === "string" ? effectiveNotes : "", 120) || "(empty)"}
        </div>
      </div>
    </section>
  );
}
