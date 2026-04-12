// src/app/api/generate/all/route.ts
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
    const backendRes = await fetch(`${getBackendBaseUrl()}/generate/all`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    if (!backendRes.ok) {
      const payload = await toErrorPayload(backendRes);
      return NextResponse.json(payload, { status: backendRes.status });
    }

    const data = (await backendRes.json()) as unknown;
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Server Error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}