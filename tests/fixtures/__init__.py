"""Synthetic fixtures for the Bem Maior NFC-e layout.

These fixtures produce representative ``list[str]`` text lines
that mirror the Bem Maior supermarket receipt layout.  They are
used by integration tests and do **not** depend on network access
or real customer data.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Unit items — exact total
# ---------------------------------------------------------------------------


def bem_maior_receipt_unit_items() -> tuple[list[str], dict[str, object]]:
    """Receipt with three unit-quantity items whose total is exact.

    Returns:
        A tuple of (text_lines, expected_metadata) where
        *expected_metadata* documents the values a correct parse
        must produce.
    """
    lines = [
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
    metadata = {
        "total_value": "69.69",
        "total_items": 3,
        "date": "2026-08-15T14:30:25",
        "item_codes": ["000042", "000088", "000101"],
    }
    return lines, metadata


# ---------------------------------------------------------------------------
# Weighted / fractional KG items — exact total
# ---------------------------------------------------------------------------


def bem_maior_receipt_weighted_items() -> tuple[list[str], dict[str, object]]:
    """Receipt with weighted items (KG) whose total is exact.

    Returns:
        A tuple of (text_lines, expected_metadata).
    """
    lines = [
        "SUPERMERCADO BEM MAIOR LTDA",
        "",
        "000099 BANANA PRATA",
        "0,542 KG X 5,99 (3,25)",
        "000200 TOMATE ITALIANO",
        "0,345 KG X 12,90 (4,45)",
        "000150 CARNE BOVINA ALCATRA",
        "1,250 KG X 49,90 (62,38)",
        "",
        "TOTAL R$ 70,08",
        "",
        "Emissao: 10/07/2026 09:15:00",
    ]
    metadata = {
        "total_value": "70.08",
        "total_items": 3,
        "date": "2026-07-10T09:15:00",
        "item_codes": ["000099", "000200", "000150"],
    }
    return lines, metadata


# ---------------------------------------------------------------------------
# Mixed unit + weighted items — exact total
# ---------------------------------------------------------------------------


def bem_maior_receipt_mixed_items() -> tuple[list[str], dict[str, object]]:
    """Receipt mixing unit and weighted items with exact total.

    Returns:
        A tuple of (text_lines, expected_metadata).
    """
    lines = [
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
    metadata = {
        "total_value": "86.65",
        "total_items": 3,
        "date": "2026-06-20T18:45:30",
        "item_codes": ["000042", "000099", "000088"],
    }
    return lines, metadata


# ---------------------------------------------------------------------------
# Rounding warning — difference within tolerance
# ---------------------------------------------------------------------------


def bem_maior_receipt_rounding_warning() -> tuple[list[str], dict[str, object]]:
    """Receipt whose item sum differs from declared total within R$ 0.05.

    The item total_price is 4.45 but the declared total is 4.48,
    causing a R$ 0.03 difference (within tolerance).

    Returns:
        A tuple of (text_lines, expected_metadata).
    """
    lines = [
        "SUPERMERCADO BEM MAIOR LTDA",
        "",
        "000200 TOMATE ITALIANO",
        "0,345 KG X 12,90 (4,45)",
        "",
        "TOTAL R$ 4,48",
        "",
        "Data de emissao: 01/03/2026 10:00:00",
    ]
    metadata = {
        "total_value": "4.48",
        "total_items": 1,
        "date": "2026-03-01T10:00:00",
        "item_codes": ["000200"],
        "expect_rounding_warning": True,
        "calculated_sum": "4.45",
        "difference": "0.03",
    }
    return lines, metadata


# ---------------------------------------------------------------------------
# Multiple items with rounding difference exactly at tolerance boundary
# ---------------------------------------------------------------------------


def bem_maior_receipt_tolerance_boundary() -> tuple[list[str], dict[str, object]]:
    """Receipt with difference exactly at R$ 0.05 tolerance boundary.

    Item sum = 15.90, declared total = 15.95.
    Difference = R$ 0.05 (inclusive boundary → WARNING, not ERROR).

    Returns:
        A tuple of (text_lines, expected_metadata).
    """
    lines = [
        "SUPERMERCADO BEM MAIOR LTDA",
        "",
        "000042 CAFE TORRADO 500G",
        "1 UN X 15,90 (15,90)",
        "",
        "TOTAL R$ 15,95",
        "",
        "Data de emissao: 05/05/2026 12:00:00",
    ]
    metadata = {
        "total_value": "15.95",
        "total_items": 1,
        "date": "2026-05-05T12:00:00",
        "item_codes": ["000042"],
        "expect_rounding_warning": True,
        "calculated_sum": "15.90",
        "difference": "0.05",
    }
    return lines, metadata


__all__ = [
    "bem_maior_receipt_mixed_items",
    "bem_maior_receipt_rounding_warning",
    "bem_maior_receipt_tolerance_boundary",
    "bem_maior_receipt_unit_items",
    "bem_maior_receipt_weighted_items",
]
