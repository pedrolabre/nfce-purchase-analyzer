from datetime import datetime
from decimal import Decimal
import uuid

import pytest

from nfce_purchase_analyzer.domain import (
    Category,
    Product,
    Purchase,
    PurchaseItem,
    Store,
)

STORE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PURCHASE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
CATEGORY_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
PARENT_CATEGORY_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def test_store_normalizes_uuid_and_required_text() -> None:
    store = Store(
        id=str(STORE_ID).upper(),
        code=" 0001 ",
        name=" Bem Maior ",
    )

    assert store.id == STORE_ID
    assert store.code == "0001"
    assert store.name == "Bem Maior"


def test_purchase_normalizes_values() -> None:
    purchased_at = datetime(2026, 8, 13, 10, 30)

    purchase = Purchase(
        id=PURCHASE_ID,
        store_id=str(STORE_ID),
        date=purchased_at,
        total_value=Decimal("123.456"),
        total_items=3,
        source_pdf=" notas/compra.pdf ",
    )

    assert purchase.id == PURCHASE_ID
    assert purchase.store_id == STORE_ID
    assert purchase.date == purchased_at
    assert purchase.total_value == Decimal("123.46")
    assert purchase.total_items == 3
    assert purchase.source_pdf == "notas/compra.pdf"


def test_purchase_item_normalizes_values() -> None:
    item = PurchaseItem(
        purchase_id=str(PURCHASE_ID),
        store_id=STORE_ID,
        internal_code=" 7891000100103 ",
        raw_name=" Arroz Branco 5kg ",
        quantity=Decimal("0.3456"),
        unit_price=Decimal("10.125"),
        total_price=Decimal("3.494"),
    )

    assert item.purchase_id == PURCHASE_ID
    assert item.store_id == STORE_ID
    assert item.internal_code == "7891000100103"
    assert item.raw_name == "Arroz Branco 5kg"
    assert item.quantity == Decimal("0.346")
    assert item.unit_price == Decimal("10.13")
    assert item.total_price == Decimal("3.49")


def test_product_allows_optional_category() -> None:
    product = Product(
        store_id=STORE_ID,
        internal_code=" 123 ",
        raw_name_sample=" Banana KG ",
        category_id=str(CATEGORY_ID),
    )
    uncategorized = Product(
        store_id=STORE_ID,
        internal_code="124",
        raw_name_sample="Maca KG",
    )

    assert product.store_id == STORE_ID
    assert product.internal_code == "123"
    assert product.raw_name_sample == "Banana KG"
    assert product.category_id == CATEGORY_ID
    assert uncategorized.category_id is None


def test_category_allows_optional_parent() -> None:
    category = Category(
        store_id=str(STORE_ID),
        id=CATEGORY_ID,
        name=" Hortifruti ",
        parent_id=str(PARENT_CATEGORY_ID),
    )
    root = Category(store_id=STORE_ID, id=PARENT_CATEGORY_ID, name="Mercado")

    assert category.store_id == STORE_ID
    assert category.id == CATEGORY_ID
    assert category.name == "Hortifruti"
    assert category.parent_id == PARENT_CATEGORY_ID
    assert root.parent_id is None


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Store(id=STORE_ID, code=" ", name="Bem Maior"),
        lambda: Store(id=STORE_ID, code="0001", name=" "),
        lambda: Purchase(
            id=PURCHASE_ID,
            store_id=STORE_ID,
            date=datetime(2026, 8, 13),
            total_value=Decimal("1.00"),
            total_items=1,
            source_pdf=" ",
        ),
        lambda: PurchaseItem(
            purchase_id=PURCHASE_ID,
            store_id=STORE_ID,
            internal_code=" ",
            raw_name="Arroz",
            quantity=Decimal("1"),
            unit_price=Decimal("1.00"),
            total_price=Decimal("1.00"),
        ),
        lambda: PurchaseItem(
            purchase_id=PURCHASE_ID,
            store_id=STORE_ID,
            internal_code="123",
            raw_name=" ",
            quantity=Decimal("1"),
            unit_price=Decimal("1.00"),
            total_price=Decimal("1.00"),
        ),
        lambda: Product(store_id=STORE_ID, internal_code=" ", raw_name_sample="Arroz"),
        lambda: Product(store_id=STORE_ID, internal_code="123", raw_name_sample=" "),
        lambda: Category(store_id=STORE_ID, id=CATEGORY_ID, name=" "),
    ],
)
def test_models_reject_empty_required_text(factory) -> None:
    with pytest.raises(ValueError):
        factory()


