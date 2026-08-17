"""Tests for the Bem Maior NFC-e parser."""

from datetime import datetime
from decimal import Decimal

import pytest

from nfce_purchase_analyzer.parsing import (
    BEM_MAIOR_STORE_ID,
    BemMaiorParser,
    DiagnosticLevel,
    ParseResult,
    ParserLayout,
    ParserRegistry,
)


# ---------------------------------------------------------------------------
# Representative text fixtures for Bem Maior layout
# ---------------------------------------------------------------------------

# Minimal valid receipt with unit items
VALID_RECEIPT_UNIT_ITEMS: list[str] = [
    "SUPERMERCADO BEM MAIOR LTDA",
    "CNPJ: 12.345.678/0001-99",
    "",
    "CODIGO DESCRICAO QTD UN VL UNIT VL TOTAL",
    "000042 CAFE TORRADO 500G",
    "1 UN X 15,90 (15,90)",
    "000088 ARROZ BRANCO 5KG",
    "2 UN X 22,50 (45,00)",
    "000101 OLEO SOJA 900ML",
    "1 UN X 8,79 (8,79)",
    "",
    "TOTAL R$ 69,69",
    "",
    "Data de emissao: 15/08/2026 14:30:25",
]

# Receipt with weighted (KG) items
VALID_RECEIPT_WEIGHTED_ITEMS: list[str] = [
    "SUPERMERCADO BEM MAIOR LTDA",
    "",
    "000042 CAFE TORRADO 500G",
    "1 UN X 15,90 (15,90)",
    "000099 BANANA PRATA",
    "0,542 KG X 5,99 (3,25)",
    "000150 CARNE BOVINA ALCATRA",
    "1,250 KG X 49,90 (62,38)",
    "",
    "TOTAL R$ 81,53",
    "",
    "Emissao: 10/07/2026 09:15:00",
]

# Receipt with mixed unit and weighted items
VALID_RECEIPT_MIXED: list[str] = [
    "SUPERMERCADO BEM MAIOR LTDA",
    "CNPJ: 12.345.678/0001-99",
    "",
    "000042 CAFE TORRADO 500G",
    "1 UN X 15,90 (15,90)",
    "000099 BANANA PRATA",
    "0,542 KG X 5,99 (3,25)",
    "000088 ARROZ BRANCO 5KG",
    "3 UN X 22,50 (67,50)",
    "",
    "TOTAL R$ 86,65",
    "",
    "Data de emissao: 20/06/2026 18:45:30",
]

# Receipt with no items
RECEIPT_NO_ITEMS: list[str] = [
    "SUPERMERCADO BEM MAIOR LTDA",
    "CNPJ: 12.345.678/0001-99",
    "",
    "TOTAL R$ 0,00",
    "",
    "Data de emissao: 15/08/2026 14:30:25",
]

# Receipt with no date
RECEIPT_NO_DATE: list[str] = [
    "SUPERMERCADO BEM MAIOR LTDA",
    "",
    "000042 CAFE TORRADO 500G",
    "1 UN X 15,90 (15,90)",
    "",
    "TOTAL R$ 15,90",
]

# Receipt with no total
RECEIPT_NO_TOTAL: list[str] = [
    "SUPERMERCADO BEM MAIOR LTDA",
    "",
    "000042 CAFE TORRADO 500G",
    "1 UN X 15,90 (15,90)",
    "",
    "Data de emissao: 15/08/2026 14:30:25",
]

# Receipt with date-only (no time)
RECEIPT_DATE_ONLY: list[str] = [
    "SUPERMERCADO BEM MAIOR LTDA",
    "",
    "000042 CAFE TORRADO 500G",
    "1 UN X 15,90 (15,90)",
    "",
    "TOTAL R$ 15,90",
    "",
    "15/08/2026",
]

# Receipt with fractional KG quantities (sub-kg items)
RECEIPT_FRACTIONAL_KG: list[str] = [
    "SUPERMERCADO BEM MAIOR LTDA",
    "",
    "000200 TOMATE ITALIANO",
    "0,345 KG X 12,90 (4,45)",
    "000201 CEBOLA BRANCA",
    "0,780 KG X 6,50 (5,07)",
    "",
    "TOTAL R$ 9,52",
    "",
    "Data de emissao: 01/01/2026 08:00:00",
]

