import { NextResponse } from "next/server";
import { getBackendBaseUrl, toErrorPayload, BACKEND_TIMEOUT } from "@/lib/backend";

export const maxDuration = 600;

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const backendRes = await fetch(`${getBackendBaseUrl()}/export/pptx`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(BACKEND_TIMEOUT),
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