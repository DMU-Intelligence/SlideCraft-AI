from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile

from ..models.project_state import ProjectState
from ..schemas.common import Metadata
from ..schemas.ingest import IngestDocumentResponse
from ..utils.file_loader import sanitize_filename, save_upload_file

router = APIRouter(tags=["ingest"])


@router.post("/ingest/document", response_model=IngestDocumentResponse)
async def ingest_document(
    file: UploadFile,
    request: Request,
    project_id: Optional[str] = Form(default=None),
    title: Optional[str] = Form(default=None),
    language: str = Form(default="ko"),
    tone: str = Form(default="professional"),
    max_chunk_chars: int = Form(default=1200),
    chunk_overlap: int = Form(default=150),
) -> IngestDocumentResponse:
    """
    파일을 업로드하고 텍스트 추출 → 청킹 → 요약을 수행합니다.

    Form fields:
        file             : 업로드할 파일 (PDF 또는 텍스트)
        project_id       : 프로젝트 ID (미입력 시 자동 생성)
        title            : 프레젠테이션 제목 (미입력 시 파일명 사용)
        language         : 언어 코드 (기본값: "ko")
        tone             : 말투 스타일 (기본값: "professional")
        max_chunk_chars  : 청크 최대 글자 수 (기본값: 1200)
        chunk_overlap    : 청크 간 중복 글자 수 (기본값: 150)
    """
    state_repo = request.app.state.project_repository
    document_parser = request.app.state.document_parser
    chunking_service = request.app.state.chunking_service
    summarizer = request.app.state.summarizer
    settings = request.app.state.settings

    # ── 파일 저장 ────────────────────────────────────────────────────────────
    original_filename = file.filename or "upload"
    safe_filename = sanitize_filename(original_filename)

    resolved_project_id = project_id or uuid.uuid4().hex
    dest_dir = Path(settings.upload_dir) / resolved_project_id
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = dest_dir / safe_filename

    await save_upload_file(file, str(dest_path))

    # ── 제목 결정 ────────────────────────────────────────────────────────────
    resolved_title = title or os.path.splitext(safe_filename)[0] or "Untitled"

    # ── 문서 파싱 → 청킹 → 요약 ─────────────────────────────────────────────
    try:
        parsed_doc = await document_parser.parse_document(str(dest_path))
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))

    chunks = await chunking_service.chunk_text(
        parsed_doc.text,
        max_chunk_chars=max_chunk_chars,
        chunk_overlap=chunk_overlap,
    )
    summary_result = await summarizer.summarize(chunks)

    # ── ProjectState 생성 & 저장 ─────────────────────────────────────────────
    state = ProjectState(
        project_id=resolved_project_id,
        title=resolved_title,
        language=language,
        tone=tone,
        source_document_text=parsed_doc.text,
        chunks=chunks,
        summary=summary_result["summary"],
        outline=None,
        slides=[],
        notes=[],
        user_edited_slide_ids=[],
        metadata={
            "source_filename": original_filename,
            "source_document_metadata": parsed_doc.metadata,
        },
    )
    await state_repo.upsert(state)

    # ── 응답 ────────────────────────────────────────────────────────────────
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