# Receipt with "VALOR TOTAL" variant
RECEIPT_VALOR_TOTAL: list[str] = [
    "SUPERMERCADO BEM MAIOR LTDA",
    "",
    "000042 CAFE TORRADO 500G",
    "1 UN X 15,90 (15,90)",
    "",
    "VALOR TOTAL 15,90",
    "",
    "Data de emissao: 15/08/2026 14:30:25",
]

# Receipt with total without parentheses on item prices
RECEIPT_NO_PARENS: list[str] = [
    "SUPERMERCADO BEM MAIOR LTDA",
    "",
    "000042 CAFE TORRADO 500G",
    "1 UN X 15,90 15,90",
    "",
    "TOTAL R$ 15,90",
    "",
    "Data de emissao: 15/08/2026 14:30:25",
]

# Receipt with time without seconds
RECEIPT_TIME_NO_SECONDS: list[str] = [
    "SUPERMERCADO BEM MAIOR LTDA",
    "",
    "000042 CAFE TORRADO 500G",
    "1 UN X 15,90 (15,90)",
    "",
    "TOTAL R$ 15,90",
    "",
    "Data de emissao: 15/08/2026 14:30",
]


# ---------------------------------------------------------------------------
# Parser instantiation and protocol
# ---------------------------------------------------------------------------


def test_parser_has_bem_maior_layout() -> None:
    parser = BemMaiorParser()
    assert parser.layout == ParserLayout.BEM_MAIOR


def test_parser_satisfies_nfce_parser_protocol() -> None:
    """BemMaiorParser can be registered in the ParserRegistry."""
    registry = ParserRegistry()
    parser = BemMaiorParser()
    registry.register(parser)

    assert ParserLayout.BEM_MAIOR in registry
    assert registry.get(ParserLayout.BEM_MAIOR) is parser


# ---------------------------------------------------------------------------
# Successful parsing
# ---------------------------------------------------------------------------


def test_parse_valid_receipt_with_unit_items() -> None:
    parser = BemMaiorParser()
    result = parser.parse(VALID_RECEIPT_UNIT_ITEMS, source_pdf="compra1.pdf")

    assert result.ok is True
    assert result.layout == ParserLayout.BEM_MAIOR
    assert result.pending_import is not None

    imp = result.pending_import
    assert imp.store_id == BEM_MAIOR_STORE_ID
    assert imp.date == datetime(2026, 8, 15, 14, 30, 25)
    assert imp.total_value == Decimal("69.69")
    assert imp.source_pdf == "compra1.pdf"
    assert imp.total_items == 3

    items = imp.items
    assert len(items) == 3

    # First item: CAFE TORRADO 500G
    assert items[0].internal_code == "000042"
    assert items[0].raw_name == "CAFE TORRADO 500G"
    assert items[0].quantity == Decimal("1.000")
    assert items[0].unit_price == Decimal("15.90")
    assert items[0].total_price == Decimal("15.90")
    assert items[0].store_id == BEM_MAIOR_STORE_ID

    # Second item: ARROZ BRANCO 5KG
    assert items[1].internal_code == "000088"
    assert items[1].raw_name == "ARROZ BRANCO 5KG"
    assert items[1].quantity == Decimal("2.000")
    assert items[1].unit_price == Decimal("22.50")
    assert items[1].total_price == Decimal("45.00")

    # Third item: OLEO SOJA 900ML
    assert items[2].internal_code == "000101"
    assert items[2].raw_name == "OLEO SOJA 900ML"
    assert items[2].quantity == Decimal("1.000")
    assert items[2].unit_price == Decimal("8.79")
    assert items[2].total_price == Decimal("8.79")


def test_parse_valid_receipt_with_weighted_items() -> None:
    parser = BemMaiorParser()
    result = parser.parse(VALID_RECEIPT_WEIGHTED_ITEMS, source_pdf="pesados.pdf")

    assert result.ok is True
    imp = result.pending_import
    assert imp is not None
    assert imp.total_value == Decimal("81.53")
    assert imp.date == datetime(2026, 7, 10, 9, 15, 0)

    items = imp.items
    assert len(items) == 3

    # Weighted item: BANANA PRATA
    banana = items[1]
    assert banana.internal_code == "000099"
    assert banana.raw_name == "BANANA PRATA"
    assert banana.quantity == Decimal("0.542")
    assert banana.unit_price == Decimal("5.99")
    assert banana.total_price == Decimal("3.25")

    # Weighted item: CARNE BOVINA ALCATRA
    carne = items[2]
    assert carne.internal_code == "000150"
    assert carne.raw_name == "CARNE BOVINA ALCATRA"
    assert carne.quantity == Decimal("1.250")
    assert carne.unit_price == Decimal("49.90")
    assert carne.total_price == Decimal("62.38")


