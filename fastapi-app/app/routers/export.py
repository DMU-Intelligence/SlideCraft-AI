from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from ..models.project_state import ProjectState
from ..services.json_validation import validate_outline_payload, validate_slides_payload
from ..services.pptx_service import PptxGenerator

router = APIRouter(tags=["export"])
logger = logging.getLogger(__name__)

_pptx_generator = PptxGenerator()


class ExportPptxRequest(BaseModel):
    project_id: int
    filename: str | None = None


@router.post("/export/pptx")
async def export_pptx(req: ExportPptxRequest, request: Request) -> Response:
    repo = request.app.state.project_repository
    state: ProjectState | None = await repo.get(req.project_id)

    if state is None:
        raise HTTPException(status_code=404, detail=f"project not found: {req.project_id}")
    if not state.slides:
        raise HTTPException(
            status_code=400,
            detail="slides not found. Call /generate/slides or /generate/all first.",
        )

    outline_ok, outline_error = validate_outline_payload(
        {title: item.model_dump() for title, item in state.outline.items()}
    )
    if not outline_ok:
        message = f"{outline_error}가 잘못되었습니다 regenerate 해주세요"
        logger.error(message)
        raise HTTPException(status_code=400, detail=message)

    slides_ok, slides_error = validate_slides_payload(
        [slide.model_dump() for slide in state.slides]
    )
    if not slides_ok:
        message = f"{slides_error}가 잘못되었습니다 regenerate 해주세요"
        logger.error(message)
        raise HTTPException(status_code=400, detail=message)

    pptx_bytes = _pptx_generator.generate(state)

    filename = req.filename or state.title or "presentation"
    if not filename.endswith(".pptx"):
        filename += ".pptx"

    encoded = quote(filename, safe="")

    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
            "Content-Length": str(len(pptx_bytes)),
        },
    )


@router.get("/export/notes/{project_id}")
async def export_notes(project_id: int, request: Request) -> Response:
    repo = request.app.state.project_repository
    state: ProjectState | None = await repo.get(project_id)

    if state is None:
        raise HTTPException(status_code=404, detail=f"project not found: {project_id}")
    if not state.notes:
        raise HTTPException(status_code=404, detail="notes not found")

    base_title = (state.title or "presentation").strip() or "presentation"
    filename = f"{base_title}_대본.txt"
    encoded = quote(filename, safe="")
    notes_bytes = state.notes.encode("utf-8")

    return Response(
        content=notes_bytes,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
            "Content-Length": str(len(notes_bytes)),
        },
    )
