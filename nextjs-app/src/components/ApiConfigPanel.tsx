"use client";

import { useState } from "react";
import { useApiTestStore } from "@/store/useApiTestStore";

export function ApiConfigPanel() {
  const baseUrl = useApiTestStore((s) => s.backendBaseUrl);
  const setBaseUrl = useApiTestStore((s) => s.setBackendBaseUrl);
  const [localUrl, setLocalUrl] = useState(baseUrl);

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-zinc-900">API Base URL Config</h2>
      <p className="mt-1 text-xs text-zinc-600">
        FastAPI base URL for local development requests.
      </p>
      <div className="mt-3 flex gap-2">
        <input
          className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-zinc-500"
          value={localUrl}
          onChange={(e) => setLocalUrl(e.target.value)}
          placeholder="http://127.0.0.1:8000"
        />
        <button
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          onClick={() => setBaseUrl(localUrl.trim())}
          disabled={!localUrl.trim()}
        >
          Save
        </button>
      </div>
      <div className="mt-2 text-xs text-zinc-500">Current: {baseUrl}</div>
    </section>
  );
}