def test_parse_mixed_unit_and_weighted() -> None:
    parser = BemMaiorParser()
    result = parser.parse(VALID_RECEIPT_MIXED, source_pdf="misto.pdf")

    assert result.ok is True
    imp = result.pending_import
    assert imp is not None
    assert imp.total_items == 3
    assert imp.total_value == Decimal("86.65")
    assert imp.date == datetime(2026, 6, 20, 18, 45, 30)

    # Unit item
    assert imp.items[0].quantity == Decimal("1.000")
    # Weighted item
    assert imp.items[1].quantity == Decimal("0.542")
    # Multiple units
    assert imp.items[2].quantity == Decimal("3.000")


def test_parse_fractional_kg_items() -> None:
    parser = BemMaiorParser()
    result = parser.parse(RECEIPT_FRACTIONAL_KG, source_pdf="hortifruti.pdf")

    assert result.ok is True
    imp = result.pending_import
    assert imp is not None
    assert imp.total_items == 2

    tomate = imp.items[0]
    assert tomate.internal_code == "000200"
    assert tomate.raw_name == "TOMATE ITALIANO"
    assert tomate.quantity == Decimal("0.345")
    assert tomate.unit_price == Decimal("12.90")
    assert tomate.total_price == Decimal("4.45")

    cebola = imp.items[1]
    assert cebola.internal_code == "000201"
    assert cebola.quantity == Decimal("0.780")
    assert cebola.total_price == Decimal("5.07")


def test_parse_valor_total_variant() -> None:
    parser = BemMaiorParser()
    result = parser.parse(RECEIPT_VALOR_TOTAL, source_pdf="variante.pdf")

    assert result.ok is True
    assert result.pending_import is not None
    assert result.pending_import.total_value == Decimal("15.90")


def test_parse_item_price_without_parentheses() -> None:
    parser = BemMaiorParser()
    result = parser.parse(RECEIPT_NO_PARENS, source_pdf="sem_parens.pdf")

    assert result.ok is True
    assert result.pending_import is not None
    assert result.pending_import.items[0].total_price == Decimal("15.90")


def test_parse_time_without_seconds() -> None:
    parser = BemMaiorParser()
    result = parser.parse(RECEIPT_TIME_NO_SECONDS, source_pdf="curto.pdf")

    assert result.ok is True
    assert result.pending_import is not None
    assert result.pending_import.date == datetime(2026, 8, 15, 14, 30)


def test_parse_date_only_fallback() -> None:
    parser = BemMaiorParser()
    result = parser.parse(RECEIPT_DATE_ONLY, source_pdf="data_apenas.pdf")

    assert result.ok is True
    assert result.pending_import is not None
    assert result.pending_import.date == datetime(2026, 8, 15, 0, 0, 0)


def test_items_have_correct_store_id() -> None:
    parser = BemMaiorParser()
    result = parser.parse(VALID_RECEIPT_UNIT_ITEMS, source_pdf="loja.pdf")

    assert result.ok is True
    for item in result.pending_import.items:
        assert item.store_id == BEM_MAIOR_STORE_ID


def test_source_pdf_is_preserved() -> None:
    parser = BemMaiorParser()
    result = parser.parse(
        VALID_RECEIPT_UNIT_ITEMS,
        source_pdf="notas/2026/agosto/compra_bem_maior.pdf",
    )

    assert result.ok is True
    assert result.pending_import.source_pdf == (
        "notas/2026/agosto/compra_bem_maior.pdf"
    )


# ---------------------------------------------------------------------------
# Failure cases
# ---------------------------------------------------------------------------


def test_parse_empty_input() -> None:
    parser = BemMaiorParser()
    result = parser.parse([], source_pdf="vazio.pdf")

    assert result.ok is False
    assert result.pending_import is None
    assert len(result.errors) == 1
    assert result.errors[0].code == "empty_input"
    assert result.layout == ParserLayout.BEM_MAIOR


