"""Synthetic PDF builder for integration tests.

Generates minimal valid PDF files in memory from plain text lines.
The resulting PDFs are readable by ``pdfplumber`` and do **not**
depend on network access or external resources.
"""

from __future__ import annotations


def build_text_pdf(lines: list[str]) -> bytes:
    """Build a minimal single-page PDF containing the given text lines.

    Each line is rendered as a separate ``Tj`` text operation using
    the built-in Helvetica font.  The text is laid out top-to-bottom
    starting near the top of a standard US Letter page.

    Args:
        lines: Text lines to embed in the PDF.  Empty strings produce
            blank lines in the layout.

    Returns:
        Raw PDF bytes that ``pdfplumber`` can open and extract text from.
    """
    # Build the content stream with one Tj per line.
    font_size = 10
    leading = 14  # vertical spacing between lines
    x_start = 50
    y_start = 750

    stream_parts: list[bytes] = []
    stream_parts.append(f"BT\n/F1 {font_size} Tf\n".encode())

    for idx, line in enumerate(lines):
        y = y_start - idx * leading
        if y < 50:
            break  # stop if we run out of page space
        escaped = _escape_pdf_string(line)
        stream_parts.append(
            f"{x_start} {y} Td\n({escaped}) Tj\n0 0 Td\n".encode()
        )

    stream_parts.append(b"ET\n")
    stream_content = b"".join(stream_parts)
    stream_length = len(stream_content)

    parts: list[bytes] = []
    offsets: list[int] = []

    def _current_offset() -> int:
        return sum(len(p) for p in parts)

    # Header
    parts.append(b"%PDF-1.4\n")

    # 1: Catalog
    offsets.append(_current_offset())
    parts.append(b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n")

    # 2: Pages
    offsets.append(_current_offset())
    parts.append(
        b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
    )

    # 3: Page
    offsets.append(_current_offset())
    parts.append(
        b"3 0 obj\n"
        b"<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>>\n"
        b"endobj\n"
    )

    # 4: Content stream
    offsets.append(_current_offset())
    parts.append(
        b"4 0 obj\n<</Length "
        + str(stream_length).encode()
        + b">>\nstream\n"
        + stream_content
        + b"\nendstream\nendobj\n"
    )

    # 5: Font
    offsets.append(_current_offset())
    parts.append(
        b"5 0 obj\n"
        b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>\n"
        b"endobj\n"
    )

    # xref table
    xref_offset = _current_offset()
    xref = b"xref\n0 6\n"
    xref += b"0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()
    xref += b"trailer\n<</Size 6 /Root 1 0 R>>\n"
    xref += b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF\n"
    parts.append(xref)

    return b"".join(parts)


def _escape_pdf_string(text: str) -> str:
    """Escape special characters for a PDF literal string.

    PDF literal strings use parentheses as delimiters and require
    backslash escaping for ``(``, ``)``, and ``\\``.
    """
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


__all__ = ["build_text_pdf"]
