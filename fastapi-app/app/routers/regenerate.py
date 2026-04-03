from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..models.project_state import ProjectState
from ..schemas.regenerate import (
    RegenerateNotesRequest,
    RegenerateNotesResponse,
    RegenerateSlideRequest,
    RegenerateSlideResponse,
)

router = APIRouter(tags=["regenerate"])


@router.post("/regenerate/slide", response_model=RegenerateSlideResponse)
async def regenerate_slide(req: RegenerateSlideRequest, request: Request) -> RegenerateSlideResponse:
    repo = request.app.state.project_repository
    regeneration_service = request.app.state.regeneration_service

    state: ProjectState | None = await repo.get(req.project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")

    if req.user_edited_slide_ids:
        existing = set(state.user_edited_slide_ids)
        for sid in req.user_edited_slide_ids:
            existing.add(sid)
        state.user_edited_slide_ids = sorted(existing)

    slide = await regeneration_service.regenerate_slide(state, slide_id=req.slide_id, force=req.force)
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

    slide_ids = list(req.slide_ids) if req.slide_ids else []
    if req.slide_id and req.slide_id not in slide_ids:
        slide_ids.append(req.slide_id)
    if not slide_ids:
        slide_ids = None

    notes = await regeneration_service.regenerate_notes(state, slide_ids=slide_ids)
    state.touch()
    await repo.upsert(state)
    return RegenerateNotesResponse(project_id=state.project_id, notes=notes)

