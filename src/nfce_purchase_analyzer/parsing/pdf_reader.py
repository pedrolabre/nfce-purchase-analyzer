"""Isolated PDF text extraction adapter using pdfplumber.

This module is the **only** place in the project that imports
``pdfplumber``.  The domain layer and the parsing contracts must
never depend on ``pdfplumber`` directly.

Public API
----------
- :class:`PdfReadError` — raised for any PDF reading failure.
- :func:`extract_text_from_pdf` — returns extracted text per page.
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber
from pdfplumber.pdf import PDF


class PdfReadError(Exception):
    """Raised when a PDF file cannot be read or yields no text.

    Attributes:
        path: The file path that caused the error.
        reason: A machine-readable reason code.
    """

    def __init__(self, path: str, reason: str, message: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(message)


def extract_text_from_pdf(path: str | Path) -> list[str]:
    """Extract text from each page of a PDF file.

    Args:
        path: Filesystem path to the PDF file.

    Returns:
        A list of strings, one per page, containing the extracted
        text.  Pages that yield no text are represented as empty
        strings.

    Raises:
        PdfReadError: If *path* does not exist, is not a valid PDF,
            is password-protected, or contains no extractable text
            on any page.
    """
    resolved = Path(path)

    if not resolved.exists():
        raise PdfReadError(
            path=str(resolved),
            reason="file_not_found",
            message=f"File not found: {resolved}",
        )

    if not resolved.is_file():
        raise PdfReadError(
            path=str(resolved),
            reason="not_a_file",
            message=f"Path is not a file: {resolved}",
        )

    try:
        pdf: PDF = pdfplumber.open(resolved)
    except Exception as exc:
        raise PdfReadError(
            path=str(resolved),
            reason="invalid_pdf",
            message=f"Cannot open PDF: {resolved} ({exc})",
        ) from exc

    try:
        if not pdf.pages:
            raise PdfReadError(
                path=str(resolved),
                reason="no_pages",
                message=f"PDF has no pages: {resolved}",
            )

        pages: list[str] = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)

        if all(p == "" for p in pages):
            raise PdfReadError(
                path=str(resolved),
                reason="no_text",
                message=f"PDF contains no extractable text: {resolved}",
            )

        return pages
    finally:
        pdf.close()


__all__ = ["PdfReadError", "extract_text_from_pdf"]