def test_models_reject_invalid_uuid_values() -> None:
    with pytest.raises(ValueError):
        Store(id="not-a-uuid", code="0001", name="Bem Maior")

    with pytest.raises(ValueError):
        Product(
            store_id=STORE_ID,
            internal_code="123",
            raw_name_sample="Arroz",
            category_id="not-a-uuid",
        )

    with pytest.raises(TypeError):
        Category(store_id=123, id=CATEGORY_ID, name="Mercado")


def test_purchase_rejects_invalid_date_and_total_items() -> None:
    with pytest.raises(TypeError):
        Purchase(
            id=PURCHASE_ID,
            store_id=STORE_ID,
            date="2026-08-13",
            total_value=Decimal("1.00"),
            total_items=1,
            source_pdf="compra.pdf",
        )

    with pytest.raises(ValueError):
        Purchase(
            id=PURCHASE_ID,
            store_id=STORE_ID,
            date=datetime(2026, 8, 13),
            total_value=Decimal("1.00"),
            total_items=0,
            source_pdf="compra.pdf",
        )

    with pytest.raises(TypeError):
        Purchase(
            id=PURCHASE_ID,
            store_id=STORE_ID,
            date=datetime(2026, 8, 13),
            total_value=Decimal("1.00"),
            total_items=True,
            source_pdf="compra.pdf",
        )


def test_models_reject_float_decimal_inputs() -> None:
    with pytest.raises(TypeError):
        Purchase(
            id=PURCHASE_ID,
            store_id=STORE_ID,
            date=datetime(2026, 8, 13),
            total_value=1.0,
            total_items=1,
            source_pdf="compra.pdf",
        )

    with pytest.raises(TypeError):
        PurchaseItem(
            purchase_id=PURCHASE_ID,
            store_id=STORE_ID,
            internal_code="123",
            raw_name="Arroz",
            quantity=1.0,
            unit_price=Decimal("1.00"),
            total_price=Decimal("1.00"),
        )


def test_models_reject_invalid_decimal_ranges() -> None:
    with pytest.raises(ValueError):
        Purchase(
            id=PURCHASE_ID,
            store_id=STORE_ID,
            date=datetime(2026, 8, 13),
            total_value=Decimal("-0.01"),
            total_items=1,
            source_pdf="compra.pdf",
        )

    with pytest.raises(ValueError):
        PurchaseItem(
            purchase_id=PURCHASE_ID,
            store_id=STORE_ID,
            internal_code="123",
            raw_name="Arroz",
            quantity=Decimal("0"),
            unit_price=Decimal("1.00"),
            total_price=Decimal("1.00"),
        )

    with pytest.raises(ValueError):
        PurchaseItem(
            purchase_id=PURCHASE_ID,
            store_id=STORE_ID,
            internal_code="123",
            raw_name="Arroz",
            quantity=Decimal("1"),
            unit_price=Decimal("-0.01"),
            total_price=Decimal("1.00"),
        )

    with pytest.raises(ValueError):
        PurchaseItem(
            purchase_id=PURCHASE_ID,
            store_id=STORE_ID,
            internal_code="123",
            raw_name="Arroz",
            quantity=Decimal("1"),
            unit_price=Decimal("1.00"),
            total_price=Decimal("-0.01"),
        )
