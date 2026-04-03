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
    <section className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-900">Logs / Status Viewer</h3>
        <span className="text-xs text-zinc-500">{logs.length} logs</span>
      </div>
      <div className="max-h-[240px] space-y-2 overflow-auto">
        {logs.length === 0 ? (
          <div className="rounded-md border border-dashed border-zinc-300 p-3 text-xs text-zinc-500">
            No logs yet.
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="rounded-md border border-zinc-200 p-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-medium text-zinc-800">{log.action}</span>
                <span className={`rounded-full px-2 py-0.5 ${statusColor[log.status] ?? "bg-zinc-100 text-zinc-700"}`}>
                  {log.status}
                </span>
              </div>
              <div className="mt-1 text-zinc-600">{log.message}</div>
              <div className="mt-1 text-zinc-400">{new Date(log.at).toLocaleString()}</div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

