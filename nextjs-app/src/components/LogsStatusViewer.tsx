"use client";

import { useApiTestStore } from "@/store/useApiTestStore";

const statusColor: Record<string, string> = {
  loading: "bg-amber-100 text-amber-800",
  success: "bg-emerald-100 text-emerald-800",
  error: "bg-rose-100 text-rose-800",
};

export function LogsStatusViewer() {
  const logs = useApiTestStore((s) => s.logs);

  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-5 shadow-lg md:p-6">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">로그</h3>
        <span className="text-xs text-gray-500">{logs.length}건</span>
      </div>
      <div className="max-h-[240px] space-y-2 overflow-auto">
        {logs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-200 p-4 text-xs text-gray-500">아직 로그가 없습니다.</div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="rounded-xl border border-gray-100 bg-gray-50/50 p-3 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-gray-800">{log.action}</span>
                <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${statusColor[log.status] ?? "bg-gray-100 text-gray-700"}`}>
                  {log.status}
                </span>
              </div>
              <div className="mt-1 text-gray-600">{log.message}</div>
              <div className="mt-1 text-[11px] text-gray-400">{new Date(log.at).toLocaleString()}</div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
