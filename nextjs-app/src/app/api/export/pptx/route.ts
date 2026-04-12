// src/app/api/export/pptx/route.ts
import { NextResponse } from "next/server";

function getBackendBaseUrl(): string {
  return (process.env.BACKEND_BASE_URL || process.env.NEXT_PUBLIC_BACKEND_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

async function toErrorPayload(response: Response): Promise<{ error: string }> {
  const text = await response.text();
  if (!text) {
    return { error: `Backend error (${response.status})` };
  }
  try {
    const parsed = JSON.parse(text) as { detail?: unknown; message?: unknown; error?: unknown };
    const message =
      (typeof parsed.detail === "string" && parsed.detail) ||
      (typeof parsed.message === "string" && parsed.message) ||
      (typeof parsed.error === "string" && parsed.error) ||
      `Backend error (${response.status})`;
    return { error: message };
  } catch {
    return { error: text.slice(0, 500) };
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const backendRes = await fetch(`${getBackendBaseUrl()}/export/pptx`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    if (!backendRes.ok) {
      const payload = await toErrorPayload(backendRes);
      return NextResponse.json(payload, { status: backendRes.status });
    }

    const binary = await backendRes.arrayBuffer();
    return new NextResponse(binary, {
      status: 200,
      headers: {
        "Content-Type": backendRes.headers.get("content-type") || "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "Content-Disposition": backendRes.headers.get("content-disposition") || 'attachment; filename="presentation.pptx"',
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Download server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}