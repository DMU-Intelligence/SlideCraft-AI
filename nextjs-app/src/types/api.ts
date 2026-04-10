export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export interface IngestDocumentResponse {
  project_id: number;
  title: string;
  language: string;
  content: string;
  metadata?: {
    source_filename?: string | null;
    file_type?: string | null;
    parser_version?: string | null;
    extra?: Record<string, unknown>;
  };
  stats?: Record<string, unknown>;
}

export interface OutlineItem {
  id: string;
  role: string;
  goal: string;
  key_points: string[];
  tone: string;
  description: string;
  page_size: number;
  preferred_variant?: string | null;
}

export interface TextBoxElement {
  type: "text_box";
  text: string;
  left: number;
  top: number;
  width: number;
  height: number;
  font_name: string;
  font_size: number;
  font_bold: boolean;
  font_color: string;
  align: "left" | "center" | "right";
}

export interface ShapeElement {
  type: "shape";
  shape_type: "rectangle" | "round_rectangle";
  left: number;
  top: number;
  width: number;
  height: number;
  fill_color: string;
}

export interface BulletListElement {
  type: "bullet_list";
  left: number;
  top: number;
  width: number;
  height: number;
  items: string[];
  bullet_char: string;
  bullet_color: string;
  font_name: string;
  font_size: number;
  font_color: string;
}

export type SlideElement = TextBoxElement | ShapeElement | BulletListElement;

export interface PageLayout {
  background: string;
  elements: SlideElement[];
  slots: Record<string, JsonValue>;
}

export interface SlideContent {
  title: string;
  theme: "clean_light" | "bold_dark" | "editorial";
  slide_variant:
    | "title_page"
    | "content_box_list"
    | "content_two_panel"
    | "content_sidebar"
    | "content_split_band"
    | "content_compact"
    | "closing_page"
    | "title"
    | "section"
    | "summary"
    | "two_column";
  pages: PageLayout[];
}

export interface SlideEvaluation {
  passed: boolean;
  score: number;
  checklist: string[];
  issues: string[];
  feedback: string;
}

export interface GenerateOutlineRequest {
  project_id: number | string;
}

export interface GenerateOutlineResponse {
  project_id: number;
  outline: Record<string, OutlineItem>;
}

export interface GenerateSlidesRequest {
  project_id: number | string;
  max_slides?: number;
}

export interface GenerateSlidesResponse {
  project_id: number;
  slides: SlideContent[];
}

export interface GenerateNotesRequest {
  project_id: number | string;
}

export interface GenerateNotesResponse {
  project_id: number;
  notes: string;
}

export interface GenerateAllRequest {
  project_id: number | string;
  max_slides?: number;
}

export interface GenerateAllResponse {
  project_id: number;
  outline: Record<string, OutlineItem>;
  slides: SlideContent[];
  notes: string;
  stats?: Record<string, unknown>;
}

export interface RegenerateSlideRequest {
  project_id: number | string;
  slide_title: string;
  user_request?: string;
}

export interface RegenerateSlideResponse {
  project_id: number;
  slide: SlideContent;
}

export interface RegenerateNotesRequest {
  project_id: number | string;
}

export interface RegenerateNotesResponse {
  project_id: number;
  notes: string;
}
