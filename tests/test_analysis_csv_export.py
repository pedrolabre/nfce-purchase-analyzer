"""Tests for CSV export of analytical results."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime

from nfce_purchase_analyzer.analysis import (
    calculate_historical_price_variation,
    export_analysis_summary_csv,
    export_historical_price_variation_csv,
    summarize_selected_purchases,
)
from nfce_purchase_analyzer.analysis.selection import select_purchases_for_analysis
from nfce_purchase_analyzer.domain.models import Category, Product, Purchase, PurchaseItem

STORE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


def _purchase(*, purchase_id: uuid.UUID | None = None, total_value: str, date: datetime) -> Purchase:
    return Purchase(
        id=purchase_id or uuid.uuid4(),
        store_id=STORE_ID,
        date=date,
        total_value=total_value,
        total_items=2,
        source_pdf="nota_001.pdf",
    )


def _item(
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


def _read_csv(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


class TestAnalysisCsvExport:
    def test_exports_summary_as_csv_rows(self) -> None:
        purchase_1 = _purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000001"),
            total_value="39.90",
            date=datetime(2026, 1, 5, 10, 0, 0),
        )
        purchase_2 = _purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000002"),
            total_value="49.80",
            date=datetime(2026, 1, 12, 10, 0, 0),
        )
        selection = select_purchases_for_analysis([purchase_1, purchase_2])

        category_id = uuid.UUID("20000000-0000-4000-8000-000000000001")
        items = (
            _item(
                purchase_id=purchase_1.id,
                internal_code="001",
                raw_name="Arroz 5kg",
                quantity="1.000",
                unit_price="19.90",
                total_price="19.90",
            ),
            _item(
                purchase_id=purchase_1.id,
                internal_code="002",
                raw_name="Feijao 1kg",
                quantity="1.000",
                unit_price="20.00",
                total_price="20.00",
            ),
            _item(
                purchase_id=purchase_2.id,
                internal_code="003",
                raw_name="Sabao",
                quantity="1.000",
                unit_price="49.80",
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
            ),
            Product(
                store_id=STORE_ID,
                internal_code="003",
                raw_name_sample="Sabao",
                category_id=category_id,
            ),
        )
        categories = (
            Category(store_id=STORE_ID, id=category_id, name="Alimentos"),
        )

        summary = summarize_selected_purchases(
            selection,
            items=items,
            products=products,
            categories=categories,
        )

        rows = _read_csv(export_analysis_summary_csv(summary))

        assert rows == [
            {"metric": "total_value", "category": "", "value": "89.70"},
            {"metric": "category_distribution", "category": "Alimentos", "value": "69.70"},
            {"metric": "category_distribution", "category": "Sem categoria", "value": "20.00"},
        ]

    def test_exports_historical_variation_as_csv_rows(self) -> None:
        purchase_1 = _purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000003"),
            total_value="15.90",
            date=datetime(2026, 1, 5, 10, 0, 0),
        )
        purchase_2 = _purchase(
            purchase_id=uuid.UUID("10000000-0000-4000-8000-000000000004"),
            total_value="18.40",
            date=datetime(2026, 1, 12, 10, 0, 0),
        )
        selection = select_purchases_for_analysis([purchase_1, purchase_2])

        category_id = uuid.UUID("20000000-0000-4000-8000-000000000002")
        product = Product(
            store_id=STORE_ID,
            internal_code="001",
            raw_name_sample="Arroz 5kg",
            category_id=category_id,
        )
        category = Category(store_id=STORE_ID, id=category_id, name="Alimentos")
        items = (
            _item(
                purchase_id=purchase_1.id,
                internal_code="001",
                raw_name="Arroz 5kg",
                quantity="1.000",
                unit_price="7.95",
                total_price="7.95",
            ),
            _item(
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

        rows = _read_csv(export_historical_price_variation_csv(result))

        assert rows == [
            {
                "product_internal_code": "001",
                "product_name": "Arroz 5kg",
                "category_name": "Alimentos",
                "previous_purchase_date": "2026-01-05T10:00:00",
                "current_purchase_date": "2026-01-12T10:00:00",
                "previous_unit_price": "7.95",
                "current_unit_price": "9.20",
                "absolute_variation": "1.25",
                "percentage_variation": "15.72",
            }
        ]