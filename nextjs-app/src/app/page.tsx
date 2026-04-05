"use client";

import { ApiConfigPanel } from "@/components/ApiConfigPanel";
import { GenerationPanel } from "@/components/GenerationPanel";
import { IngestPanel } from "@/components/IngestPanel";
import { JsonViewer } from "@/components/JsonViewer";
import { LogsStatusViewer } from "@/components/LogsStatusViewer";
import { ProjectStateViewer } from "@/components/ProjectStateViewer";
import { RegenerationPanel } from "@/components/RegenerationPanel";
import { useApiTestStore } from "@/store/useApiTestStore";

export default function Home() {
  const latestRequest = useApiTestStore((s) => s.latestRequest);
  const latestResponse = useApiTestStore((s) => s.latestResponse);
  const latestError = useApiTestStore((s) => s.latestError);
  const outlineResult = useApiTestStore((s) => s.outlineResult);
  const slidesResult = useApiTestStore((s) => s.slidesResult);
  const notesResult = useApiTestStore((s) => s.notesResult);

  return (
    <main className="min-h-screen bg-zinc-100 p-4 md:p-6">
      <div className="mx-auto max-w-7xl">
        <header className="mb-4 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
          <h1 className="text-lg font-semibold text-zinc-900">SlideCraft AI - FastAPI Test Client</h1>
          <p className="mt-1 text-sm text-zinc-600">
            Developer-facing dashboard for local API testing.
          </p>
        </header>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1fr]">
          <div className="space-y-4">
            <ApiConfigPanel />
            <IngestPanel />
            <GenerationPanel />
            <RegenerationPanel />
          </div>

          <div className="space-y-4">
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
      </div>
    </main>
  );
}
