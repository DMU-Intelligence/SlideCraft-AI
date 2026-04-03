import type {
  GenerateAllRequest,
  GenerateAllResponse,
  GenerateNotesRequest,
  GenerateNotesResponse,
  GenerateOutlineRequest,
  GenerateOutlineResponse,
  GenerateSlidesRequest,
  GenerateSlidesResponse,
  IngestDocumentResponse,
  RegenerateNotesRequest,
  RegenerateNotesResponse,
  RegenerateSlideRequest,
  RegenerateSlideResponse,
} from "@/types/api";

async function parseResponse(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { raw: text };
  }
}

async function requestJson<T>(baseUrl: string, path: string, body: unknown): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await parseResponse(res);
  if (!res.ok) {
    throw {
      status: res.status,
      statusText: res.statusText,
      payload,
    };
  }
  return payload as T;
}

export interface IngestDocumentInput {
  file: File;
  projectId?: string;
  title?: string;
  language?: string;
  tone?: string;
  maxChunkChars?: number;
  chunkOverlap?: number;
  userEditedSlideIds?: string[];
}

export const apiClient = {
  async ingestDocument(baseUrl: string, input: IngestDocumentInput): Promise<IngestDocumentResponse> {
    const form = new FormData();
    form.append("file", input.file);
    if (input.projectId) form.append("project_id", input.projectId);
    if (input.title) form.append("title", input.title);
    if (input.language) form.append("language", input.language);
    if (input.tone) form.append("tone", input.tone);
    if (typeof input.maxChunkChars === "number") form.append("max_chunk_chars", String(input.maxChunkChars));
    if (typeof input.chunkOverlap === "number") form.append("chunk_overlap", String(input.chunkOverlap));
    if (input.userEditedSlideIds?.length) {
      form.append("user_edited_slide_ids", JSON.stringify(input.userEditedSlideIds));
    }

    const res = await fetch(`${baseUrl}/ingest/document`, {
      method: "POST",
      body: form,
    });

    const payload = await parseResponse(res);
    if (!res.ok) {
      throw {
        status: res.status,
        statusText: res.statusText,
        payload,
      };
    }

    return payload as IngestDocumentResponse;
  },

  generateOutline(baseUrl: string, payload: GenerateOutlineRequest) {
    return requestJson<GenerateOutlineResponse>(baseUrl, "/generate/outline", payload);
  },

  generateSlides(baseUrl: string, payload: GenerateSlidesRequest) {
    return requestJson<GenerateSlidesResponse>(baseUrl, "/generate/slides", payload);
  },

  generateNotes(baseUrl: string, payload: GenerateNotesRequest) {
    return requestJson<GenerateNotesResponse>(baseUrl, "/generate/notes", payload);
  },

  generateAll(baseUrl: string, payload: GenerateAllRequest) {
    return requestJson<GenerateAllResponse>(baseUrl, "/generate/all", payload);
  },

  regenerateSlide(baseUrl: string, payload: RegenerateSlideRequest) {
    return requestJson<RegenerateSlideResponse>(baseUrl, "/regenerate/slide", payload);
  },

  regenerateNotes(baseUrl: string, payload: RegenerateNotesRequest) {
    return requestJson<RegenerateNotesResponse>(baseUrl, "/regenerate/notes", payload);
  },
};

