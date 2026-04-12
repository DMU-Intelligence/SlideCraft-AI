from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from ..schemas.generate import (
    GenerateAllRequest,
    GenerateAllResponse,
    GenerateNotesRequest,
    GenerateNotesResponse,
    GenerateOutlineRequest,
    GenerateOutlineResponse,
    GenerateSlidesRequest,
    GenerateSlidesResponse,
)
from ..models.project_state import ProjectState

router = APIRouter(tags=["generate"])


@router.post("/generate/outline", response_model=GenerateOutlineResponse)
async def generate_outline(req: GenerateOutlineRequest, request: Request) -> GenerateOutlineResponse:
    repo = request.app.state.project_repository
    outline_generator = request.app.state.outline_generator

    state: ProjectState | None = await repo.get(req.project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")
    outline_result = await outline_generator.generate_outline(state)
    state.title = outline_result.title
    state.outline = outline_result.outline
    state.metadata["presentation_goal"] = f"문서 '{state.title}'의 핵심 내용을 청중이 이해하기 쉽게 발표 자료로 구성한다."
    state.touch()
    await repo.upsert(state)
    return GenerateOutlineResponse(
        project_id=state.project_id,
        title=state.title,
        outline=state.outline,
    )


@router.post("/generate/slides", response_model=GenerateSlidesResponse)
async def generate_slides(req: GenerateSlidesRequest, request: Request) -> GenerateSlidesResponse:
    repo = request.app.state.project_repository
    slide_generator = request.app.state.slide_generator

    state: ProjectState | None = await repo.get(req.project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        slides = await slide_generator.generate_slides(state)
        slides = await slide_generator.add_just_template(state, slides, req.template_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"템플릿 '{req.template_name}'을 찾을 수 없습니다.")
    except ValueError as exc:
        state.touch()
        await repo.upsert(state)
        raise HTTPException(status_code=400, detail=str(exc))
    state.slides = slides
    # Regenerate notes are independent; keep existing notes as-is.
    state.touch()
    await repo.upsert(state)
    return GenerateSlidesResponse(project_id=state.project_id, slides=slides)


@router.post("/generate/notes", response_model=GenerateNotesResponse)
async def generate_notes(req: GenerateNotesRequest, request: Request) -> GenerateNotesResponse:
    repo = request.app.state.project_repository
    notes_generator = request.app.state.notes_generator

    state: ProjectState | None = await repo.get(req.project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")
    notes = await notes_generator.generate_notes(state)
    state.notes = notes
    state.touch()
    await repo.upsert(state)
    return GenerateNotesResponse(project_id=state.project_id, notes=notes)


@router.get("/notes/{project_id}")
async def get_notes(project_id: int, request: Request) -> PlainTextResponse:
    repo = request.app.state.project_repository
    state: ProjectState | None = await repo.get(project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")
    if not state.notes:
        raise HTTPException(status_code=404, detail="notes not found")
    return PlainTextResponse(content=state.notes)


@router.post("/generate/all", response_model=GenerateAllResponse)
async def generate_all(req: GenerateAllRequest, request: Request) -> GenerateAllResponse:
    repo = request.app.state.project_repository
    outline_generator = request.app.state.outline_generator
    slide_generator = request.app.state.slide_generator
    notes_generator = request.app.state.notes_generator

    state: ProjectState | None = await repo.get(req.project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")

    outline_result = await outline_generator.generate_outline(state)
    state.title = outline_result.title
    state.outline = outline_result.outline
    state.metadata["presentation_goal"] = f"문서 '{state.title}'의 핵심 내용을 청중이 이해하기 쉽게 발표 자료로 구성한다."

    try:
        slides = await slide_generator.generate_slides(state)
        slides = await slide_generator.add_just_template(state, slides, req.template_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"템플릿 '{req.template_name}'을 찾을 수 없습니다.")
    except ValueError as exc:
        state.touch()
        await repo.upsert(state)
        raise HTTPException(status_code=400, detail=str(exc))
    state.slides = slides

    notes = await notes_generator.generate_notes(state)
    state.notes = notes

    state.touch()
    await repo.upsert(state)
    return GenerateAllResponse(
        project_id=state.project_id,
        title=state.title,
        outline=state.outline,
        slides=slides,
        notes=notes,
        stats={},
    )
