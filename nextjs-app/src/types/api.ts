export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type ApiRecord = Record<string, unknown>;

export interface ParsedChunk {
  chunk_id: string;
  text: string;
  heading?: string | null;
  start_char: number;
  end_char: number;
}

export interface IngestDocumentResponse {
  project_id: string;
  raw_text: string;
  chunks: ParsedChunk[];
  summary: string;
  metadata?: {
    source_filename?: string | null;
    file_type?: string | null;
    parser_version?: string | null;
    extra?: Record<string, unknown>;
  };
  stats?: Record<string, unknown>;
}

export interface PresentationOutlineItem {
  slide_number: number;
  title: string;
  goal: string;
}

export interface PresentationOutline {
  deck_title: string;
  presentation_objective: string;
  slide_outline: PresentationOutlineItem[];
}

export interface Slide {
  slide_id: string;
  title: string;
  goal: string;
  bullets: string[];
  source_chunk_ids: string[];
}

export interface SlideNotes {
  slide_id: string;
  notes: string;
}

export interface GenerateOutlineRequest {
  project_id: string;
}

export interface GenerateOutlineResponse {
  project_id: string;
  outline: PresentationOutline;
  summary: string;
}

export interface GenerateSlidesRequest {
  project_id: string;
  max_slides: number;
}

export interface GenerateSlidesResponse {
  project_id: string;
  slides: Slide[];
}

export interface GenerateNotesRequest {
  project_id: string;
}

export interface GenerateNotesResponse {
  project_id: string;
  notes: SlideNotes[];
}

export interface GenerateAllRequest {
  project_id: string;
  max_slides: number;
}

export interface GenerateAllResponse {
  project_id: string;
  outline: PresentationOutline;
  slides: Slide[];
  notes: SlideNotes[];
  summary: string;
  stats?: Record<string, unknown>;
}

export interface RegenerateSlideRequest {
  project_id: string;
  slide_id: string;
  force: boolean;
  user_edited_slide_ids?: string[];
}

export interface RegenerateSlideResponse {
  project_id: string;
  slide: Slide;
}

export interface RegenerateNotesRequest {
  project_id: string;
  slide_id?: string;
  slide_ids?: string[];
}

export interface RegenerateNotesResponse {
  project_id: string;
  notes: SlideNotes[];
}

