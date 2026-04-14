import { NextResponse } from "next/server";
import { getBackendBaseUrl, toErrorPayload, BACKEND_TIMEOUT } from "@/lib/backend";

export const maxDuration = 600;

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as { project_id?: number };
    const projectId = body.project_id;
    if (!projectId) {
      return NextResponse.json({ error: "project_id is required" }, { status: 400 });
    }

    const backendRes = await fetch(
      `${getBackendBaseUrl()}/export/notes/${encodeURIComponent(projectId)}`,
      {
        method: "GET",
        cache: "no-store",
        signal: AbortSignal.timeout(BACKEND_TIMEOUT),
      },
    );

    if (!backendRes.ok) {
      const payload = await toErrorPayload(backendRes);
      return NextResponse.json(payload, { status: backendRes.status });
    }

    const binary = await backendRes.arrayBuffer();
    return new NextResponse(binary, {
      status: 200,
      headers: {
        "Content-Type": backendRes.headers.get("content-type") || "text/plain; charset=utf-8",
        "Content-Disposition":
          backendRes.headers.get("content-disposition") ||
          'attachment; filename="notes.txt"',
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Notes export server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
