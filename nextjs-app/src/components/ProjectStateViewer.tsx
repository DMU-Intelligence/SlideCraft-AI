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
  const regenNotes = useApiTestStore((state) => state.regenerateNotesResult);

  const effectiveOutline = generateAll?.outline ?? outline?.outline ?? {};
  const effectiveSlides = generateAll?.slides ?? slides?.slides ?? (regenSlide?.slide ? [regenSlide.slide] : []);
  const effectiveNotes =
    (generateAll?.notes != null ? generateAll.notes : null) ??
    (notes?.notes != null ? notes.notes : null) ??
    regenNotes?.notes ??
    "";
  const outlineTitles = Object.keys(effectiveOutline);
  const firstSlide = effectiveSlides[0];
  const firstPage = firstSlide?.pages?.[0];
  const slotKeys = firstPage?.slots ? Object.keys(firstPage.slots) : [];

  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-5 shadow-lg md:p-6">
      <h2 className="text-sm font-semibold text-gray-900">프로젝트 상태</h2>
      <div className="mt-4 space-y-2 text-sm text-gray-800">
        <div>
          <span className="font-semibold text-gray-900">project_id:</span> {projectId || "(없음)"}
        </div>
        <div>
          <span className="font-semibold text-gray-900">title:</span> {ingest?.title || "(없음)"}
        </div>
        <div>
          <span className="font-semibold text-gray-900">content 미리보기:</span>{" "}
          {truncate(ingest?.content ?? "", 200) || "(비어 있음)"}
        </div>
        <div>
          <span className="font-semibold text-gray-900">아웃라인:</span>{" "}
          {outlineTitles.length ? outlineTitles.join(" · ") : "(없음)"}
        </div>
        <div>
          <span className="font-semibold text-gray-900">슬라이드 수:</span> {effectiveSlides.length}
        </div>
        <div>
          <span className="font-semibold text-gray-900">테마:</span> {firstSlide?.theme || "(없음)"}
        </div>
        <div>
          <span className="font-semibold text-gray-900">variant:</span> {firstSlide?.slide_variant || "(없음)"}
        </div>
        <div>
          <span className="font-semibold text-gray-900">슬롯 키:</span> {slotKeys.length ? slotKeys.join(" · ") : "(없음)"}
        </div>
        <div>
          <span className="font-semibold text-gray-900">노트 미리보기:</span>{" "}
          {truncate(typeof effectiveNotes === "string" ? effectiveNotes : "", 120) || "(비어 있음)"}
        </div>
      </div>
    </section>
  );
}
