"""CSV export helpers for analytical results."""

from __future__ import annotations

import csv
import io
from decimal import Decimal

from nfce_purchase_analyzer.analysis.historical_variation import (
    HistoricalPriceVariationEntry,
    HistoricalPriceVariationResult,
)
from nfce_purchase_analyzer.analysis.summary import PurchaseAnalysisSummary


def _format_decimal(value: Decimal) -> str:
    return format(value, "f")


def _write_csv(headers: list[str], rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def export_analysis_summary_csv(summary: PurchaseAnalysisSummary) -> str:
    """Export the analytical summary to CSV text."""

    if not isinstance(summary, PurchaseAnalysisSummary):
        raise TypeError("summary must be a PurchaseAnalysisSummary")

    rows = [
        {
            "metric": "total_value",
            "category": "",
            "value": _format_decimal(summary.total_value),
        }
    ]
    for category_name, value in summary.distribution.items():
        rows.append(
            {
                "metric": "category_distribution",
                "category": category_name,
                "value": _format_decimal(value),
            }
        )

    return _write_csv(["metric", "category", "value"], rows)


def _variation_row(entry: HistoricalPriceVariationEntry) -> dict[str, str]:
    return {
        "product_internal_code": entry.product_internal_code,
        "product_name": entry.product_name,
        "category_name": entry.category_name,
        "previous_purchase_date": ""
        if entry.previous_purchase_date is None
        else entry.previous_purchase_date.isoformat(),
        "current_purchase_date": ""
        if entry.current_purchase_date is None
        else entry.current_purchase_date.isoformat(),
        "previous_unit_price": _format_decimal(entry.previous_unit_price),
        "current_unit_price": _format_decimal(entry.current_unit_price),
        "absolute_variation": _format_decimal(entry.absolute_variation),
        "percentage_variation": _format_decimal(entry.percentage_variation),
    }


def export_historical_price_variation_csv(
    result: HistoricalPriceVariationResult,
) -> str:
    """Export historical variation entries to CSV text."""

    if not isinstance(result, HistoricalPriceVariationResult):
        raise TypeError("result must be a HistoricalPriceVariationResult")

    rows: list[dict[str, str]] = []
    for entries in result.by_product.values():
        for entry in entries:
            if not isinstance(entry, HistoricalPriceVariationEntry):
                raise TypeError(
                    "result must contain only HistoricalPriceVariationEntry values"
                )
            rows.append(_variation_row(entry))

    return _write_csv(
        [
            "product_internal_code",
            "product_name",
            "category_name",
            "previous_purchase_date",
            "current_purchase_date",
            "previous_unit_price",
            "current_unit_price",
            "absolute_variation",
            "percentage_variation",
        ],
        rows,
    )


__all__ = [
    "export_analysis_summary_csv",
    "export_historical_price_variation_csv",
]