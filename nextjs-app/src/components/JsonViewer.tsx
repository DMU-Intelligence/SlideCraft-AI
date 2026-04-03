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
      // No-op for browsers where clipboard access is blocked.
    }
  };

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-900">{title}</h3>
        <button
          className="rounded-md border border-zinc-300 px-2 py-1 text-xs text-zinc-700 disabled:opacity-50"
          onClick={copy}
          disabled={!text}
        >
          Copy
        </button>
      </div>
      <pre className="max-h-[260px] overflow-auto rounded-md bg-zinc-950 p-3 text-xs leading-5 text-zinc-100">
        {text || "// empty"}
      </pre>
    </section>
  );
}

