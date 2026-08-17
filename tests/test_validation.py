"""Tests for mathematical validation of NFC-e purchase totals."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from nfce_purchase_analyzer.deterministic import MONEY_TOLERANCE, quantize_money
from nfce_purchase_analyzer.domain import PendingPurchaseImport, PendingPurchaseItem
from nfce_purchase_analyzer.parsing.contracts import DiagnosticLevel
from nfce_purchase_analyzer.parsing.validation import validate_purchase_total


_STORE_ID = uuid.uuid5(uuid.UUID("00000000-0000-0000-0000-000000000001"), "test_store")
_DATE = datetime(2026, 1, 15, 10, 30, 0)
_SOURCE_PDF = "test_receipt.pdf"


def _make_item(
    code: str,
    name: str,
    quantity: str,
    unit_price: str,
    total_price: str,
) -> PendingPurchaseItem:
    """Create a PendingPurchaseItem for testing."""
    return PendingPurchaseItem(
        store_id=_STORE_ID,
        internal_code=code,
        raw_name=name,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
    )


def _make_import(
    items: list[PendingPurchaseItem],
    total_value: str,
) -> PendingPurchaseImport:
    """Create a PendingPurchaseImport for testing."""
    return PendingPurchaseImport(
        store_id=_STORE_ID,
        date=_DATE,
        total_value=total_value,
        source_pdf=_SOURCE_PDF,
        items=tuple(items),
    )


# -------------------------------------------------------------------------
# Exact match — no diagnostics
# -------------------------------------------------------------------------


class TestExactMatch:
    """Tests where the sum of items exactly equals the declared total."""

    def test_single_item_exact(self) -> None:
        items = [_make_item("001", "Arroz 5kg", "1", "25.90", "25.90")]
        pending = _make_import(items, "25.90")
        diagnostics = validate_purchase_total(pending)
        assert diagnostics == ()

    def test_multiple_items_exact(self) -> None:
        items = [
            _make_item("001", "Arroz 5kg", "1", "25.90", "25.90"),
            _make_item("002", "Feijao 1kg", "2", "8.50", "17.00"),
            _make_item("003", "Oleo 900ml", "1", "7.49", "7.49"),
        ]
        total = quantize_money(Decimal("25.90") + Decimal("17.00") + Decimal("7.49"))
        pending = _make_import(items, str(total))
        diagnostics = validate_purchase_total(pending)
        assert diagnostics == ()

    def test_weighted_items_exact(self) -> None:
        items = [
            _make_item("010", "Banana Prata", "1.542", "5.99", "9.24"),
            _make_item("011", "Tomate", "0.800", "8.90", "7.12"),
        ]
        total = quantize_money(Decimal("9.24") + Decimal("7.12"))
        pending = _make_import(items, str(total))
        diagnostics = validate_purchase_total(pending)
        assert diagnostics == ()


# -------------------------------------------------------------------------
# Within tolerance — WARNING diagnostic
# -------------------------------------------------------------------------


class TestWithinTolerance:
    """Tests where the difference is within MONEY_TOLERANCE (R$ 0.05)."""

    def test_difference_one_cent(self) -> None:
        """Sum exceeds declared total by R$ 0.01."""
        items = [
            _make_item("001", "Arroz 5kg", "1", "25.90", "25.90"),
            _make_item("002", "Feijao 1kg", "1", "8.50", "8.50"),
        ]
        # Declared total is 1 cent less than the sum
        actual_sum = Decimal("25.90") + Decimal("8.50")  # 34.40
        declared = quantize_money(actual_sum - Decimal("0.01"))  # 34.39
        pending = _make_import(items, str(declared))

        diagnostics = validate_purchase_total(pending)
        assert len(diagnostics) == 1
        diag = diagnostics[0]
        assert diag.level == DiagnosticLevel.WARNING
        assert diag.code == "total_rounding"
        assert "0.01" in diag.message

    def test_difference_three_cents(self) -> None:
        """Sum exceeds declared total by R$ 0.03."""
        items = [_make_item("001", "Cafe 500g", "1", "15.90", "15.90")]
        declared = quantize_money(Decimal("15.90") - Decimal("0.03"))  # 15.87
        pending = _make_import(items, str(declared))

        diagnostics = validate_purchase_total(pending)
        assert len(diagnostics) == 1
        assert diagnostics[0].level == DiagnosticLevel.WARNING
        assert diagnostics[0].code == "total_rounding"

    def test_difference_exactly_at_tolerance(self) -> None:
        """Difference is exactly R$ 0.05 — should still be WARNING."""
        items = [_make_item("001", "Leite 1L", "1", "6.50", "6.50")]
        declared = quantize_money(Decimal("6.50") - Decimal("0.05"))  # 6.45
        pending = _make_import(items, str(declared))

        diagnostics = validate_purchase_total(pending)
        assert len(diagnostics) == 1
        diag = diagnostics[0]
        assert diag.level == DiagnosticLevel.WARNING
        assert diag.code == "total_rounding"
        assert "0.05" in diag.message

    def test_negative_difference_within_tolerance(self) -> None:
        """Declared total exceeds the sum by R$ 0.02."""
        items = [_make_item("001", "Pao Frances", "1", "12.00", "12.00")]
        declared = quantize_money(Decimal("12.00") + Decimal("0.02"))  # 12.02
        pending = _make_import(items, str(declared))

        diagnostics = validate_purchase_total(pending)
        assert len(diagnostics) == 1
        assert diagnostics[0].level == DiagnosticLevel.WARNING
        assert diagnostics[0].code == "total_rounding"

    def test_tolerance_matches_money_tolerance_constant(self) -> None:
        """Ensure the function uses the project's MONEY_TOLERANCE constant."""
        items = [_make_item("001", "Item A", "1", "10.00", "10.00")]
        # Difference exactly at MONEY_TOLERANCE
        declared = quantize_money(Decimal("10.00") - MONEY_TOLERANCE)
        pending = _make_import(items, str(declared))

        diagnostics = validate_purchase_total(pending)
        assert len(diagnostics) == 1
        assert diagnostics[0].level == DiagnosticLevel.WARNING


