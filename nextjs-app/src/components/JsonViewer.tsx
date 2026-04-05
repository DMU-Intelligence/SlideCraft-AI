"use client";

import { prettyJson } from "@/lib/utils";

interface JsonViewerProps {
  title: string;
  data: unknown;
}

export function JsonViewer({ title, data }: JsonViewerProps) {
  const text = prettyJson(data);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text || "");
    } catch {
      // Clipboard may be blocked.
    }
  };

  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-5 shadow-lg md:p-6">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
        <button
          type="button"
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:border-blue-200 hover:bg-blue-50/50 disabled:opacity-50"
          onClick={copy}
          disabled={!text}
        >
          복사
        </button>
      </div>
      <pre className="max-h-[260px] overflow-auto rounded-xl border border-gray-900/10 bg-slate-950 p-4 text-xs leading-5 text-slate-100">
        {text || "// empty"}
      </pre>
    </section>
  );
}
