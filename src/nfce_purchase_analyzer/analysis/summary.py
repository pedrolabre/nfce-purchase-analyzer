"""Aggregated summaries for selected purchases."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from nfce_purchase_analyzer.analysis.selection import PurchaseAnalysisSelection
from nfce_purchase_analyzer.domain.models import Category, Product, PurchaseItem

_DEFAULT_BUCKET = "Sem categoria"


@dataclass(frozen=True, slots=True)
class PurchaseAnalysisSummary:
    """Aggregate total and category distribution for a purchase selection."""

    total_value: Decimal
    distribution: dict[str, Decimal]


def _normalize_distribution(distribution: dict[str, Decimal]) -> dict[str, Decimal]:
    normalized: dict[str, Decimal] = {}
    for name, value in sorted(distribution.items(), key=lambda item: item[0].lower()):
        normalized[name] = value
    return normalized


def summarize_selected_purchases(
    selection: PurchaseAnalysisSelection,
    *,
    items: Iterable[PurchaseItem] = (),
    products: Iterable[Product] = (),
    categories: Iterable[Category] = (),
) -> PurchaseAnalysisSummary:
    """Summarize a vetted store-scoped purchase selection.

    The total is the sum of selected purchase totals. The category distribution
    is derived from the corresponding purchase items when product/category
    metadata is available; uncategorized items remain grouped under the explicit
    "Sem categoria" bucket.
    """
    if not isinstance(selection, PurchaseAnalysisSelection):
        raise TypeError("selection must be a PurchaseAnalysisSelection")

    total_value = sum((purchase.total_value for purchase in selection.purchases), Decimal("0"))

    selected_ids = {purchase.id for purchase in selection.purchases}
    item_tuple = tuple(items)
    product_by_code: dict[str, Product] = {}
    for product in products:
        if not isinstance(product, Product):
            raise TypeError("products must contain only Product instances")
        product_by_code[product.internal_code] = product

    category_by_id: dict[str, Category] = {}
    for category in categories:
        if not isinstance(category, Category):
            raise TypeError("categories must contain only Category instances")
        category_by_id[str(category.id)] = category

    distribution: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    seen_category_values = False

    for item in item_tuple:
        if not isinstance(item, PurchaseItem):
            raise TypeError("items must contain only PurchaseItem instances")
        if item.purchase_id not in selected_ids:
            continue

        product = product_by_code.get(item.internal_code)
        category_name = _DEFAULT_BUCKET
        if product is not None and product.category_id is not None:
            category = category_by_id.get(str(product.category_id))
            if category is not None:
                category_name = category.name
                seen_category_values = True
            else:
                category_name = _DEFAULT_BUCKET
        elif product is None:
            category_name = _DEFAULT_BUCKET

        distribution[category_name] += item.total_price

    if not distribution:
        distribution[_DEFAULT_BUCKET] = total_value
    elif not seen_category_values:
        distribution[_DEFAULT_BUCKET] = total_value
    else:
        uncategorized_total = sum(
            value for name, value in distribution.items() if name == _DEFAULT_BUCKET
        )
        if uncategorized_total == Decimal("0"):
            for name, value in distribution.items():
                if name == _DEFAULT_BUCKET:
                    distribution[name] = value
        # Keep any explicitly uncategorized values that were present.

    normalized = _normalize_distribution(dict(distribution))
    return PurchaseAnalysisSummary(total_value=total_value, distribution=normalized)


__all__ = [
    "PurchaseAnalysisSummary",
    "summarize_selected_purchases",
]
