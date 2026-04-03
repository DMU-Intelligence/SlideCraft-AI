from __future__ import annotations

import os
from pathlib import Path

from fastapi import UploadFile


def sanitize_filename(filename: str) -> str:
    # Keep only the base name to avoid path traversal via client-provided names.
    return os.path.basename(filename).replace("\x00", "")


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


async def save_upload_file(upload: UploadFile, dest_path: str, chunk_size: int = 1024 * 1024) -> None:
    ensure_dir(os.path.dirname(dest_path) or ".")
    with open(dest_path, "wb") as f:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)