# -------------------------------------------------------------------------
# Above tolerance — ERROR diagnostic
# -------------------------------------------------------------------------


class TestAboveTolerance:
    """Tests where the difference exceeds MONEY_TOLERANCE (R$ 0.05)."""

    def test_difference_six_cents(self) -> None:
        """Sum exceeds declared total by R$ 0.06."""
        items = [_make_item("001", "Sabao Po", "1", "18.90", "18.90")]
        declared = quantize_money(Decimal("18.90") - Decimal("0.06"))  # 18.84
        pending = _make_import(items, str(declared))

        diagnostics = validate_purchase_total(pending)
        assert len(diagnostics) == 1
        diag = diagnostics[0]
        assert diag.level == DiagnosticLevel.ERROR
        assert diag.code == "total_mismatch"
        assert "0.06" in diag.message

    def test_difference_ten_cents(self) -> None:
        """Sum exceeds declared total by R$ 0.10."""
        items = [
            _make_item("001", "Arroz 5kg", "1", "25.90", "25.90"),
            _make_item("002", "Feijao 1kg", "1", "8.50", "8.50"),
        ]
        actual_sum = Decimal("25.90") + Decimal("8.50")  # 34.40
        declared = quantize_money(actual_sum - Decimal("0.10"))  # 34.30
        pending = _make_import(items, str(declared))

        diagnostics = validate_purchase_total(pending)
        assert len(diagnostics) == 1
        assert diagnostics[0].level == DiagnosticLevel.ERROR
        assert diagnostics[0].code == "total_mismatch"

    def test_large_difference(self) -> None:
        """Sum exceeds declared total by R$ 5.00."""
        items = [
            _make_item("001", "Carne kg", "2", "45.00", "90.00"),
            _make_item("002", "Queijo kg", "1", "30.00", "30.00"),
        ]
        pending = _make_import(items, "115.00")

        diagnostics = validate_purchase_total(pending)
        assert len(diagnostics) == 1
        assert diagnostics[0].level == DiagnosticLevel.ERROR
        assert diagnostics[0].code == "total_mismatch"

    def test_negative_difference_above_tolerance(self) -> None:
        """Declared total exceeds the sum by R$ 0.10."""
        items = [_make_item("001", "Macarrao", "1", "5.00", "5.00")]
        declared = quantize_money(Decimal("5.00") + Decimal("0.10"))  # 5.10
        pending = _make_import(items, str(declared))

        diagnostics = validate_purchase_total(pending)
        assert len(diagnostics) == 1
        assert diagnostics[0].level == DiagnosticLevel.ERROR
        assert diagnostics[0].code == "total_mismatch"


# -------------------------------------------------------------------------
# Diagnostic message content
# -------------------------------------------------------------------------


