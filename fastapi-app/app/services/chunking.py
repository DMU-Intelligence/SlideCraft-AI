from __future__ import annotations

import re
from typing import List

from ..schemas.ingest import ParsedChunk


_HEADING_MD_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
_HEADING_NUM_RE = re.compile(r"^\s*((\d+[\.\)]\s*){1,5})(.+?)\s*$")
_HEADING_ALLCAPS_RE = re.compile(r"^[A-Z0-9][A-Z0-9\s\-\(\)]{4,}$")


def _detect_heading(paragraph: str) -> str | None:
    m = _HEADING_MD_RE.match(paragraph)
    if m:
        return m.group(1).strip()
    m = _HEADING_NUM_RE.match(paragraph)
    if m:
        return m.group(3).strip()
    if _HEADING_ALLCAPS_RE.match(paragraph) and len(paragraph) <= 120:
        return paragraph.strip()
    return None


class ChunkingService:
    async def chunk_text(
        self,
        text: str,
        max_chunk_chars: int = 1200,
        chunk_overlap: int = 150,
    ) -> List[ParsedChunk]:
        normalized = text.replace("\r\n", "\n").strip()
        if not normalized:
            return []

        paragraphs = [p.strip() for p in re.split(r"(?:\n){2,}", normalized) if p.strip()]
        # Track paragraph positions for deterministic start/end.
        cursor = 0
        para_positions: list[tuple[int, int]] = []
        for p in paragraphs:
            idx = normalized.find(p, cursor)
            if idx == -1:
                idx = cursor
            start = idx
            end = idx + len(p)
            para_positions.append((start, end))
            cursor = end

        chunks: list[ParsedChunk] = []
        current_paras: list[int] = []  # indices into paragraphs
        current_chars = 0
        active_heading: str | None = None

        def finalize_chunk() -> None:
            nonlocal current_paras, current_chars
            if not current_paras:
                return
            first_idx = current_paras[0]
            last_idx = current_paras[-1]
            start = para_positions[first_idx][0]
            end = para_positions[last_idx][1]
            chunk_text = "\n\n".join(paragraphs[i] for i in current_paras).strip()
            heading = active_heading_at(first_idx)
            chunk_id = f"chunk_{len(chunks) + 1:03d}"
            chunks.append(
                ParsedChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    heading=heading,
                    start_char=start,
                    end_char=end,
                )
            )
            current_paras = []
            current_chars = 0

        def active_heading_at(i: int) -> str | None:
            heading: str | None = None
            for j in range(0, i + 1):
                h = _detect_heading(paragraphs[j])
                if h:
                    heading = h
            return heading

        def tail_for_overlap() -> list[int]:
            if chunk_overlap <= 0 or not current_paras:
                return []
            overlap_paras: list[int] = []
            overlap_chars = 0
            # Take from the end backwards until we meet overlap_chars.
            for idx in reversed(current_paras):
                overlap_paras.insert(0, idx)
                overlap_chars += len(paragraphs[idx])
                if overlap_chars >= chunk_overlap:
                    break
            return overlap_paras

        for i, p in enumerate(paragraphs):
            h = _detect_heading(p)
            if h:
                active_heading = h

            p_len = len(p)
            # If adding would exceed target, finalize the current chunk first.
            if current_paras and current_chars + p_len > max_chunk_chars:
                tail = tail_for_overlap()
                finalize_chunk()
                current_paras = tail
                current_chars = sum(len(paragraphs[idx]) for idx in current_paras)

            current_paras.append(i)
            current_chars += p_len

            # Ensure we don't create extremely large chunks.
            if current_chars >= max_chunk_chars * 1.25:
                finalize_chunk()

        finalize_chunk()
        return chunks

