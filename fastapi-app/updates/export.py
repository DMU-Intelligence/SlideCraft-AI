from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from ..models.project_state import ProjectState
from ..services.pptx_service import PptxGenerator

router = APIRouter(tags=["export"])

_pptx_generator = PptxGenerator()


class ExportPptxRequest(BaseModel):
    project_id: int
    filename: str | None = None


@router.post("/export/pptx")
async def export_pptx(req: ExportPptxRequest, request: Request) -> Response:
    """슬라이드 기반 PPTX 파일 반환 (notes는 포함되지 않음)"""
    repo = request.app.state.project_repository
    state: ProjectState | None = await repo.get(req.project_id)

    if state is None:
        raise HTTPException(
            status_code=404, detail=f"프로젝트를 찾을 수 없습니다: {req.project_id}"
        )
    if not state.slides:
        raise HTTPException(
            status_code=400,
            detail="슬라이드가 없습니다. /generate/slides 또는 /generate/all을 먼저 호출하세요.",
        )

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
