from __future__ import annotations

import re
from collections import Counter
from typing import Iterable


_WORD_RE = re.compile(r"[A-Za-z0-9_']+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "at",
    "by",
    "from",
    "into",
    "over",
    "under",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "it",
    "its",
    "as",
    "that",
    "this",
    "these",
    "those",
    "you",
    "your",
    "we",
    "our",
    "they",
    "their",
    "i",
    "me",
    "my",
    "not",
    "no",
    "yes",
    "can",
    "will",
    "would",
    "should",
    "could",
    "may",
    "might",
    "do",
    "does",
    "did",
    "done",
    "have",
    "has",
    "had",
    "having",
    "so",
    "such",
    "than",
    "too",
    "very",
    "also",
}


def tokenize_words(text: str) -> list[str]:
    words = _WORD_RE.findall(text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


def count_word_freq(text: str) -> Counter[str]:
    return Counter(tokenize_words(text))


def extract_top_keywords(text: str, top_n: int = 8) -> list[str]:
    freq = count_word_freq(text)
    # Deterministic tie-break: by keyword alphabetical.
    items = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in items[:top_n]]


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    # Prefer punctuation-based splitting; fall back to line-based chunks.
    parts = _SENTENCE_RE.split(text)
    cleaned = [p.strip() for p in parts if p.strip()]
    if cleaned:
        return cleaned
    return [line.strip() for line in text.splitlines() if line.strip()]


def iter_paragraphs(text: str) -> Iterable[str]:
    # Keep things simple and deterministic.
    for p in re.split(r"(?:\r?\n){2,}", text):
        p = p.strip()
        if p:
            yield p