class TestDiagnosticMessages:
    """Tests that diagnostic messages contain the expected values."""

    def test_warning_message_contains_values(self) -> None:
        items = [_make_item("001", "Item A", "1", "10.00", "10.00")]
        pending = _make_import(items, "9.97")

        diagnostics = validate_purchase_total(pending)
        assert len(diagnostics) == 1
        msg = diagnostics[0].message
        assert "10.00" in msg  # calculated
        assert "9.97" in msg   # declared
        assert "0.03" in msg   # difference

    def test_error_message_contains_values(self) -> None:
        items = [_make_item("001", "Item A", "1", "10.00", "10.00")]
        pending = _make_import(items, "9.50")

        diagnostics = validate_purchase_total(pending)
        assert len(diagnostics) == 1
        msg = diagnostics[0].message
        assert "10.00" in msg  # calculated
        assert "9.50" in msg   # declared
        assert "0.50" in msg   # difference


# -------------------------------------------------------------------------
# Input validation
# -------------------------------------------------------------------------


class TestInputValidation:
    """Tests for invalid input handling."""

    def test_rejects_non_pending_import(self) -> None:
        with pytest.raises(TypeError, match="PendingPurchaseImport"):
            validate_purchase_total("not_a_pending_import")  # type: ignore[arg-type]

    def test_rejects_none(self) -> None:
        with pytest.raises(TypeError, match="PendingPurchaseImport"):
            validate_purchase_total(None)  # type: ignore[arg-type]


# -------------------------------------------------------------------------
# Integration with BemMaiorParser
# -------------------------------------------------------------------------


class TestBemMaiorParserIntegration:
    """Tests that BemMaiorParser includes validation diagnostics."""

    def test_parser_emits_validation_warning_on_rounding(self) -> None:
        """Parser should emit total_rounding warning when sum differs
        from total within tolerance."""
        from nfce_purchase_analyzer.parsing import BemMaiorParser

        parser = BemMaiorParser()
        lines = [
            "CUPOM FISCAL ELETRONICO",
            "Data de emissao: 15/01/2026 10:30:00",
            "000001 ARROZ 5KG",
            "1 UN X 25,90 (25,90)",
            "000002 FEIJAO 1KG",
            "1 UN X 8,50 (8,50)",
            # Total is 0.02 less than item sum (34.40)
            "TOTAL R$ 34,38",
        ]
        result = parser.parse(lines, source_pdf="test.pdf")
        assert result.ok
        assert result.pending_import is not None

        rounding_warnings = [
            d for d in result.diagnostics if d.code == "total_rounding"
        ]
        assert len(rounding_warnings) == 1
        assert rounding_warnings[0].level == DiagnosticLevel.WARNING

    def test_parser_emits_validation_error_on_mismatch(self) -> None:
        """Parser should emit total_mismatch error when sum differs
        from total above tolerance."""
        from nfce_purchase_analyzer.parsing import BemMaiorParser

        parser = BemMaiorParser()
        lines = [
            "CUPOM FISCAL ELETRONICO",
            "Data de emissao: 15/01/2026 10:30:00",
            "000001 ARROZ 5KG",
            "1 UN X 25,90 (25,90)",
            "000002 FEIJAO 1KG",
            "1 UN X 8,50 (8,50)",
            # Total is 0.10 less than item sum (34.40)
            "TOTAL R$ 34,30",
        ]
        result = parser.parse(lines, source_pdf="test.pdf")
        # Parse still succeeds (pending_import is populated) but has
        # error diagnostic — the decision whether to reject the import
        # based on validation errors belongs to downstream consumers.
        assert result.pending_import is not None

        mismatch_errors = [
            d for d in result.diagnostics if d.code == "total_mismatch"
        ]
        assert len(mismatch_errors) == 1
        assert mismatch_errors[0].level == DiagnosticLevel.ERROR

    def test_parser_no_validation_diagnostics_on_exact_match(self) -> None:
        """Parser should emit no validation diagnostics when totals match."""
        from nfce_purchase_analyzer.parsing import BemMaiorParser

        parser = BemMaiorParser()
        lines = [
            "CUPOM FISCAL ELETRONICO",
            "Data de emissao: 15/01/2026 10:30:00",
            "000001 ARROZ 5KG",
            "1 UN X 25,90 (25,90)",
            "000002 FEIJAO 1KG",
            "1 UN X 8,50 (8,50)",
            "TOTAL R$ 34,40",
        ]
        result = parser.parse(lines, source_pdf="test.pdf")
        assert result.ok

        validation_diags = [
            d
            for d in result.diagnostics
            if d.code in ("total_rounding", "total_mismatch")
        ]
        assert len(validation_diags) == 0
