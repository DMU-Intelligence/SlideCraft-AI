from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "template"


def get_template_dir() -> Path:
    return _TEMPLATE_DIR


def sanitize_template_name(template_name: str) -> str:
    safe_name = template_name.strip().replace("/", "_").replace("\\", "_")
    if not safe_name:
        raise ValueError("템플릿 이름이 비어 있습니다.")
    return safe_name


def get_template_path(template_name: str) -> Path:
    safe_name = sanitize_template_name(template_name)
    return _TEMPLATE_DIR / f"{safe_name}.json"


def load_template(template_name: str) -> list[dict[str, Any]]:
    template_path = get_template_path(template_name)
    if not template_path.exists():
        raise FileNotFoundError(f"템플릿 '{template_name}'을 찾을 수 없습니다.")

    data = json.loads(template_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("템플릿 파일 형식이 올바르지 않습니다.")
    return data


def save_template(template_name: str, template_pages: list[dict[str, Any]]) -> Path:
    template_path = get_template_path(template_name)
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(
        json.dumps(template_pages, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return template_path


def list_templates() -> list[dict[str, Any]]:
    if not _TEMPLATE_DIR.exists():
        return []

    templates: list[dict[str, Any]] = []
    for path in sorted(_TEMPLATE_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        slide_count = len(data) if isinstance(data, list) else 0
        templates.append(
            {
                "template_name": path.stem,
                "slide_count": slide_count,
            }
        )
    return templates
