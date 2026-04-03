from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import load_settings
from .core.logging import configure_logging
from .repositories.project_repository import FileProjectRepository, InMemoryProjectRepository
from .routers.health import router as health_router
from .routers.ingest import router as ingest_router
from .routers.generate import router as generate_router
from .routers.regenerate import router as regenerate_router
from .routers.export import router as export_router
from .services.chunking import ChunkingService
from .services.document_parser import DocumentParser
from .services.llm_client import create_llm_client
from .services.notes_generator import NotesGenerator
from .services.outline_generator import OutlineGenerator
from .services.regeneration_service import RegenerationService
from .services.slide_generator import SlideGenerator
from .services.summarizer import Summarizer


configure_logging()
settings = load_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "SlideCraft AI FastAPI service is running."}


@app.on_event("startup")
async def startup() -> None:
    os.makedirs(settings.upload_dir, exist_ok=True)

    if settings.project_repo_mode == "file":
        app.state.project_repository = FileProjectRepository(settings.project_repo_path)
    else:
        app.state.project_repository = InMemoryProjectRepository()

    app.state.settings = settings
    app.state.document_parser = DocumentParser()
    app.state.chunking_service = ChunkingService()
    app.state.summarizer = Summarizer()

    llm_client = create_llm_client(settings)
    app.state.llm_client = llm_client
    app.state.outline_generator = OutlineGenerator(llm_client)
    app.state.slide_generator = SlideGenerator(llm_client)
    app.state.notes_generator = NotesGenerator(llm_client)
    app.state.regeneration_service = RegenerationService(llm_client)


app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(generate_router)
app.include_router(regenerate_router)
app.include_router(export_router)

