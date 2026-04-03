"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type {
  GenerateAllResponse,
  GenerateNotesResponse,
  GenerateOutlineResponse,
  GenerateSlidesResponse,
  IngestDocumentResponse,
  RegenerateNotesResponse,
  RegenerateSlideResponse,
} from "@/types/api";

type ActionKey =
  | "ingest"
  | "generateOutline"
  | "generateSlides"
  | "generateNotes"
  | "generateAll"
  | "regenerateSlide"
  | "regenerateNotes";

type RequestState = Record<string, unknown> | null;
type ResponseState = Record<string, unknown> | null;
type ErrorState = Record<string, unknown> | null;
type LogItem = {
  id: string;
  at: string;
  action: ActionKey;
  status: "loading" | "success" | "error";
  message: string;
};

interface ApiTestState {
  backendBaseUrl: string;
  currentProjectId: string;

  ingestResult: IngestDocumentResponse | null;
  outlineResult: GenerateOutlineResponse | null;
  slidesResult: GenerateSlidesResponse | null;
  notesResult: GenerateNotesResponse | null;
  generateAllResult: GenerateAllResponse | null;
  regenerateSlideResult: RegenerateSlideResponse | null;
  regenerateNotesResult: RegenerateNotesResponse | null;

  latestRequest: RequestState;
  latestResponse: ResponseState;
  latestError: ErrorState;
  logs: LogItem[];
  actionStatus: Record<ActionKey, "idle" | "loading" | "success" | "error">;

  setBackendBaseUrl: (url: string) => void;
  setCurrentProjectId: (id: string) => void;

  setActionLoading: (action: ActionKey, request: RequestState) => void;
  setActionSuccess: (action: ActionKey, response: ResponseState) => void;
  setActionError: (action: ActionKey, error: ErrorState) => void;

  setIngestResult: (result: IngestDocumentResponse) => void;
  setOutlineResult: (result: GenerateOutlineResponse) => void;
  setSlidesResult: (result: GenerateSlidesResponse) => void;
  setNotesResult: (result: GenerateNotesResponse) => void;
  setGenerateAllResult: (result: GenerateAllResponse) => void;
  setRegenerateSlideResult: (result: RegenerateSlideResponse) => void;
  setRegenerateNotesResult: (result: RegenerateNotesResponse) => void;
}

const defaultStatus: ApiTestState["actionStatus"] = {
  ingest: "idle",
  generateOutline: "idle",
  generateSlides: "idle",
  generateNotes: "idle",
  generateAll: "idle",
  regenerateSlide: "idle",
  regenerateNotes: "idle",
};

export const useApiTestStore = create<ApiTestState>()(
  persist(
    (set) => ({
      backendBaseUrl: "http://127.0.0.1:8000",
      currentProjectId: "",

      ingestResult: null,
      outlineResult: null,
      slidesResult: null,
      notesResult: null,
      generateAllResult: null,
      regenerateSlideResult: null,
      regenerateNotesResult: null,

      latestRequest: null,
      latestResponse: null,
      latestError: null,
      logs: [],
      actionStatus: defaultStatus,

      setBackendBaseUrl: (url) => set({ backendBaseUrl: url }),
      setCurrentProjectId: (id) => set({ currentProjectId: id }),

      setActionLoading: (action, request) =>
        set((state) => ({
          latestRequest: request,
          latestError: null,
          logs: [
            {
              id: `${Date.now()}_${Math.random()}`,
              at: new Date().toISOString(),
              action,
              status: "loading",
              message: `${action} started`,
            },
            ...state.logs,
          ].slice(0, 100),
          actionStatus: { ...state.actionStatus, [action]: "loading" },
        })),
      setActionSuccess: (action, response) =>
        set((state) => ({
          latestResponse: response,
          latestError: null,
          logs: [
            {
              id: `${Date.now()}_${Math.random()}`,
              at: new Date().toISOString(),
              action,
              status: "success",
              message: `${action} succeeded`,
            },
            ...state.logs,
          ].slice(0, 100),
          actionStatus: { ...state.actionStatus, [action]: "success" },
        })),
      setActionError: (action, error) =>
        set((state) => ({
          latestError: error,
          logs: [
            {
              id: `${Date.now()}_${Math.random()}`,
              at: new Date().toISOString(),
              action,
              status: "error",
              message: `${action} failed`,
            },
            ...state.logs,
          ].slice(0, 100),
          actionStatus: { ...state.actionStatus, [action]: "error" },
        })),

      setIngestResult: (result) => set({ ingestResult: result, currentProjectId: result.project_id }),
      setOutlineResult: (result) => set({ outlineResult: result, currentProjectId: result.project_id }),
      setSlidesResult: (result) => set({ slidesResult: result, currentProjectId: result.project_id }),
      setNotesResult: (result) => set({ notesResult: result, currentProjectId: result.project_id }),
      setGenerateAllResult: (result) => set({ generateAllResult: result, currentProjectId: result.project_id }),
      setRegenerateSlideResult: (result) => set({ regenerateSlideResult: result, currentProjectId: result.project_id }),
      setRegenerateNotesResult: (result) => set({ regenerateNotesResult: result, currentProjectId: result.project_id }),
    }),
    {
      name: "slidecraft-api-test-store",
      partialize: (state) => ({
        backendBaseUrl: state.backendBaseUrl,
        currentProjectId: state.currentProjectId,
        ingestResult: state.ingestResult,
        outlineResult: state.outlineResult,
        slidesResult: state.slidesResult,
        notesResult: state.notesResult,
        generateAllResult: state.generateAllResult,
        regenerateSlideResult: state.regenerateSlideResult,
        regenerateNotesResult: state.regenerateNotesResult,
        logs: state.logs,
      }),
    }
  )
);

