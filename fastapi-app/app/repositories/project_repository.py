from __future__ import annotations

import json
import os
import tempfile
from abc import ABC, abstractmethod
from typing import Dict

from ..models.project_state import ProjectState


class ProjectRepository(ABC):
    @abstractmethod
    async def get(self, project_id: str) -> ProjectState | None:
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, state: ProjectState) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, project_id: str) -> bool:
        raise NotImplementedError


class InMemoryProjectRepository(ProjectRepository):
    def __init__(self) -> None:
        self._store: Dict[str, ProjectState] = {}

    async def get(self, project_id: str) -> ProjectState | None:
        state = self._store.get(project_id)
        if state is None:
            return None
        return ProjectState.model_validate(state.model_dump())

    async def upsert(self, state: ProjectState) -> None:
        # Store a copy to avoid accidental cross-request mutation.
        self._store[state.project_id] = ProjectState.model_validate(state.model_dump())

    async def exists(self, project_id: str) -> bool:
        return project_id in self._store


class FileProjectRepository(ProjectRepository):
    def __init__(self, path: str) -> None:
        self._path = path

    def _load_all(self) -> Dict[str, ProjectState]:
        if not os.path.exists(self._path):
            return {}
        with open(self._path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {pid: ProjectState.model_validate(data) for pid, data in raw.items()}

    def _write_all(self, states: Dict[str, ProjectState]) -> None:
        dir_path = os.path.dirname(self._path) or "."
        os.makedirs(dir_path, exist_ok=True)
        payload = {pid: state.model_dump() for pid, state in states.items()}

        fd, tmp_path = tempfile.mkstemp(prefix="projects_", suffix=".json", dir=dir_path)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass

    async def get(self, project_id: str) -> ProjectState | None:
        states = self._load_all()
        state = states.get(project_id)
        if state is None:
            return None
        return ProjectState.model_validate(state.model_dump())

    async def upsert(self, state: ProjectState) -> None:
        states = self._load_all()
        states[state.project_id] = ProjectState.model_validate(state.model_dump())
        self._write_all(states)

    async def exists(self, project_id: str) -> bool:
        states = self._load_all()
        return project_id in states

