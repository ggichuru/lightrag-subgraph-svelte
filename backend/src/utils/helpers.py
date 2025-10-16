from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Iterable, Iterator

from docx import Document  # type: ignore
from pypdf import PdfReader  # type: ignore
from pypdf.errors import FileNotDecryptedError  # type: ignore

LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx", ".json"}


def slugify(value: str) -> str:
    """Return a filesystem-friendly slug for the provided value."""

    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "document"


def iter_corpus_files(base_path: Path) -> Iterator[Path]:
    """Yield supported document files within the corpus directory."""

    if not base_path.exists():
        LOGGER.warning("Corpus directory %s does not exist", base_path)
        return

    for path in sorted(base_path.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_json_file(path: Path) -> str:
    content = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    return json.dumps(content, indent=2, ensure_ascii=False)


def read_pdf_file(path: Path) -> str:
    reader = PdfReader(str(path))
    if getattr(reader, 'is_encrypted', False):
        try:
            if reader.decrypt("") == 0:
                raise ValueError(f"PDF '{path.name}' is encrypted and requires a password")
        except (FileNotDecryptedError, NotImplementedError) as exc:
            raise ValueError(f"PDF '{path.name}' is encrypted and cannot be processed") from exc
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages).strip()


def read_docx_file(path: Path) -> str:
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs]
    return "\n".join(paragraphs).strip()


READERS = {
    ".txt": read_text_file,
    ".md": read_text_file,
    ".markdown": read_text_file,
    ".json": read_json_file,
    ".pdf": read_pdf_file,
    ".docx": read_docx_file,
}


def load_document_text(path: Path) -> str:
    """Load document text based on file extension."""

    reader = READERS.get(path.suffix.lower())
    if not reader:
        raise ValueError(f"Unsupported file extension: {path.suffix}")

    try:
        text = reader(path)
    except Exception as exc:  # pragma: no cover - log for visibility
        LOGGER.exception("Failed to read %s: %s", path, exc)
        raise

    if not text.strip():
        LOGGER.warning("Document %s produced empty text", path)
    return text


def chunked(iterable: Iterable[str], size: int) -> Iterator[list[str]]:
    """Yield chunks of a given size from an iterable."""

    batch: list[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch

