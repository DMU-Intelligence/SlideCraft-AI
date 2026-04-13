/** Shared backend utilities for API routes */

export function getBackendBaseUrl(): string {
  const raw =
    process.env.BACKEND_BASE_URL ||
    process.env.NEXT_PUBLIC_BACKEND_BASE_URL;

  if (!raw) {
    throw new Error(
      "BACKEND_BASE_URL 또는 NEXT_PUBLIC_BACKEND_BASE_URL 환경변수를 설정해주세요."
    );
  }

  try {
    return new URL(raw).toString().replace(/\/$/, "");
  } catch {
    throw new Error("BACKEND_BASE_URL 또는 NEXT_PUBLIC_BACKEND_BASE_URL 설정이 올바르지 않습니다.");
  }
}

export async function toErrorPayload(
  response: Response
): Promise<{ error: string }> {
  const text = await response.text();
  if (!text) {
    return { error: `Backend error (${response.status})` };
  }
  try {
    const parsed = JSON.parse(text) as {
      detail?: unknown;
      message?: unknown;
      error?: unknown;
    };
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

/** 10-minute timeout for long-running LLM calls */
export const BACKEND_TIMEOUT = 10 * 60 * 1000;
