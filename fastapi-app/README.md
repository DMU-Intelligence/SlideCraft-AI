# fastapi-app

## Run (PowerShell)

```powershell
cd c:\SlideCraft_AI\fastapi-app
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` or `http://127.0.0.1:8000/docs`.

## Install deps (reproducible)

```powershell
cd c:\SlideCraft_AI\fastapi-app
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Example Requests (JSON)

### 1) `POST /ingest/document` (JSON, `file_path` 사용)

```json
{
  "project_id": "proj_1",
  "title": "My SlideCraft AI Deck",
  "language": "en",
  "tone": "professional",
  "file_path": "C:\\path\\to\\document.pdf",
  "max_chunk_chars": 1200,
  "chunk_overlap": 150,
  "user_edited_slide_ids": ["slide_02"]
}
```

### Response (예시)

```json
{
  "project_id": "proj_1",
  "raw_text": "....",
  "chunks": [
    {
      "chunk_id": "chunk_001",
      "text": "....",
      "heading": null,
      "start_char": 0,
      "end_char": 1234
    }
  ],
  "summary": "....",
  "metadata": {
    "source_filename": "document.pdf",
    "file_type": "pdf",
    "parser_version": "mvp-1",
    "extra": {
      "chunk_count": 10
    }
  },
  "stats": {
    "char_count": 99999,
    "chunk_count": 10
  }
}
```

### 2) `POST /generate/outline`

```json
{ "project_id": "proj_1" }
```

### 3) `POST /generate/slides`

```json
{ "project_id": "proj_1", "max_slides": 8 }
```

### 4) `POST /generate/notes`

```json
{ "project_id": "proj_1" }
```

### 5) `POST /generate/all`

```json
{ "project_id": "proj_1", "max_slides": 8 }
```

## Example Requests (Partial Regeneration)

### 6) `POST /regenerate/slide`

```json
{
  "project_id": "proj_1",
  "slide_id": "slide_03",
  "force": false,
  "user_edited_slide_ids": ["slide_03"]
}
```

### 7) `POST /regenerate/notes`

```json
{
  "project_id": "proj_1",
  "slide_id": "slide_03",
  "slide_ids": []
}
```