def test_parse_no_items_found() -> None:
    parser = BemMaiorParser()
    result = parser.parse(RECEIPT_NO_ITEMS, source_pdf="sem_itens.pdf")

    assert result.ok is False
    assert result.pending_import is None
    error_codes = {e.code for e in result.errors}
    assert "no_items" in error_codes


def test_parse_no_date_found() -> None:
    parser = BemMaiorParser()
    result = parser.parse(RECEIPT_NO_DATE, source_pdf="sem_data.pdf")

    assert result.ok is False
    assert result.pending_import is None
    error_codes = {e.code for e in result.errors}
    assert "missing_date" in error_codes


def test_parse_no_total_found() -> None:
    parser = BemMaiorParser()
    result = parser.parse(RECEIPT_NO_TOTAL, source_pdf="sem_total.pdf")

    assert result.ok is False
    assert result.pending_import is None
    error_codes = {e.code for e in result.errors}
    assert "missing_total" in error_codes


def test_parse_garbage_input() -> None:
    parser = BemMaiorParser()
    result = parser.parse(
        ["random text", "no structure here", "just noise"],
        source_pdf="lixo.pdf",
    )

    assert result.ok is False
    assert result.pending_import is None
    error_codes = {e.code for e in result.errors}
    # Should have at least missing_date, missing_total, no_items
    assert "missing_date" in error_codes
    assert "missing_total" in error_codes
    assert "no_items" in error_codes


# ---------------------------------------------------------------------------
# Diagnostic quality
# ---------------------------------------------------------------------------


def test_no_items_produces_all_error_diagnostics() -> None:
    """When all extraction fails, diagnostics cover date, total, and items."""
    parser = BemMaiorParser()
    result = parser.parse(
        ["nothing useful"],
        source_pdf="ruim.pdf",
    )

    assert result.ok is False
    error_codes = {e.code for e in result.errors}
    assert "missing_date" in error_codes
    assert "missing_total" in error_codes
    assert "no_items" in error_codes


def test_successful_parse_can_have_zero_diagnostics() -> None:
    parser = BemMaiorParser()
    result = parser.parse(VALID_RECEIPT_UNIT_ITEMS, source_pdf="limpo.pdf")

    assert result.ok is True
    assert result.diagnostics == ()


def test_warnings_do_not_prevent_success() -> None:
    """A receipt with warnings but all required data should succeed."""
    # Create receipt with a duplicate item that generates a warning
    lines = [
        "SUPERMERCADO BEM MAIOR LTDA",
        "",
        "000042 CAFE TORRADO 500G",
        "1 UN X 15,90 (15,90)",
        "000042 CAFE TORRADO 500G",
        "1 UN X 15,90 (15,90)",
        "",
        "TOTAL R$ 15,90",
        "",
        "Data de emissao: 15/08/2026 14:30:25",
    ]
    parser = BemMaiorParser()
    result = parser.parse(lines, source_pdf="duplicado.pdf")

    assert result.ok is True
    assert len(result.warnings) >= 1
    assert result.errors == ()
    # Only one item should be extracted (duplicate ignored)
    assert result.pending_import.total_items == 1


# ---------------------------------------------------------------------------
# No duplication
# ---------------------------------------------------------------------------


def test_parser_does_not_duplicate_items() -> None:
    """Spec requirement: parser must not duplicate items."""
    parser = BemMaiorParser()
    result = parser.parse(VALID_RECEIPT_UNIT_ITEMS, source_pdf="unico.pdf")

    assert result.ok is True
    codes = [item.internal_code for item in result.pending_import.items]
    # All codes in the fixture are unique, so no duplicates
    assert len(codes) == len(set(codes))


# ---------------------------------------------------------------------------
# Monetary precision
# ---------------------------------------------------------------------------


def test_monetary_values_are_precise() -> None:
    """Spec requirement: extracted values preserve monetary precision."""
    parser = BemMaiorParser()
    result = parser.parse(VALID_RECEIPT_UNIT_ITEMS, source_pdf="preciso.pdf")

    assert result.ok is True
    imp = result.pending_import
    # Total should be exact Decimal, not float-approximated
    assert imp.total_value == Decimal("69.69")
    assert isinstance(imp.total_value, Decimal)

    for item in imp.items:
        assert isinstance(item.unit_price, Decimal)
        assert isinstance(item.total_price, Decimal)
        assert isinstance(item.quantity, Decimal)
