"""Parser for the Bem Maior supermarket NFC-e layout."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from nfce_purchase_analyzer.deterministic import (
    deterministic_uuid,
    quantize_money,
    quantize_quantity,
    uuid_from,
)
from nfce_purchase_analyzer.domain import PendingPurchaseImport, PendingPurchaseItem
from nfce_purchase_analyzer.parsing.contracts import (
    DiagnosticLevel,
    ParseDiagnostic,
    ParseResult,
    ParserLayout,
)

# ---------------------------------------------------------------------------
# Store identity
# ---------------------------------------------------------------------------

#: Namespace UUID for deterministic store ID generation.
_BEM_MAIOR_NAMESPACE = uuid_from("00000000-0000-0000-0000-000000000001")

#: Deterministic store UUID for "Bem Maior".
BEM_MAIOR_STORE_ID = deterministic_uuid(_BEM_MAIOR_NAMESPACE, "bem_maior")

# ---------------------------------------------------------------------------
# Regex patterns for line parsing
# ---------------------------------------------------------------------------

# Matches an item line in the format:
#   <code> <description> <quantity> <unit> <unit_price> <total_price>
# Example: "000042 CAFE TORRADO 500G 1 UN X 15,90 (15,90)"
# Or with weighted items: "000099 BANANA PRATA 0,542 KG X 5,99 (3,25)"
#
# The NFC-e item lines typically look like:
#   CODE DESCRIPTION
#   QTY UNIT X UNIT_PRICE TOTAL_PRICE
#
# In Bem Maior layout, items can span two lines:
#   Line 1: CODE DESCRIPTION
#   Line 2: QTD UNIT X UNIT_PRICE TOTAL
#
# Or be on a single line:
#   CODE DESCRIPTION QTD UNIT X UNIT_PRICE TOTAL

# Pattern for the item header line: code followed by description
_ITEM_CODE_RE = re.compile(
    r"^\s*(\d{1,20})\s+(.+?)\s*$",
)

# Pattern for the quantity/price line:
#   quantity unit X unit_price total_price
# Supports both comma and dot as decimal separator.
_QTY_PRICE_RE = re.compile(
    r"^\s*"
    r"(\d+(?:[.,]\d+)?)"       # quantity
    r"\s+"
    r"(UN|KG|PCT|CX|LT|ML|GR|MT|M2|M3|DZ|PR|FD|GL|SC|TB|PT|BD|RL|CT|CJ|VD|L|G)"  # unit
    r"\s+[Xx]\s+"
    r"(\d+(?:[.,]\d+)?)"       # unit price
    r"\s+"
    r"\(?\s*(\d+(?:[.,]\d+)?)\s*\)?"  # total price (optionally in parentheses)
    r"\s*$",
    re.IGNORECASE,
)

# Pattern for total line: "TOTAL" or "TOTAL R$" followed by value
_TOTAL_RE = re.compile(
    r"^\s*(?:VALOR\s+)?TOTAL(?:\s+R\$)?\s+(\d+(?:[.,]\d+)?)\s*$",
    re.IGNORECASE,
)

# Pattern for date/time of emission:
#   DD/MM/YYYY HH:MM:SS or DD/MM/YYYY HH:MM
_DATETIME_RE = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}(?::\d{2})?)",
)

# Date-only pattern as fallback
_DATE_ONLY_RE = re.compile(
    r"(\d{2}/\d{2}/\d{4})",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_brazilian_decimal(text: str) -> Decimal:
    """Parse a Brazilian-formatted decimal string.

    Converts comma decimal separator to dot and returns a Decimal.

    Raises:
        InvalidOperation: If the text is not a valid decimal.
    """
    normalized = text.strip().replace(",", ".")
    return Decimal(normalized)


def _parse_emission_datetime(text: str) -> datetime | None:
    """Try to parse a datetime from a line of text.

    Returns ``None`` if no date/time pattern is found.
    """
    match = _DATETIME_RE.search(text)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        fmt = "%d/%m/%Y %H:%M:%S" if len(time_str) > 5 else "%d/%m/%Y %H:%M"
        try:
            return datetime.strptime(f"{date_str} {time_str}", fmt)
        except ValueError:
            return None
    return None


def _find_emission_date(lines: list[str]) -> datetime | None:
    """Scan lines for the emission date/time.

    Looks for keywords that typically precede the emission date
    in the Bem Maior layout, then falls back to the first
    date/time found in the document.
    """
    # First pass: look for lines with emission-related keywords
    emission_keywords = ("emissao", "emissão", "data de emissao", "data de emissão")
    for line in lines:
        lower = line.lower()
        if any(kw in lower for kw in emission_keywords):
            result = _parse_emission_datetime(line)
            if result is not None:
                return result

    # Second pass: look for any date/time in the document
    for line in lines:
        result = _parse_emission_datetime(line)
        if result is not None:
            return result

    # Third pass: look for date-only as last resort
    for line in lines:
        match = _DATE_ONLY_RE.search(line)
        if match:
            try:
                return datetime.strptime(match.group(1), "%d/%m/%Y")
            except ValueError:
                continue

    return None


def _find_total(lines: list[str]) -> Decimal | None:
    """Scan lines for the total value of the NFC-e.

    Returns the last match found, since the general total
    typically appears after item-level totals.
    """
    last_total: Decimal | None = None
    for line in lines:
        match = _TOTAL_RE.match(line)
        if match:
            try:
                last_total = _parse_brazilian_decimal(match.group(1))
            except InvalidOperation:
                continue
    return last_total


# ---------------------------------------------------------------------------
# Item extraction
# ---------------------------------------------------------------------------


def _extract_items(
    lines: list[str],
    store_id_hex: str,
) -> tuple[list[PendingPurchaseItem], list[ParseDiagnostic]]:
    """Extract purchase items from text lines.

    Returns a tuple of (items, diagnostics).
    """
    items: list[PendingPurchaseItem] = []
    diagnostics: list[ParseDiagnostic] = []
    seen_codes: set[str] = set()

    store_id = uuid_from(store_id_hex)

    i = 0
    while i < len(lines):
        line = lines[i]

        # Try to match an item code + description line
        code_match = _ITEM_CODE_RE.match(line)
        if code_match is None:
            i += 1
            continue

        code = code_match.group(1)
        description = code_match.group(2).strip()

        # Check if quantity/price is on the same line (embedded in description)
        # or on the next line
        qty_match = _QTY_PRICE_RE.search(description)
        if qty_match is not None:
            # Quantity info is embedded in the description line
            # Extract the description part before the quantity
            desc_end = qty_match.start()
            description = description[:desc_end].strip()
        else:
            # Look for quantity/price on the next line
            if i + 1 < len(lines):
                qty_match = _QTY_PRICE_RE.match(lines[i + 1])
                if qty_match is not None:
                    i += 1  # consume the next line

        if qty_match is None:
            # No quantity/price found — skip this line
            i += 1
            continue

        try:
            quantity = quantize_quantity(_parse_brazilian_decimal(qty_match.group(1)))
            unit_price = quantize_money(_parse_brazilian_decimal(qty_match.group(3)))
            total_price = quantize_money(_parse_brazilian_decimal(qty_match.group(4)))
        except (InvalidOperation, ValueError, TypeError) as exc:
            diagnostics.append(
                ParseDiagnostic(
                    level=DiagnosticLevel.WARNING,
                    code="invalid_item_value",
                    message=(
                        f"Valores invalidos no item {code!r}: {exc}"
                    ),
                )
            )
            i += 1
            continue

        if not description:
            diagnostics.append(
                ParseDiagnostic(
                    level=DiagnosticLevel.WARNING,
                    code="empty_description",
                    message=f"Descricao vazia para item {code!r}",
                )
            )
            i += 1
            continue

        # Check for duplicate codes within the same receipt
        item_key = f"{code}:{description}"
        if item_key in seen_codes:
            diagnostics.append(
                ParseDiagnostic(
                    level=DiagnosticLevel.WARNING,
                    code="duplicate_item",
                    message=(
                        f"Item duplicado ignorado: codigo {code!r}, "
                        f"descricao {description!r}"
                    ),
                )
            )
            i += 1
            continue
        seen_codes.add(item_key)

        items.append(
            PendingPurchaseItem(
                store_id=store_id,
                internal_code=code,
                raw_name=description,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
            )
        )
        i += 1

    return items, diagnostics


# ---------------------------------------------------------------------------
# BemMaiorParser
# ---------------------------------------------------------------------------


class BemMaiorParser:
    """Parser for the Bem Maior supermarket NFC-e PDF layout.

    This parser operates on plain text lines extracted from a PDF.
    It does **not** perform file I/O, write to disk, or confirm
    any import.

    The parser extracts:
    - Purchase items with code, description, quantity, unit price, total.
    - Emission date/time.
    - Total value of the receipt.

    Usage::

        parser = BemMaiorParser()
        result = parser.parse(text_lines, source_pdf="receipt.pdf")
    """

    @property
    def layout(self) -> ParserLayout:
        """The layout this parser handles."""
        return ParserLayout.BEM_MAIOR

    def parse(
        self,
        text_lines: list[str],
        *,
        source_pdf: str,
    ) -> ParseResult:
        """Parse NFC-e text lines from a Bem Maior receipt.

        Args:
            text_lines: Ordered lines of text extracted from the PDF.
            source_pdf: Path or identifier of the source PDF file.

        Returns:
            A ``ParseResult`` with extracted data or error diagnostics.
        """
        diagnostics: list[ParseDiagnostic] = []

        if not text_lines:
            return ParseResult(
                pending_import=None,
                diagnostics=(
                    ParseDiagnostic(
                        level=DiagnosticLevel.ERROR,
                        code="empty_input",
                        message="Nenhuma linha de texto fornecida para parsing",
                    ),
                ),
                layout=self.layout,
            )

        # Extract emission date
        emission_date = _find_emission_date(text_lines)
        if emission_date is None:
            diagnostics.append(
                ParseDiagnostic(
                    level=DiagnosticLevel.ERROR,
                    code="missing_date",
                    message="Data de emissao nao encontrada no documento",
                )
            )

        # Extract total value
        total_value = _find_total(text_lines)
        if total_value is None:
            diagnostics.append(
                ParseDiagnostic(
                    level=DiagnosticLevel.ERROR,
                    code="missing_total",
                    message="Valor total da nota nao encontrado no documento",
                )
            )

        # Extract items
        store_id_hex = str(BEM_MAIOR_STORE_ID)
        items, item_diagnostics = _extract_items(text_lines, store_id_hex)
        diagnostics.extend(item_diagnostics)

        if not items:
            diagnostics.append(
                ParseDiagnostic(
                    level=DiagnosticLevel.ERROR,
                    code="no_items",
                    message="Nenhum item de compra encontrado no documento",
                )
            )

        # If any error-level diagnostic was emitted, return failure
        has_errors = any(
            d.level == DiagnosticLevel.ERROR for d in diagnostics
        )
        if has_errors:
            return ParseResult(
                pending_import=None,
                diagnostics=tuple(diagnostics),
                layout=self.layout,
            )

        # Build successful result
        # At this point emission_date and total_value are guaranteed non-None
        assert emission_date is not None
        assert total_value is not None

        pending_import = PendingPurchaseImport(
            store_id=BEM_MAIOR_STORE_ID,
            date=emission_date,
            total_value=quantize_money(total_value),
            source_pdf=source_pdf,
            items=tuple(items),
        )

        return ParseResult(
            pending_import=pending_import,
            diagnostics=tuple(diagnostics),
            layout=self.layout,
        )


__all__ = [
    "BEM_MAIOR_STORE_ID",
    "BemMaiorParser",
]
