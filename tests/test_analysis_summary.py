"""Tests for accumulated totals and category distribution."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from nfce_purchase_analyzer.analysis import (
    summarize_selected_purchases,
)
from nfce_purchase_analyzer.analysis.selection import select_purchases_for_analysis
from nfce_purchase_analyzer.domain.models import (
    Category,
    Product,
    Purchase,
    PurchaseItem,
)

STORE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


def _purchase(*, purchase_id: uuid.UUID | None = None, total_value: str) -> Purchase:
    return Purchase(
        id=purchase_id or uuid.uuid4(),
        store_id=STORE_ID,
        date=datetime(2026, 1, 15, 10, 30, 0),
        total_value=total_value,
        total_items=2,
        source_pdf="nota_001.pdf",
    )


def _item(
    *,
    purchase_id: uuid.UUID,
    internal_code: str,
    raw_name: str,
    total_price: str,
) -> PurchaseItem:
    return PurchaseItem(
        purchase_id=purchase_id,
        store_id=STORE_ID,
        internal_code=internal_code,
        raw_name=raw_name,
        quantity="1.000",
        unit_price=total_price,
        total_price=total_price,
    )


class TestSummarizeSelectedPurchases:
    def test_total_accumulated_sums_selected_purchases(self) -> None:
        p1 = _purchase(total_value="39.90")
        p2 = _purchase(purchase_id=uuid.uuid4(), total_value="49.80")

        selection = select_purchases_for_analysis([p1, p2])

        summary = summarize_selected_purchases(selection, items=())

        assert summary.total_value == Decimal("89.70")
        assert summary.distribution == {"Sem categoria": Decimal("89.70")}

    def test_distribution_by_category_groups_uncategorized_items(self) -> None:
        p1 = _purchase(total_value="39.90")
        p2 = _purchase(purchase_id=uuid.uuid4(), total_value="49.80")
        selection = select_purchases_for_analysis([p1, p2])

        category_id = uuid.uuid4()
        items = (
            _item(
                purchase_id=p1.id,
                internal_code="001",
                raw_name="Arroz 5kg",
                total_price="19.90",
            ),
            _item(
                purchase_id=p1.id,
                internal_code="002",
                raw_name="Feijao 1kg",
                total_price="20.00",
            ),
            _item(
                purchase_id=p2.id,
                internal_code="003",
                raw_name="Sabao",
                total_price="49.80",
            ),
        )
        products = (
            Product(
                store_id=STORE_ID,
                internal_code="001",
                raw_name_sample="Arroz 5kg",
                category_id=category_id,
            ),
            Product(
                store_id=STORE_ID,
                internal_code="002",
                raw_name_sample="Feijao 1kg",
                category_id=None,
            ),
            Product(
                store_id=STORE_ID,
                internal_code="003",
                raw_name_sample="Sabao",
                category_id=category_id,
            ),
        )
        categories = (
            Category(
                store_id=STORE_ID,
                id=category_id,
                name="Alimentos",
            ),
        )

        summary = summarize_selected_purchases(
            selection,
            items=items,
            products=products,
            categories=categories,
        )

        assert summary.total_value == Decimal("89.70")
        assert summary.distribution == {
            "Alimentos": Decimal("69.70"),
            "Sem categoria": Decimal("20.00"),
        }
