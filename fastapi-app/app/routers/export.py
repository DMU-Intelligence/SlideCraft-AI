from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ..models.project_state import ProjectState
from ..services.pptx_service import PptxGenerator

router = APIRouter(tags=["export"])

_pptx_generator = PptxGenerator()


@router.post("/export/pptx")
async def export_pptx(request: Request) -> Response:
    """
    저장된 프로젝트의 슬라이드와 노트를 기반으로
    .pptx 파일을 생성하여 다운로드합니다.

    Body (JSON):
        project_id (str): 대상 프로젝트 ID
        filename   (str, optional): 저장 파일명 (기본값: 프로젝트 제목)

    Returns:
        application/vnd.openxmlformats-officedocument.presentationml.presentation
    """
    body = await request.json()
    project_id: str = body.get("project_id", "")
    custom_filename: str = body.get("filename", "")

    if not project_id:
        raise HTTPException(status_code=422, detail="project_id는 필수입니다.")

    repo = request.app.state.project_repository
    state: ProjectState | None = await repo.get(project_id)

    if state is None:
        raise HTTPException(status_code=404, detail=f"프로젝트를 찾을 수 없습니다: {project_id}")

    if not state.slides:
        raise HTTPException(
            status_code=400,
            detail="슬라이드가 생성되지 않았습니다. /generate/slides 또는 /generate/all을 먼저 호출하세요.",
        )

    # PPTX 생성
    pptx_bytes = _pptx_generator.generate(state)

    # 파일명 결정 (특수문자 제거)
    safe_title = "".join(c for c in state.title if c.isalnum() or c in " _-").strip()
    filename = custom_filename or f"{safe_title or 'presentation'}.pptx"
    if not filename.endswith(".pptx"):
        filename += ".pptx"

    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pptx_bytes)),
        },
    )