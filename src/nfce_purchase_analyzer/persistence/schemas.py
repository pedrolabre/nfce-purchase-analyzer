"""Canonical JSON schemas for domain model serialization."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
import uuid

from nfce_purchase_analyzer.deterministic import (
    decimal_from,
    decimal_to_string,
    uuid_from,
    uuid_to_string,
)
from nfce_purchase_analyzer.domain.models import (
    Category,
    Product,
    Purchase,
    PurchaseItem,
    Store,
)


# ------------------------------------------------------------------
# JSON file I/O
# ------------------------------------------------------------------


def write_json(path: Path, data: Any) -> None:
    """Write *data* as deterministic JSON to *path*.

    The output uses sorted keys, 2-space indentation, UTF-8 encoding,
    and a trailing newline.
    """
    content = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    path.write_text(content + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    """Read and parse a JSON file encoded as UTF-8."""
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------
# Datetime helpers
# ------------------------------------------------------------------


def _datetime_to_string(value: datetime) -> str:
    """Serialize a datetime to ISO 8601 format."""
    return value.isoformat()


def _string_to_datetime(value: str) -> datetime:
    """Deserialize an ISO 8601 string to a datetime."""
    return datetime.fromisoformat(value)


# ------------------------------------------------------------------
# Optional UUID helper
# ------------------------------------------------------------------


def _optional_uuid_to_string(value: uuid.UUID | None) -> str | None:
    """Serialize an optional UUID to its canonical string or None."""
    if value is None:
        return None
    return uuid_to_string(value)


def _optional_string_to_uuid(value: str | None) -> uuid.UUID | None:
    """Deserialize an optional string to UUID or None."""
    if value is None:
        return None
    return uuid_from(value)


# ------------------------------------------------------------------
# Store
# ------------------------------------------------------------------


def store_to_dict(store: Store) -> dict[str, Any]:
    """Serialize a Store to a JSON-safe dict."""
    return {
        "id": uuid_to_string(store.id),
        "code": store.code,
        "name": store.name,
    }


def dict_to_store(data: dict[str, Any]) -> Store:
    """Deserialize a dict to a Store."""
    return Store(
        id=uuid_from(data["id"]),
        code=data["code"],
        name=data["name"],
    )


# ------------------------------------------------------------------
# PurchaseItem
# ------------------------------------------------------------------


def purchase_item_to_dict(item: PurchaseItem) -> dict[str, Any]:
    """Serialize a PurchaseItem to a JSON-safe dict."""
    return {
        "purchase_id": uuid_to_string(item.purchase_id),
        "store_id": uuid_to_string(item.store_id),
        "internal_code": item.internal_code,
        "raw_name": item.raw_name,
        "quantity": decimal_to_string(item.quantity),
        "unit_price": decimal_to_string(item.unit_price),
        "total_price": decimal_to_string(item.total_price),
    }


def dict_to_purchase_item(
    data: dict[str, Any],
    purchase_id: uuid.UUID | str,
) -> PurchaseItem:
    """Deserialize a dict to a PurchaseItem.

    The *purchase_id* is passed explicitly because items may be stored
    embedded inside a purchase document.
    """
    return PurchaseItem(
        purchase_id=uuid_from(purchase_id),
        store_id=uuid_from(data["store_id"]),
        internal_code=data["internal_code"],
        raw_name=data["raw_name"],
        quantity=decimal_from(data["quantity"]),
        unit_price=decimal_from(data["unit_price"]),
        total_price=decimal_from(data["total_price"]),
    )


# ------------------------------------------------------------------
# Purchase (with embedded items)
# ------------------------------------------------------------------


def purchase_to_dict(
    purchase: Purchase,
    items: list[PurchaseItem],
) -> dict[str, Any]:
    """Serialize a Purchase and its items to a JSON-safe dict.

    Items are embedded in the purchase document under the ``"items"`` key.
    """
    return {
        "id": uuid_to_string(purchase.id),
        "store_id": uuid_to_string(purchase.store_id),
        "date": _datetime_to_string(purchase.date),
        "total_value": decimal_to_string(purchase.total_value),
        "total_items": purchase.total_items,
        "source_pdf": purchase.source_pdf,
        "items": [purchase_item_to_dict(item) for item in items],
    }


def dict_to_purchase(
    data: dict[str, Any],
) -> tuple[Purchase, list[PurchaseItem]]:
    """Deserialize a dict to a Purchase and its embedded items."""
    purchase_id = uuid_from(data["id"])
    purchase = Purchase(
        id=purchase_id,
        store_id=uuid_from(data["store_id"]),
        date=_string_to_datetime(data["date"]),
        total_value=decimal_from(data["total_value"]),
        total_items=data["total_items"],
        source_pdf=data["source_pdf"],
    )
    items = [
        dict_to_purchase_item(item_data, purchase_id)
        for item_data in data.get("items", [])
    ]
    return purchase, items


# ------------------------------------------------------------------
# Product
# ------------------------------------------------------------------


def product_to_dict(product: Product) -> dict[str, Any]:
    """Serialize a Product to a JSON-safe dict."""
    return {
        "store_id": uuid_to_string(product.store_id),
        "internal_code": product.internal_code,
        "raw_name_sample": product.raw_name_sample,
        "category_id": _optional_uuid_to_string(product.category_id),
    }


def dict_to_product(data: dict[str, Any]) -> Product:
    """Deserialize a dict to a Product."""
    return Product(
        store_id=uuid_from(data["store_id"]),
        internal_code=data["internal_code"],
        raw_name_sample=data["raw_name_sample"],
        category_id=_optional_string_to_uuid(data.get("category_id")),
    )


# ------------------------------------------------------------------
# Category
# ------------------------------------------------------------------


def category_to_dict(category: Category) -> dict[str, Any]:
    """Serialize a Category to a JSON-safe dict."""
    return {
        "store_id": uuid_to_string(category.store_id),
        "id": uuid_to_string(category.id),
        "name": category.name,
        "parent_id": _optional_uuid_to_string(category.parent_id),
    }


def dict_to_category(data: dict[str, Any]) -> Category:
    """Deserialize a dict to a Category."""
    return Category(
        store_id=uuid_from(data["store_id"]),
        id=uuid_from(data["id"]),
        name=data["name"],
        parent_id=_optional_string_to_uuid(data.get("parent_id")),
    )


__all__ = [
    "category_to_dict",
    "dict_to_category",
    "dict_to_product",
    "dict_to_purchase",
    "dict_to_purchase_item",
    "dict_to_store",
    "product_to_dict",
    "purchase_item_to_dict",
    "purchase_to_dict",
    "read_json",
    "store_to_dict",
    "write_json",
]
