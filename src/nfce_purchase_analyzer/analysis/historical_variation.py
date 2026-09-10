"""Historical price variation within a single store."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from nfce_purchase_analyzer.analysis.selection import PurchaseAnalysisSelection
from nfce_purchase_analyzer.domain.models import Category, Product, PurchaseItem

_DEFAULT_BUCKET = "Sem categoria"
_PCT_QUANT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class HistoricalPriceVariationEntry:
    """A single historical price comparison for one product."""

    product_internal_code: str
    product_name: str
    category_name: str
    previous_purchase_date: datetime | None
    current_purchase_date: datetime | None
    previous_unit_price: Decimal
    current_unit_price: Decimal
    absolute_variation: Decimal
    percentage_variation: Decimal


@dataclass(frozen=True, slots=True)
class HistoricalPriceVariationResult:
    """Historical price movements grouped by product and category."""

    by_product: dict[str, tuple[HistoricalPriceVariationEntry, ...]]
    by_category: dict[str, tuple[HistoricalPriceVariationEntry, ...]]


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(_PCT_QUANT, rounding=ROUND_HALF_UP)


def _percentage_variation(current: Decimal, previous: Decimal) -> Decimal:
    if previous == Decimal("0"):
        return Decimal("0")
    percentage = ((current - previous) / previous) * Decimal("100")
    return _round_money(percentage)


def _normalize_history(
    history: dict[str, tuple[HistoricalPriceVariationEntry, ...]],
) -> dict[str, tuple[HistoricalPriceVariationEntry, ...]]:
    return {
        key: tuple(history[key])
        for key in sorted(history, key=lambda item: item.lower())
    }


def calculate_historical_price_variation(
    selection: PurchaseAnalysisSelection,
    *,
    items: Iterable[PurchaseItem] = (),
    products: Iterable[Product] = (),
    categories: Iterable[Category] = (),
) -> HistoricalPriceVariationResult:
    """Calculate price changes for selected item histories within a single store."""
    if not isinstance(selection, PurchaseAnalysisSelection):
        raise TypeError("selection must be a PurchaseAnalysisSelection")

    item_tuple = tuple(items)
    product_tuple = tuple(products)
    category_tuple = tuple(categories)

    for item in item_tuple:
        if not isinstance(item, PurchaseItem):
            raise TypeError("items must contain only PurchaseItem instances")
    for product in product_tuple:
        if not isinstance(product, Product):
            raise TypeError("products must contain only Product instances")
    for category in category_tuple:
        if not isinstance(category, Category):
            raise TypeError("categories must contain only Category instances")

    selected_by_id = {purchase.id: purchase for purchase in selection.purchases}
    product_by_code: dict[str, Product] = {}
    for product in product_tuple:
        product_by_code[product.internal_code] = product

    category_by_id: dict[str, Category] = {}
    for category in category_tuple:
        category_by_id[str(category.id)] = category

    history_by_code: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for item in item_tuple:
        if item.purchase_id not in selected_by_id:
            continue

        product = product_by_code.get(item.internal_code)
        category_name = _DEFAULT_BUCKET
        if product is not None and product.category_id is not None:
            category = category_by_id.get(str(product.category_id))
            if category is not None:
                category_name = category.name
        history_by_code[item.internal_code].append(
            {
                "purchase_date": selected_by_id[item.purchase_id].date,
                "raw_name": item.raw_name,
                "category_name": category_name,
                "unit_price": item.unit_price,
            }
        )

    by_product: dict[str, tuple[HistoricalPriceVariationEntry, ...]] = {}
    by_category: defaultdict[str, list[HistoricalPriceVariationEntry]] = defaultdict(list)

    for code in sorted(history_by_code):
        ordered = sorted(
            history_by_code[code],
            key=lambda record: record["purchase_date"],
        )

        entries: list[HistoricalPriceVariationEntry] = []
        for index in range(1, len(ordered)):
            previous = ordered[index - 1]
            current = ordered[index]
            previous_date = previous["purchase_date"]
            current_date = current["purchase_date"]
            previous_price = previous["unit_price"]
            current_price = current["unit_price"]
            current_name = current["raw_name"]
            category_name = current["category_name"]

            entries.append(
                HistoricalPriceVariationEntry(
                    product_internal_code=code,
                    product_name=str(current_name),
                    category_name=str(category_name),
                    previous_purchase_date=previous_date,
                    current_purchase_date=current_date,
                    previous_unit_price=previous_price,
                    current_unit_price=current_price,
                    absolute_variation=_round_money(current_price - previous_price),
                    percentage_variation=_percentage_variation(
                        current_price,
                        previous_price,
                    ),
                )
            )

        if not entries:
            first = ordered[0]
            entries.append(
                HistoricalPriceVariationEntry(
                    product_internal_code=code,
                    product_name=str(first["raw_name"]),
                    category_name=str(first["category_name"]),
                    previous_purchase_date=None,
                    current_purchase_date=first["purchase_date"],
                    previous_unit_price=first["unit_price"],
                    current_unit_price=first["unit_price"],
                    absolute_variation=Decimal("0"),
                    percentage_variation=Decimal("0"),
                )
            )

        by_product[code] = tuple(entries)
        for entry in entries:
            by_category[entry.category_name].append(entry)

    normalized_by_product = _normalize_history(by_product)
    normalized_by_category = {
        key: tuple(value)
        for key, value in sorted(
            ((category, tuple(entries)) for category, entries in by_category.items()),
            key=lambda item: item[0].lower(),
        )
    }

    return HistoricalPriceVariationResult(
        by_product=normalized_by_product,
        by_category=normalized_by_category,
    )


__all__ = [
    "HistoricalPriceVariationEntry",
    "HistoricalPriceVariationResult",
    "calculate_historical_price_variation",
]
