"""Tests for historical price variation within a store."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from nfce_purchase_analyzer.analysis import (
    MixedStoreSelectionError,
    calculate_historical_price_variation,
    select_purchases_for_analysis,
)
from nfce_purchase_analyzer.domain.models import Category, Product, Purchase, PurchaseItem

STORE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
OTHER_STORE_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")


def _make_purchase(
    *,
    purchase_id: uuid.UUID | None = None,
    store_id: uuid.UUID = STORE_ID,
    date: datetime,
    total_value: str,
) -> Purchase:
    return Purchase(
        id=purchase_id or uuid.uuid4(),
        store_id=store_id,
        date=date,
        total_value=total_value,
        total_items=2,
        source_pdf="nota.pdf",
    )


def _make_item(
    *,
    purchase_id: uuid.UUID,
    internal_code: str,
    raw_name: str,
    quantity: str,
    unit_price: str,
    total_price: str,
) -> PurchaseItem:
    return PurchaseItem(
        purchase_id=purchase_id,
        store_id=STORE_ID,
        internal_code=internal_code,
        raw_name=raw_name,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
    )


class TestHistoricalPriceVariation:
    def test_calculates_consecutive_price_change_for_same_product(self) -> None:
        purchase_1 = _make_purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000001"),
            date=datetime(2026, 1, 5, 10, 0, 0),
            total_value="15.90",
        )
        purchase_2 = _make_purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000002"),
            date=datetime(2026, 1, 12, 10, 0, 0),
            total_value="18.40",
        )
        selection = select_purchases_for_analysis([purchase_1, purchase_2])

        product = Product(
            store_id=STORE_ID,
            internal_code="001",
            raw_name_sample="Arroz 5kg",
            category_id=uuid.UUID("20000000-0000-4000-8000-000000000001"),
        )
        category = Category(
            store_id=STORE_ID,
            id=product.category_id,
            name="Alimentos",
        )
        items = (
            _make_item(
                purchase_id=purchase_1.id,
                internal_code="001",
                raw_name="Arroz 5kg",
                quantity="1.000",
                unit_price="7.95",
                total_price="7.95",
            ),
            _make_item(
                purchase_id=purchase_2.id,
                internal_code="001",
                raw_name="Arroz 5kg",
                quantity="1.000",
                unit_price="9.20",
                total_price="9.20",
            ),
        )

        result = calculate_historical_price_variation(
            selection,
            items=items,
            products=(product,),
            categories=(category,),
        )

        entry = result.by_product["001"][0]
        assert entry.category_name == "Alimentos"
        assert entry.previous_unit_price == Decimal("7.95")
        assert entry.current_unit_price == Decimal("9.20")
        assert entry.absolute_variation == Decimal("1.25")
        assert entry.percentage_variation == Decimal("15.72")
        assert result.by_category["Alimentos"][0].product_internal_code == "001"

    def test_keeps_zero_variation_when_price_is_stable(self) -> None:
        purchase_1 = _make_purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000003"),
            date=datetime(2026, 1, 5, 10, 0, 0),
            total_value="10.00",
        )
        purchase_2 = _make_purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000004"),
            date=datetime(2026, 1, 12, 10, 0, 0),
            total_value="10.00",
        )
        selection = select_purchases_for_analysis([purchase_1, purchase_2])

        product = Product(
            store_id=STORE_ID,
            internal_code="002",
            raw_name_sample="Leite 1L",
        )
        items = (
            _make_item(
                purchase_id=purchase_1.id,
                internal_code="002",
                raw_name="Leite 1L",
                quantity="1.000",
                unit_price="5.00",
                total_price="5.00",
            ),
            _make_item(
                purchase_id=purchase_2.id,
                internal_code="002",
                raw_name="Leite 1L",
                quantity="1.000",
                unit_price="5.00",
                total_price="5.00",
            ),
        )

        result = calculate_historical_price_variation(selection, items=items, products=(product,))

        entry = result.by_product["002"][0]
        assert entry.absolute_variation == Decimal("0")
        assert entry.percentage_variation == Decimal("0")

    def test_keeps_missing_history_as_zero_without_blocking_rest(self) -> None:
        purchase_1 = _make_purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000005"),
            date=datetime(2026, 1, 5, 10, 0, 0),
            total_value="7.90",
        )
        purchase_2 = _make_purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000006"),
            date=datetime(2026, 1, 12, 10, 0, 0),
            total_value="14.90",
        )
        selection = select_purchases_for_analysis([purchase_1, purchase_2])

        product_with_history = Product(
            store_id=STORE_ID,
            internal_code="003",
            raw_name_sample="Cafe 250g",
        )
        product_without_history = Product(
            store_id=STORE_ID,
            internal_code="004",
            raw_name_sample="Biscoito",
        )
        items = (
            _make_item(
                purchase_id=purchase_1.id,
                internal_code="003",
                raw_name="Cafe 250g",
                quantity="1.000",
                unit_price="3.95",
                total_price="3.95",
            ),
            _make_item(
                purchase_id=purchase_2.id,
                internal_code="003",
                raw_name="Cafe 250g",
                quantity="1.000",
                unit_price="7.45",
                total_price="7.45",
            ),
            _make_item(
                purchase_id=purchase_2.id,
                internal_code="004",
                raw_name="Biscoito",
                quantity="1.000",
                unit_price="4.90",
                total_price="4.90",
            ),
        )

        result = calculate_historical_price_variation(
            selection,
            items=items,
            products=(product_with_history, product_without_history),
        )

        assert result.by_product["003"][0].absolute_variation == Decimal("3.50")
        assert result.by_product["004"][0].absolute_variation == Decimal("0")
        assert result.by_product["004"][0].percentage_variation == Decimal("0")

    def test_rejects_mixed_stores_even_for_historical_variation(self) -> None:
        purchase_1 = _make_purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000007"),
            store_id=STORE_ID,
            date=datetime(2026, 1, 5, 10, 0, 0),
            total_value="7.90",
        )
        purchase_2 = _make_purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000008"),
            store_id=OTHER_STORE_ID,
            date=datetime(2026, 1, 12, 10, 0, 0),
            total_value="8.90",
        )

        with pytest.raises(MixedStoreSelectionError):
            select_purchases_for_analysis([purchase_1, purchase_2])
