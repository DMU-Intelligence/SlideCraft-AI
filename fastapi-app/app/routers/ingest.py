from __future__ import annotations

import os
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
    project_id: Optional[int] = Form(default=None),
    title: Optional[str] = Form(default=None),
    language: str = Form(default="ko"),
) -> IngestDocumentResponse:
    """
    파일을 업로드하고 텍스트 추출 → AI 텍스트 정리를 수행합니다.

    Form fields:
        file             : 업로드할 파일 (PDF 또는 텍스트)
        project_id       : 프로젝트 ID (미입력 시 자동 생성)
        title            : 프레젠테이션 제목 (미입력 시 파일명 사용)
        language         : 언어 코드 (기본값: "ko")
    """
    state_repo = request.app.state.project_repository
    document_parser = request.app.state.document_parser
    llm_client = request.app.state.llm_client
    settings = request.app.state.settings

    # ── 파일 저장 ────────────────────────────────────────────────────────────
    original_filename = file.filename or "upload"
    safe_filename = sanitize_filename(original_filename)

    resolved_project_id = project_id
    if resolved_project_id is None:
        resolved_project_id = await state_repo.next_id()

    dest_dir = Path(settings.upload_dir) / str(resolved_project_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = dest_dir / safe_filename

    await save_upload_file(file, str(dest_path))

    # ── 제목 결정 ────────────────────────────────────────────────────────────
    resolved_title = title or os.path.splitext(safe_filename)[0] or "Untitled"

    # ── 문서 파싱 → AI 텍스트 정리 ─────────────────────────────────────────────
    try:
        parsed_doc = await document_parser.parse_document(str(dest_path))
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cleaned_text = await llm_client.clean_text(parsed_doc.text, language)

    # ── ProjectState 생성 & 저장 ─────────────────────────────────────────────
    state = ProjectState(
        project_id=resolved_project_id,
        title=resolved_title,
        language=language,
        source_document_text=parsed_doc.text,
        content=cleaned_text,
        outline={},
        slides=[],
        notes="",
        metadata={
            "source_filename": original_filename,
            "source_document_metadata": parsed_doc.metadata,
            "presentation_goal": f"문서 '{resolved_title}'의 핵심 내용을 청중이 빠르게 이해하도록 구조화한다.",
            "target_audience": "해당 문서를 읽지 않았거나 배경지식이 많지 않을 수 있는 일반 청중",
            "slide_evaluations": {},
        },
    )
    await state_repo.upsert(state)

    # ── 응답 ────────────────────────────────────────────────────────────────
    metadata = Metadata(
        source_filename=original_filename,
        file_type=parsed_doc.metadata.get("file_type"),
        parser_version="mvp-1",
        extra={},
    )
    stats: dict[str, Any] = {
        "char_count": len(parsed_doc.text),
        "clean_char_count": len(cleaned_text),
    }

    return IngestDocumentResponse(
        project_id=state.project_id,
        title=state.title,
        language=state.language,
        content=state.content,
        metadata=metadata,
        stats=stats,
    )
