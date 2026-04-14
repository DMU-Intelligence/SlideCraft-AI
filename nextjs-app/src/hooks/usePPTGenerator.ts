"use client";

import { useState, useCallback } from "react";
import type {
  GenerateAllResponse,
  IngestDocumentResponse,
  Phase,
  ResultSlide,
} from "@/types/api";

const TIMEOUT = 10 * 60 * 1000; // 10 minutes

function getBackendUrl(): string {
  const raw = process.env.NEXT_PUBLIC_BACKEND_BASE_URL?.trim();

  if (!raw) {
    return "";
  }

  try {
    const parsed = new URL(raw);
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return "";
  }
}

// ── Fetch helper ──────────────────────────────────────────────────────────────

async function safeFetch(url: string, options: RequestInit = {}) {
  const res = await fetch(url, {
    ...options,
    signal: AbortSignal.timeout(TIMEOUT),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error (${res.status}): ${text.slice(0, 200)}`);
  }
  return res.json();
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function usePPTGenerator() {
  const backendUrl = getBackendUrl();

  // state
  const [phase, setPhase] = useState<Phase>("upload");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [presentationTitle, setPresentationTitle] = useState("");
  const [projectId, setProjectId] = useState<number | null>(null);
  const [slides, setSlides] = useState<ResultSlide[]>([]);
  const [script, setScript] = useState("");
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [generatePending, setGeneratePending] = useState(false);
  const [downloadPending, setDownloadPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingMessage, setLoadingMessage] = useState("");

  // ── Generate ────────────────────────────────────────────────────────────────

  const generate = useCallback(async () => {
    if (!uploadedFile || !presentationTitle || generatePending) return;

    if (!backendUrl) {
      setError("NEXT_PUBLIC_BACKEND_BASE_URL 환경변수가 올바르게 설정되지 않았습니다.");
      return;
    }

    setPhase("loading");
    setGeneratePending(true);
    setError(null);

    try {
      setLoadingMessage("\uBB38\uC11C\uB97C \uBD84\uC11D\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4...");

      const formData = new FormData();
      formData.append("file", uploadedFile);
      formData.append("title", presentationTitle);
      formData.append("language", "ko");

      const ingestData = (await safeFetch(`${backendUrl}/ingest/document`, {
        method: "POST",
        body: formData,
      })) as IngestDocumentResponse;

      const newProjectId = ingestData.project_id;
      setProjectId(newProjectId);

      setLoadingMessage("\uC2AC\uB77C\uC774\uB4DC\uB97C \uADF8\uB9AC\uACE0 \uC788\uC2B5\uB2C8\uB2E4...");

      const generateData = (await safeFetch(`${backendUrl}/generate/all`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: newProjectId }),
      })) as GenerateAllResponse;

      setLoadingMessage("\uB300\uBCF8\uC744 \uC791\uC131 \uC911\uC785\uB2C8\uB2E4...");

      const formattedSlides: ResultSlide[] = generateData.slides.map(
        (slide, index) => ({
          id: index + 1,
          ...slide,
        })
      );

      setSlides(formattedSlides);
      setScript(generateData.notes);
      setCurrentSlideIndex(0);

      await new Promise((r) => setTimeout(r, 600));
      setPhase("result");
    } catch (err) {
      console.error("Generation error:", err);
      setError(
        err instanceof Error ? err.message : "\uC54C \uC218 \uC5C6\uB294 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4."
      );
      setPhase("upload");
    } finally {
      setGeneratePending(false);
    }
  }, [uploadedFile, presentationTitle, generatePending, backendUrl]);

  // ── Download ────────────────────────────────────────────────────────────────

  const download = useCallback(async () => {
    if (!projectId || downloadPending) return;

    if (!backendUrl) {
      setError("NEXT_PUBLIC_BACKEND_BASE_URL 환경변수가 올바르게 설정되지 않았습니다.");
      return;
    }

    setDownloadPending(true);
    setError(null);
    try {
      const res = await fetch(`${backendUrl}/export/pptx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId }),
        signal: AbortSignal.timeout(TIMEOUT),
      });

      if (!res.ok) throw new Error("\uB2E4\uC6B4\uB85C\uB4DC \uC2E4\uD328");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${presentationTitle || "presentation"}.pptx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download error:", err);
      setError(
        err instanceof Error
          ? err.message
          : "\uB2E4\uC6B4\uB85C\uB4DC \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4."
      );
    } finally {
      setDownloadPending(false);
    }
  }, [projectId, downloadPending, presentationTitle, backendUrl]);

  // ── Navigation ──────────────────────────────────────────────────────────────

  const goToSlide = useCallback(
    (index: number) => {
      if (index >= 0 && index < slides.length) setCurrentSlideIndex(index);
    },
    [slides.length]
  );

  const nextSlide = useCallback(
    () => goToSlide(currentSlideIndex + 1),
    [currentSlideIndex, goToSlide]
  );

  const prevSlide = useCallback(
    () => goToSlide(currentSlideIndex - 1),
    [currentSlideIndex, goToSlide]
  );

  // ── Reset ───────────────────────────────────────────────────────────────────

  const reset = useCallback(() => {
    setPhase("upload");
    setUploadedFile(null);
    setPresentationTitle("");
    setSlides([]);
    setScript("");
    setCurrentSlideIndex(0);
    setProjectId(null);
    setError(null);
  }, []);

  return {
    phase,
    uploadedFile,
    presentationTitle,
    slides,
    script,
    currentSlideIndex,
    generatePending,
    downloadPending,
    error,
    loadingMessage,
    setUploadedFile,
    setPresentationTitle,
    generate,
    download,
    reset,
    nextSlide,
    prevSlide,
  };
}