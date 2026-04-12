from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..models.project_state import ProjectState
from ..schemas.regenerate import (
    RegenerateNotesRequest,
    RegenerateNotesResponse,
    RegenerateSlideRequest,
    RegenerateSlideResponse,
    UpdateOutlineRequest,
    UpdateOutlineResponse,
)

router = APIRouter(tags=["regenerate"])


@router.post("/regenerate/slide", response_model=RegenerateSlideResponse)
async def regenerate_slide(req: RegenerateSlideRequest, request: Request) -> RegenerateSlideResponse:
    repo = request.app.state.project_repository
    regeneration_service = request.app.state.regeneration_service

    state: ProjectState | None = await repo.get(req.project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")

    try:
        slide = await regeneration_service.regenerate_slide(
            state,
            slide_title=req.slide_title,
            user_request=req.user_request,
            template_name=req.template_name,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"템플릿 '{req.template_name}'을 찾을 수 없습니다.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    state.touch()
    await repo.upsert(state)
    return RegenerateSlideResponse(project_id=state.project_id, slide=slide)


@router.post("/regenerate/notes", response_model=RegenerateNotesResponse)
async def regenerate_notes(req: RegenerateNotesRequest, request: Request) -> RegenerateNotesResponse:
    repo = request.app.state.project_repository
    regeneration_service = request.app.state.regeneration_service

    state: ProjectState | None = await repo.get(req.project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")

    notes = await regeneration_service.regenerate_notes(state)
    state.touch()
    await repo.upsert(state)
    return RegenerateNotesResponse(project_id=state.project_id, notes=notes)


@router.post("/regenerate/outline", response_model=UpdateOutlineResponse)
async def update_outline(req: UpdateOutlineRequest, request: Request) -> UpdateOutlineResponse:
    repo = request.app.state.project_repository
    regeneration_service = request.app.state.regeneration_service

    state: ProjectState | None = await repo.get(req.project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")

    outline = await regeneration_service.update_outline(state, req.outline_titles)
    state.touch()
    await repo.upsert(state)
    return UpdateOutlineResponse(project_id=state.project_id, outline=outline)
