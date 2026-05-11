"""Text extraction + chunking for the Theme Q2 ingestion pipeline.

Pure functions — no DB, no S3. Celery task wires them together.
"""

from __future__ import annotations

import io
import re


# ---------- extraction --------------------------------------------------

def extract_text(content: bytes, mime_type: str) -> str:
    """Decode bytes to text based on MIME.

    Supports: text/*, application/json, text/markdown, text/csv,
    text/plain, application/pdf (via pypdf). Other types raise
    UnsupportedMimeTypeError.
    """
    mt = (mime_type or "").lower().split(";")[0].strip()

    if mt == "application/pdf":
        return _extract_pdf(content)

    if mt.startswith("text/") or mt in (
        "application/json", "application/xml", "application/yaml",
    ):
        # Naive utf-8 with replacement — defensive against non-text
        # bytes sneaking in.
        return content.decode("utf-8", errors="replace")

    raise UnsupportedMimeTypeError(
        f"Cannot extract text from mime type {mime_type!r}. "
        f"Supported: text/*, application/json, application/xml, "
        f"application/yaml, application/pdf."
    )


def _extract_pdf(content: bytes) -> str:
    """PDF text extraction via pypdf. Returns concatenated page text."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise UnsupportedMimeTypeError(
            "pypdf not installed; cannot extract PDF text. "
            "Add `pypdf>=4.0.0` to requirements.txt."
        ) from exc

    reader = PdfReader(io.BytesIO(content))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            pages.append(f"[page {i + 1}]\n{text}")
    return "\n\n".join(pages)


class UnsupportedMimeTypeError(Exception):
    pass


# ---------- chunking ----------------------------------------------------

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")


def chunk_text(text: str, *, max_chars: int = 2000, overlap_chars: int = 200) -> list[str]:
    """Split text into chunks of at most `max_chars` characters.

    Strategy:
    1. Split on paragraph boundaries (blank line).
    2. Greedily pack paragraphs into chunks under max_chars.
    3. If a single paragraph exceeds max_chars, hard-split with overlap.

    Q3 will replace this with a token-aware semantic chunker.
    """
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        if len(para) > max_chars:
            # Flush current first
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            # Hard-split with overlap
            start = 0
            while start < len(para):
                end = min(start + max_chars, len(para))
                chunks.append(para[start:end])
                if end == len(para):
                    break
                start = end - overlap_chars
            continue

        if current_len + len(para) + 2 > max_chars and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += len(para) + 2

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def estimate_tokens(text: str) -> int:
    """Cheap token count: 1 token ≈ 4 chars. Good enough for budgeting
    before we wire tiktoken in Q3.
    """
    return max(1, len(text) // 4)


__all__ = [
    "UnsupportedMimeTypeError",
    "extract_text",
    "chunk_text",
    "estimate_tokens",
]
