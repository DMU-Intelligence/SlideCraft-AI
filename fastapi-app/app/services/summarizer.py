from __future__ import annotations

import re
from typing import Any

from ..schemas.ingest import ParsedChunk
from ..utils.token_utils import split_sentences


class Summarizer:
    async def summarize(
        self,
        chunks: list[ParsedChunk],
        max_chunk_summaries: int = 6,
        max_summary_chars: int = 700,
    ) -> dict[str, Any]:
        if not chunks:
            return {"summary": "", "chunk_summaries": []}

        chunk_summaries: list[str] = []
        for c in chunks[:max_chunk_summaries]:
            sentences = split_sentences(c.text)
            if not sentences:
                chunk_summaries.append(c.text[:180].strip())
                continue
            selected = sentences[: min(2, len(sentences))]
            chunk_summaries.append(" ".join(selected).strip())

        merged = " ".join(chunk_summaries).strip()
        merged = re.sub(r"\s+", " ", merged)
        if len(merged) > max_summary_chars:
            merged = merged[:max_summary_chars].rsplit(" ", 1)[0].strip() + "..."
        return {"summary": merged, "chunk_summaries": chunk_summaries}

