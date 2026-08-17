"""Tests for the PDF text extraction adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from nfce_purchase_analyzer.parsing.pdf_reader import PdfReadError, extract_text_from_pdf


# ---------------------------------------------------------------------------
# Fixtures — tiny synthetic files for each error scenario
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_text_file(tmp_path: Path) -> Path:
    """Create a plain text file that is not a valid PDF."""
    p = tmp_path / "not_a_pdf.txt"
    p.write_text("This is not a PDF file.", encoding="utf-8")
    return p


@pytest.fixture()
def tmp_empty_pdf(tmp_path: Path) -> Path:
    """Create a minimal valid PDF with a single page containing no text.

    This is the smallest possible PDF that pdfplumber can open —
    a single empty page with no content stream.
    """
    # Minimal hand-crafted PDF with one empty page.
    content = (
        b"%PDF-1.0\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n190\n%%EOF"
    )
    p = tmp_path / "empty.pdf"
    p.write_bytes(content)
    return p


@pytest.fixture()
def tmp_corrupted_pdf(tmp_path: Path) -> Path:
    """Create a file that starts with PDF header but is corrupted."""
    p = tmp_path / "corrupted.pdf"
    p.write_bytes(b"%PDF-1.0\nGARBAGE CONTENT")
    return p


@pytest.fixture()
def tmp_text_pdf(tmp_path: Path) -> Path:
    """Create a minimal valid PDF containing extractable text.

    Uses a proper PDF with a text content stream so pdfplumber
    can extract meaningful text.
    """
    # Hand-crafted PDF with a text stream on page 1.
    stream_content = b"BT /F1 12 Tf 100 700 Td (Hello NFC-e) Tj ET"
    stream_length = len(stream_content)

    parts: list[bytes] = []
    offsets: list[int] = []

    def _add(obj: bytes) -> None:
        offsets.append(len(b"".join(parts)))
        parts.append(obj)

    # Header
    parts.append(b"%PDF-1.4\n")

    # 1: Catalog
    _add(
        b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n"
    )
    # 2: Pages
    _add(
        b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
    )
    # 3: Page
    _add(
        b"3 0 obj\n"
        b"<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>>\n"
        b"endobj\n"
    )
    # 4: Content stream
    _add(
        b"4 0 obj\n<</Length " + str(stream_length).encode() + b">>\n"
        b"stream\n" + stream_content + b"\nendstream\nendobj\n"
    )
    # 5: Font
    _add(
        b"5 0 obj\n<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>\nendobj\n"
    )

    # xref
    xref_offset = len(b"".join(parts))
    xref = b"xref\n0 6\n"
    xref += b"0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()
    xref += b"trailer\n<</Size 6 /Root 1 0 R>>\n"
    xref += b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF\n"
    parts.append(xref)

    p = tmp_path / "with_text.pdf"
    p.write_bytes(b"".join(parts))
    return p


@pytest.fixture()
def tmp_directory(tmp_path: Path) -> Path:
    """Return a path to a directory (not a file)."""
    d = tmp_path / "subdir"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# PdfReadError
# ---------------------------------------------------------------------------


class TestPdfReadError:
    def test_attributes(self) -> None:
        err = PdfReadError(path="/x.pdf", reason="file_not_found", message="gone")
        assert err.path == "/x.pdf"
        assert err.reason == "file_not_found"
        assert str(err) == "gone"

    def test_is_exception(self) -> None:
        assert issubclass(PdfReadError, Exception)


# ---------------------------------------------------------------------------
# extract_text_from_pdf — error cases
# ---------------------------------------------------------------------------


class TestExtractTextErrors:
    def test_file_not_found(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.pdf"
        with pytest.raises(PdfReadError, match="not found") as exc_info:
            extract_text_from_pdf(missing)
        assert exc_info.value.reason == "file_not_found"

    def test_path_is_directory(self, tmp_directory: Path) -> None:
        with pytest.raises(PdfReadError, match="not a file") as exc_info:
            extract_text_from_pdf(tmp_directory)
        assert exc_info.value.reason == "not_a_file"

    def test_not_a_pdf(self, tmp_text_file: Path) -> None:
        with pytest.raises(PdfReadError, match="Cannot open PDF") as exc_info:
            extract_text_from_pdf(tmp_text_file)
        assert exc_info.value.reason == "invalid_pdf"

    def test_corrupted_pdf(self, tmp_corrupted_pdf: Path) -> None:
        with pytest.raises(PdfReadError) as exc_info:
            extract_text_from_pdf(tmp_corrupted_pdf)
        assert exc_info.value.reason in ("invalid_pdf", "no_pages", "no_text")

    def test_pdf_without_text(self, tmp_empty_pdf: Path) -> None:
        with pytest.raises(PdfReadError) as exc_info:
            extract_text_from_pdf(tmp_empty_pdf)
        assert exc_info.value.reason in ("no_text", "no_pages")

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        missing = str(tmp_path / "missing.pdf")
        with pytest.raises(PdfReadError) as exc_info:
            extract_text_from_pdf(missing)
        assert exc_info.value.reason == "file_not_found"


# ---------------------------------------------------------------------------
# extract_text_from_pdf — success case
# ---------------------------------------------------------------------------


class TestExtractTextSuccess:
    def test_extracts_text_from_valid_pdf(self, tmp_text_pdf: Path) -> None:
        pages = extract_text_from_pdf(tmp_text_pdf)
        assert isinstance(pages, list)
        assert len(pages) == 1
        assert "Hello" in pages[0] or "NFC-e" in pages[0]

    def test_accepts_pathlib_path(self, tmp_text_pdf: Path) -> None:
        pages = extract_text_from_pdf(tmp_text_pdf)
        assert len(pages) >= 1

    def test_accepts_string_path(self, tmp_text_pdf: Path) -> None:
        pages = extract_text_from_pdf(str(tmp_text_pdf))
        assert len(pages) >= 1
