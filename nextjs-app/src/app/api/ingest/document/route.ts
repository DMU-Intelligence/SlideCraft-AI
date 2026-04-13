import { NextResponse } from "next/server";
import { getBackendBaseUrl, toErrorPayload, BACKEND_TIMEOUT } from "@/lib/backend";

export const maxDuration = 600;

export async function POST(req: Request) {
  try {
    const incoming = await req.formData();
    const outbound = new FormData();

    for (const [key, value] of incoming.entries()) {
      if (typeof value === "string") {
        outbound.append(key, value);
      } else {
        outbound.append(key, value, value.name);
      }
    }

    const backendRes = await fetch(`${getBackendBaseUrl()}/ingest/document`, {
      method: "POST",
      body: outbound,
      cache: "no-store",
      signal: AbortSignal.timeout(BACKEND_TIMEOUT),
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