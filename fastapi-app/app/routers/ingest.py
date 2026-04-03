from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..models.project_state import ProjectState
from ..schemas.common import Metadata
from ..schemas.ingest import IngestDocumentRequest, IngestDocumentResponse
from ..utils.file_loader import save_upload_file, sanitize_filename

router = APIRouter(tags=["ingest"])


def _parse_user_edited_ids(value: str | None) -> list[str]:
    if not value:
        return []
    value = value.strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
            return parsed
    except json.JSONDecodeError:
        pass
    # Fallback: comma-separated.
    return [v.strip() for v in value.split(",") if v.strip()]


@router.post("/ingest/document", response_model=IngestDocumentResponse)
async def ingest_document(request: Request) -> IngestDocumentResponse:
    state_repo = request.app.state.project_repository
    document_parser = request.app.state.document_parser
    chunking_service = request.app.state.chunking_service
    summarizer = request.app.state.summarizer
    settings = request.app.state.settings

    content_type = request.headers.get("content-type", "")
    resolved_project_id: str
    resolved_title: str | None = None
    resolved_file_path: str | None = None
    original_filename: str | None = None
    language = "en"
    tone = "neutral"
    max_chunk_chars = 1200
    chunk_overlap = 150
    user_edited_slide_ids: str | None = None

    if "application/json" in content_type:
        payload = await request.json()
        ingest_req = IngestDocumentRequest.model_validate(payload)
        resolved_project_id = ingest_req.project_id or uuid.uuid4().hex
        resolved_title = ingest_req.title
        resolved_file_path = ingest_req.file_path
        language = ingest_req.language
        tone = ingest_req.tone
        max_chunk_chars = ingest_req.max_chunk_chars
        chunk_overlap = ingest_req.chunk_overlap
        user_edited_slide_ids = json.dumps(ingest_req.user_edited_slide_ids)
        if not resolved_file_path:
            raise HTTPException(status_code=422, detail="file_path is required for JSON requests.")
        original_filename = os.path.basename(resolved_file_path)
    else:
        form = await request.form()
        resolved_project_id = str(form.get("project_id") or uuid.uuid4().hex)
        resolved_title = form.get("title") or None
        resolved_file_path = form.get("file_path") or None
        language = str(form.get("language") or "en")
        tone = str(form.get("tone") or "neutral")
        max_chunk_chars = int(form.get("max_chunk_chars") or 1200)
        chunk_overlap = int(form.get("chunk_overlap") or 150)
        user_edited_slide_ids = form.get("user_edited_slide_ids") or None

        upload = form.get("file")
        if upload is not None:
            # Starlette UploadFile instance.
            original_filename = upload.filename or "upload"
            upload_filename = sanitize_filename(original_filename)
            dest_dir = Path(settings.upload_dir) / resolved_project_id
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = dest_dir / upload_filename
            await save_upload_file(upload, str(dest_path))
            resolved_file_path = str(dest_path)
            if not resolved_title:
                resolved_title = os.path.splitext(upload_filename)[0] or "Untitled"

    if not resolved_file_path:
        raise HTTPException(status_code=422, detail="Provide either file_path or an uploaded file.")

    if not resolved_title:
        resolved_title = os.path.splitext(original_filename or "Untitled")[0] or "Untitled"

    parsed_request = IngestDocumentRequest(
        project_id=resolved_project_id,
        title=resolved_title,
        language=language,
        tone=tone,
        file_path=resolved_file_path,
        max_chunk_chars=max_chunk_chars,
        chunk_overlap=chunk_overlap,
        user_edited_slide_ids=_parse_user_edited_ids(user_edited_slide_ids),
    )

    try:
        parsed_doc = await document_parser.parse_document(parsed_request.file_path or "")
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))

    chunks = await chunking_service.chunk_text(
        parsed_doc.text,
        max_chunk_chars=parsed_request.max_chunk_chars,
        chunk_overlap=parsed_request.chunk_overlap,
    )
    summary_result = await summarizer.summarize(chunks)

    state = ProjectState(
        project_id=parsed_request.project_id or resolved_project_id,
        title=parsed_request.title or "Untitled",
        language=parsed_request.language,
        tone=parsed_request.tone,
        source_document_text=parsed_doc.text,
        chunks=chunks,
        summary=summary_result["summary"],
        outline=None,
        slides=[],
        notes=[],
        user_edited_slide_ids=parsed_request.user_edited_slide_ids,
        metadata={
            "source_filename": original_filename,
            "source_document_metadata": parsed_doc.metadata,
        },
    )
    await state_repo.upsert(state)

    metadata = Metadata(
        source_filename=original_filename,
        file_type=parsed_doc.metadata.get("file_type"),
        parser_version="mvp-1",
        extra={"chunk_count": len(chunks)},
    )

    stats: dict[str, Any] = {
        "char_count": len(parsed_doc.text),
        "chunk_count": len(chunks),
    }
    return IngestDocumentResponse(
        project_id=state.project_id,
        raw_text=parsed_doc.text,
        chunks=chunks,
        summary=state.summary,
        metadata=metadata,
        stats=stats,
    )

