"use client";

import { truncate } from "@/lib/utils";
import { useApiTestStore } from "@/store/useApiTestStore";

export function ProjectStateViewer() {
  const projectId = useApiTestStore((s) => s.currentProjectId);
  const ingest = useApiTestStore((s) => s.ingestResult);
  const outline = useApiTestStore((s) => s.outlineResult);
  const slides = useApiTestStore((s) => s.slidesResult);
  const notes = useApiTestStore((s) => s.notesResult);
  const regenSlide = useApiTestStore((s) => s.regenerateSlideResult);
  const regenNotes = useApiTestStore((s) => s.regenerateNotesResult);

  const effectiveSlides = slides?.slides ?? (regenSlide?.slide ? [regenSlide.slide] : []);
  const effectiveNotes = notes?.notes ?? regenNotes?.notes ?? [];
  const outlineTitles = outline?.outline?.slide_outline?.map((item) => item.title) ?? [];
  const userEdited = ingest ? (ingest as Record<string, unknown>).user_edited_slide_ids : null;

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-zinc-900">State Viewer</h2>
      <div className="mt-3 space-y-2 text-sm text-zinc-800">
        <div>
          <span className="font-semibold">project_id:</span> {projectId || "(none)"}
        </div>
        <div>
          <span className="font-semibold">summary preview:</span>{" "}
          {truncate(ingest?.summary ?? outline?.summary ?? "", 200) || "(empty)"}
        </div>
        <div>
          <span className="font-semibold">outline titles:</span>{" "}
          {outlineTitles.length ? outlineTitles.join(" | ") : "(none)"}
        </div>
        <div>
          <span className="font-semibold">slides:</span> {effectiveSlides.length}
        </div>
        <div>
          <span className="font-semibold">notes:</span> {effectiveNotes.length}
        </div>
        <div>
          <span className="font-semibold">user edited slide ids:</span>{" "}
          {Array.isArray(userEdited) ? userEdited.join(", ") || "(none)" : "(unknown/none)"}
        </div>
      </div>
    </section>
  );
}

