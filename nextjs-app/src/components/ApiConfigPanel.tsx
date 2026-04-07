"use client";

import { useState } from "react";
import { useApiTestStore } from "@/store/useApiTestStore";

export function ApiConfigPanel() {
  const baseUrl = useApiTestStore((s) => s.backendBaseUrl);
  const setBaseUrl = useApiTestStore((s) => s.setBackendBaseUrl);
  const [localUrl, setLocalUrl] = useState(baseUrl);

  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-5 shadow-lg md:p-6">
      <h2 className="text-sm font-semibold text-gray-900">API 서버 주소</h2>
      <p className="mt-1 text-xs text-gray-600">로컬 FastAPI 베이스 URL (예: http://127.0.0.1:8000)</p>
      <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:gap-3">
        <input
          className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-gray-900 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
          value={localUrl}
          onChange={(e) => setLocalUrl(e.target.value)}
          placeholder="http://127.0.0.1:8000"
        />
        <button
          type="button"
          className="shrink-0 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-md transition-all hover:from-blue-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:from-gray-300 disabled:to-gray-300"
          onClick={() => setBaseUrl(localUrl.trim())}
          disabled={!localUrl.trim()}
        >
          저장
        </button>
      </div>
      <p className="mt-2 text-xs text-gray-500">현재: {baseUrl}</p>
    </section>
  );
}
