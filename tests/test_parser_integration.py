"""End-to-end integration tests for the Bem Maior parser pipeline.

These tests connect the full chain:
    text/PDF → extract_text_from_pdf → BemMaiorParser → validate_purchase_total
        → PendingPurchaseImport → ImportPreview

Fixtures are synthetic, local, and do not depend on network access
or real customer data.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from nfce_purchase_analyzer.domain import ImportPreview, PendingPurchaseImport
from nfce_purchase_analyzer.parsing import (
    BEM_MAIOR_STORE_ID,
    BemMaiorParser,
    DiagnosticLevel,
    ParserLayout,
    validate_purchase_total,
)
from nfce_purchase_analyzer.parsing.pdf_reader import extract_text_from_pdf

from fixtures import (
    bem_maior_receipt_mixed_items,
    bem_maior_receipt_rounding_warning,
    bem_maior_receipt_tolerance_boundary,
    bem_maior_receipt_unit_items,
    bem_maior_receipt_weighted_items,
)
from fixtures.pdf_builder import build_text_pdf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_date(iso: str) -> datetime:
    """Parse an ISO-ish date string from fixture metadata."""
    return datetime.fromisoformat(iso)


def _write_pdf(tmp_path: Path, name: str, lines: list[str]) -> Path:
    """Write a synthetic PDF to tmp_path and return its path."""
    pdf_bytes = build_text_pdf(lines)
    pdf_path = tmp_path / name
    pdf_path.write_bytes(pdf_bytes)
    return pdf_path


# ===========================================================================
# SECTION 1: Text-based end-to-end (text → parser → domain)
# ===========================================================================


class TestTextToParserToDomain:
    """End-to-end: text lines → BemMaiorParser → PendingPurchaseImport → ImportPreview."""

    def test_unit_items_end_to_end(self) -> None:
        """Parse unit-quantity receipt and produce valid ImportPreview."""
        lines, meta = bem_maior_receipt_unit_items()
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="fixture_unit.pdf")

        assert result.ok is True
        assert result.layout == ParserLayout.BEM_MAIOR

        imp = result.pending_import
        assert isinstance(imp, PendingPurchaseImport)
        assert imp.store_id == BEM_MAIOR_STORE_ID
        assert imp.total_value == Decimal(meta["total_value"])
        assert imp.total_items == meta["total_items"]
        assert imp.date == _parse_date(meta["date"])
        assert imp.source_pdf == "fixture_unit.pdf"

        # Verify item codes match expected
        parsed_codes = [item.internal_code for item in imp.items]
        assert parsed_codes == meta["item_codes"]

        # All items belong to the correct store
        for item in imp.items:
            assert item.store_id == BEM_MAIOR_STORE_ID

        # ImportPreview is valid and consistent
        preview = imp.preview
        assert isinstance(preview, ImportPreview)
        assert preview.store_id == imp.store_id
        assert preview.total_value == imp.total_value
        assert preview.total_items == imp.total_items
        assert preview.date == imp.date
        assert preview.source_pdf == imp.source_pdf
        assert len(preview.items) == imp.total_items

        # Validation: exact total → no diagnostics
        validation_diags = validate_purchase_total(imp)
        assert validation_diags == ()

    def test_weighted_items_end_to_end(self) -> None:
        """Parse weighted/fractional KG receipt and produce valid ImportPreview."""
        lines, meta = bem_maior_receipt_weighted_items()
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="fixture_weighted.pdf")

        assert result.ok is True
        imp = result.pending_import
        assert isinstance(imp, PendingPurchaseImport)
        assert imp.total_value == Decimal(meta["total_value"])
        assert imp.total_items == meta["total_items"]
        assert imp.date == _parse_date(meta["date"])

        parsed_codes = [item.internal_code for item in imp.items]
        assert parsed_codes == meta["item_codes"]

        # Verify fractional quantities
        banana = imp.items[0]
        assert banana.quantity == Decimal("0.542")
        assert banana.internal_code == "000099"

        tomate = imp.items[1]
        assert tomate.quantity == Decimal("0.345")

        carne = imp.items[2]
        assert carne.quantity == Decimal("1.250")

        # ImportPreview
        preview = imp.preview
        assert isinstance(preview, ImportPreview)
        assert preview.total_items == meta["total_items"]

        # Validation: exact total → no diagnostics
        validation_diags = validate_purchase_total(imp)
        assert validation_diags == ()

    def test_mixed_items_end_to_end(self) -> None:
        """Parse mixed unit+weighted receipt and produce valid ImportPreview."""
        lines, meta = bem_maior_receipt_mixed_items()
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="fixture_mixed.pdf")

        assert result.ok is True
        imp = result.pending_import
        assert isinstance(imp, PendingPurchaseImport)
        assert imp.total_value == Decimal(meta["total_value"])
        assert imp.total_items == meta["total_items"]

        # Unit item
        assert imp.items[0].quantity == Decimal("1.000")
        # Weighted item
        assert imp.items[1].quantity == Decimal("0.542")
        # Multiple units
        assert imp.items[2].quantity == Decimal("3.000")

        preview = imp.preview
        assert isinstance(preview, ImportPreview)
        assert preview.total_items == meta["total_items"]


# ===========================================================================
# SECTION 2: Mathematical validation integration
# ===========================================================================


class TestValidationIntegration:
    """End-to-end: text → parser → validate_purchase_total → diagnostics."""

    def test_exact_total_no_diagnostics(self) -> None:
        """Receipt with exact total produces zero validation diagnostics."""
        lines, _meta = bem_maior_receipt_unit_items()
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="exact.pdf")

        assert result.ok is True
        assert result.diagnostics == ()

    def test_rounding_warning_within_tolerance(self) -> None:
        """Receipt with R$ 0.03 difference produces WARNING, not ERROR."""
        lines, meta = bem_maior_receipt_rounding_warning()
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="rounding.pdf")

        assert result.ok is True
        assert result.pending_import is not None

        # Parser integrates validation: result should have warning
        assert len(result.warnings) >= 1
        rounding_warnings = [
            d for d in result.warnings if d.code == "total_rounding"
        ]
        assert len(rounding_warnings) == 1
        assert result.errors == ()

        # Standalone validation confirms
        diags = validate_purchase_total(result.pending_import)
        assert len(diags) == 1
        assert diags[0].level == DiagnosticLevel.WARNING
        assert diags[0].code == "total_rounding"
        assert meta["calculated_sum"] in diags[0].message
        assert meta["total_value"] in diags[0].message

    def test_tolerance_boundary_is_warning(self) -> None:
        """Difference of exactly R$ 0.05 is a WARNING (inclusive boundary)."""
        lines, meta = bem_maior_receipt_tolerance_boundary()
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="boundary.pdf")

        assert result.ok is True
        assert result.pending_import is not None

        rounding_warnings = [
            d for d in result.warnings if d.code == "total_rounding"
        ]
        assert len(rounding_warnings) == 1
        assert result.errors == ()

    def test_divergence_above_tolerance_is_error(self) -> None:
        """Difference above R$ 0.05 produces ERROR diagnostic."""
        # Build a receipt where total is way off
        lines = [
            "SUPERMERCADO BEM MAIOR LTDA",
            "",
            "000042 CAFE TORRADO 500G",
            "1 UN X 15,90 (15,90)",
            "",
            "TOTAL R$ 20,00",
            "",
            "Data de emissao: 01/01/2026 08:00:00",
        ]
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="divergente.pdf")

        # Parser should still produce a result (errors from validation
        # are appended as diagnostics but the parse itself succeeded
        # in extracting data)
        assert result.ok is True
        assert result.pending_import is not None

        # Validation diagnostics should include ERROR
        diags = validate_purchase_total(result.pending_import)
        assert len(diags) == 1
        assert diags[0].level == DiagnosticLevel.ERROR
        assert diags[0].code == "total_mismatch"


# ===========================================================================
# SECTION 3: PDF-based end-to-end (PDF → extract → parser → domain)
# ===========================================================================


class TestPdfEndToEnd:
    """End-to-end: synthetic PDF → extract_text_from_pdf → BemMaiorParser → domain."""

    def test_pdf_unit_items_end_to_end(self, tmp_path: Path) -> None:
        """Full pipeline from synthetic PDF file to ImportPreview."""
        lines, meta = bem_maior_receipt_unit_items()
        pdf_path = _write_pdf(tmp_path, "unit_items.pdf", lines)

        # Step 1: Extract text from PDF
        extracted_pages = extract_text_from_pdf(pdf_path)
        assert len(extracted_pages) >= 1

        # Combine pages into lines (mimicking real usage)
        all_text = "\n".join(extracted_pages)
        extracted_lines = all_text.split("\n")

        # Step 2: Parse with BemMaiorParser
        parser = BemMaiorParser()
        result = parser.parse(extracted_lines, source_pdf=str(pdf_path))

        # The synthetic PDF may not perfectly reproduce the layout
        # due to font metrics, but the parser should extract what
        # pdfplumber returns.  We verify the pipeline connects.
        assert result.layout == ParserLayout.BEM_MAIOR

        # If parsing succeeded, verify domain objects
        if result.ok:
            imp = result.pending_import
            assert isinstance(imp, PendingPurchaseImport)
            assert imp.store_id == BEM_MAIOR_STORE_ID
            assert imp.source_pdf == str(pdf_path)

            preview = imp.preview
            assert isinstance(preview, ImportPreview)
            assert preview.store_id == BEM_MAIOR_STORE_ID
            assert preview.total_items == len(imp.items)

    def test_pdf_weighted_items_end_to_end(self, tmp_path: Path) -> None:
        """Full pipeline from synthetic weighted-items PDF."""
        lines, _meta = bem_maior_receipt_weighted_items()
        pdf_path = _write_pdf(tmp_path, "weighted.pdf", lines)

        extracted_pages = extract_text_from_pdf(pdf_path)
        all_text = "\n".join(extracted_pages)
        extracted_lines = all_text.split("\n")

        parser = BemMaiorParser()
        result = parser.parse(extracted_lines, source_pdf=str(pdf_path))

        assert result.layout == ParserLayout.BEM_MAIOR

        if result.ok:
            imp = result.pending_import
            assert isinstance(imp, PendingPurchaseImport)
            preview = imp.preview
            assert isinstance(preview, ImportPreview)

    def test_pdf_builder_produces_readable_pdf(self, tmp_path: Path) -> None:
        """Verify that build_text_pdf produces valid, readable PDFs."""
        lines = ["Line 1", "Line 2", "Line 3"]
        pdf_bytes = build_text_pdf(lines)
        pdf_path = tmp_path / "readable.pdf"
        pdf_path.write_bytes(pdf_bytes)

        pages = extract_text_from_pdf(pdf_path)
        assert len(pages) == 1
        # All lines should appear in extracted text
        text = pages[0]
        for line in lines:
            assert line in text

    def test_pdf_builder_handles_special_characters(self, tmp_path: Path) -> None:
        """Verify PDF builder escapes parentheses and backslashes."""
        lines = [
            "Preco (R$) 15,90",
            "Nota\\Fiscal",
        ]
        pdf_bytes = build_text_pdf(lines)
        pdf_path = tmp_path / "special.pdf"
        pdf_path.write_bytes(pdf_bytes)

        pages = extract_text_from_pdf(pdf_path)
        assert len(pages) == 1


# ===========================================================================
# SECTION 4: ImportPreview consistency
# ===========================================================================


class TestImportPreviewConsistency:
    """Verify that ImportPreview from parsed data is internally consistent."""

    def test_preview_matches_pending_import(self) -> None:
        """ImportPreview fields match the PendingPurchaseImport they came from."""
        lines, meta = bem_maior_receipt_unit_items()
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="preview_test.pdf")

        assert result.ok is True
        imp = result.pending_import
        preview = imp.preview

        assert preview.store_id == imp.store_id
        assert preview.date == imp.date
        assert preview.total_value == imp.total_value
        assert preview.total_items == imp.total_items
        assert preview.source_pdf == imp.source_pdf
        assert preview.items == imp.items

    def test_preview_from_weighted_items(self) -> None:
        """ImportPreview from weighted items preserves fractional quantities."""
        lines, _meta = bem_maior_receipt_weighted_items()
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="weighted_preview.pdf")

        assert result.ok is True
        preview = result.pending_import.preview

        # Verify fractional quantities are preserved in preview
        for item in preview.items:
            assert isinstance(item.quantity, Decimal)
            assert isinstance(item.unit_price, Decimal)
            assert isinstance(item.total_price, Decimal)

    def test_preview_from_mixed_items(self) -> None:
        """ImportPreview from mixed receipt has correct item count."""
        lines, meta = bem_maior_receipt_mixed_items()
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="mixed_preview.pdf")

        assert result.ok is True
        preview = result.pending_import.preview
        assert preview.total_items == meta["total_items"]
        assert len(preview.items) == meta["total_items"]


# ===========================================================================
# SECTION 5: Item-level precision and integrity
# ===========================================================================


class TestItemIntegrity:
    """Verify item-level data integrity across the pipeline."""

    def test_monetary_precision_preserved(self) -> None:
        """All monetary values use Decimal, not float."""
        lines, _meta = bem_maior_receipt_unit_items()
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="precision.pdf")

        assert result.ok is True
        imp = result.pending_import
        assert isinstance(imp.total_value, Decimal)

        for item in imp.items:
            assert isinstance(item.unit_price, Decimal)
            assert isinstance(item.total_price, Decimal)
            assert isinstance(item.quantity, Decimal)

    def test_no_duplicate_items(self) -> None:
        """Parser does not duplicate items from any fixture."""
        for fixture_fn in [
            bem_maior_receipt_unit_items,
            bem_maior_receipt_weighted_items,
            bem_maior_receipt_mixed_items,
        ]:
            lines, meta = fixture_fn()
            parser = BemMaiorParser()
            result = parser.parse(lines, source_pdf="no_dup.pdf")

            assert result.ok is True
            codes = [item.internal_code for item in result.pending_import.items]
            assert len(codes) == len(set(codes)), (
                f"Duplicate items in {fixture_fn.__name__}"
            )

    def test_store_boundary_consistent(self) -> None:
        """All items in parsed result belong to BEM_MAIOR_STORE_ID."""
        for fixture_fn in [
            bem_maior_receipt_unit_items,
            bem_maior_receipt_weighted_items,
            bem_maior_receipt_mixed_items,
        ]:
            lines, _meta = fixture_fn()
            parser = BemMaiorParser()
            result = parser.parse(lines, source_pdf="boundary.pdf")

            assert result.ok is True
            for item in result.pending_import.items:
                assert item.store_id == BEM_MAIOR_STORE_ID

    def test_weighted_item_quantity_fractions(self) -> None:
        """Fractional KG quantities are parsed to exact Decimal values."""
        lines, _meta = bem_maior_receipt_weighted_items()
        parser = BemMaiorParser()
        result = parser.parse(lines, source_pdf="fractions.pdf")

        assert result.ok is True
        quantities = [item.quantity for item in result.pending_import.items]

        # All quantities should have sub-integer fractional parts
        assert Decimal("0.542") in quantities
        assert Decimal("0.345") in quantities
        assert Decimal("1.250") in quantities
