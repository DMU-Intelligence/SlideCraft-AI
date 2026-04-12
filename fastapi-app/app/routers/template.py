from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..services.template_extractor import TemplateExtractor
from ..services.template_store import (
    get_template_dir,
    get_template_path,
    list_templates as load_template_list,
    load_template,
    sanitize_template_name,
    save_template,
)
from ..utils.file_loader import save_upload_file

router = APIRouter(tags=["template"])
_extractor = TemplateExtractor()


@router.post("/template/upload")
async def upload_template(
    file: UploadFile = File(...),
    title: str = Form(...),
) -> dict[str, object]:
    try:
        safe_title = sanitize_template_name(title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    template_dir = get_template_dir()
    template_dir.mkdir(parents=True, exist_ok=True)

    temp_path = template_dir / f"_temp_upload_{uuid.uuid4().hex}.pptx"

    try:
        await save_upload_file(file, str(temp_path))
        template_data = _extractor.extract(str(temp_path))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PPTX 파싱 실패: {exc}") from exc
    finally:
        if temp_path.exists():
            temp_path.unlink()
        await file.close()

    if not template_data:
        raise HTTPException(status_code=400, detail="추출된 콘텐츠 슬라이드가 없습니다.")

    template_path = save_template(safe_title, template_data)
    return {
        "template_name": safe_title,
        "template_path": str(template_path),
        "template": template_data,
        "slide_count": len(template_data),
    }


@router.get("/template")
async def list_templates() -> dict[str, object]:
    return {"templates": load_template_list()}


@router.get("/template/{template_name}")
async def get_template(template_name: str) -> dict[str, object]:
    try:
        safe_name = sanitize_template_name(template_name)
        template = load_template(safe_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "template_name": safe_name,
        "template_path": str(get_template_path(safe_name)),
        "template": template,
        "slide_count": len(template),
    }
