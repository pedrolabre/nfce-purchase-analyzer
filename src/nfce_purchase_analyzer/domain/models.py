"""Pure Python domain models for stores, purchases, products, and categories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import uuid

from nfce_purchase_analyzer.deterministic import (
    quantize_money,
    quantize_quantity,
    uuid_from,
)

DecimalInput = Decimal | int | str
UuidInput = uuid.UUID | str

_ZERO = Decimal("0")


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _required_uuid(value: UuidInput, field_name: str) -> uuid.UUID:
    try:
        return uuid_from(value)
    except TypeError as exc:
        raise TypeError(f"{field_name} must be a UUID or UUID string") from exc
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid UUID") from exc


def _optional_uuid(value: UuidInput | None, field_name: str) -> uuid.UUID | None:
    if value is None:
        return None
    return _required_uuid(value, field_name)


def _required_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    return value


def _positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return value


def _money(value: DecimalInput, field_name: str) -> Decimal:
    try:
        amount = quantize_money(value)
    except TypeError as exc:
        raise TypeError(f"{field_name} must be a Decimal-compatible value") from exc
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a finite Decimal value") from exc

    if amount < _ZERO:
        raise ValueError(f"{field_name} must not be negative")
    return amount


def _quantity(value: DecimalInput, field_name: str) -> Decimal:
    try:
        quantity = quantize_quantity(value)
    except TypeError as exc:
        raise TypeError(f"{field_name} must be a Decimal-compatible value") from exc
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a finite Decimal value") from exc

    if quantity <= _ZERO:
        raise ValueError(f"{field_name} must be greater than zero")
    return quantity


class StoreBoundaryError(ValueError):
    """Raised when related domain objects belong to different stores."""


@dataclass(frozen=True, slots=True)
class ProductIdentity:
    store_id: uuid.UUID
    internal_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "store_id",
            _required_uuid(self.store_id, "store_id"),
        )
        object.__setattr__(
            self,
            "internal_code",
            _required_text(self.internal_code, "internal_code"),
        )


@dataclass(frozen=True, slots=True)
class Store:
    id: uuid.UUID
    code: str
    name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _required_uuid(self.id, "id"))
        object.__setattr__(self, "code", _required_text(self.code, "code"))
        object.__setattr__(self, "name", _required_text(self.name, "name"))


@dataclass(frozen=True, slots=True)
class Purchase:
    id: uuid.UUID
    store_id: uuid.UUID
    date: datetime
    total_value: Decimal
    total_items: int
    source_pdf: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _required_uuid(self.id, "id"))
        object.__setattr__(
            self,
            "store_id",
            _required_uuid(self.store_id, "store_id"),
        )
        object.__setattr__(self, "date", _required_datetime(self.date, "date"))
        object.__setattr__(
            self,
            "total_value",
            _money(self.total_value, "total_value"),
        )
        object.__setattr__(
            self,
            "total_items",
            _positive_int(self.total_items, "total_items"),
        )
        object.__setattr__(
            self,
            "source_pdf",
            _required_text(self.source_pdf, "source_pdf"),
        )


@dataclass(frozen=True, slots=True)
class PurchaseItem:
    purchase_id: uuid.UUID
    store_id: uuid.UUID
    internal_code: str
    raw_name: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "purchase_id",
            _required_uuid(self.purchase_id, "purchase_id"),
        )
        object.__setattr__(
            self,
            "store_id",
            _required_uuid(self.store_id, "store_id"),
        )
        object.__setattr__(
            self,
            "internal_code",
            _required_text(self.internal_code, "internal_code"),
        )
        object.__setattr__(self, "raw_name", _required_text(self.raw_name, "raw_name"))
        object.__setattr__(self, "quantity", _quantity(self.quantity, "quantity"))
        object.__setattr__(self, "unit_price", _money(self.unit_price, "unit_price"))
        object.__setattr__(
            self,
            "total_price",
            _money(self.total_price, "total_price"),
        )

    @property
    def product_identity(self) -> ProductIdentity:
        return ProductIdentity(self.store_id, self.internal_code)


@dataclass(frozen=True, slots=True)
class Product:
    store_id: uuid.UUID
    internal_code: str
    raw_name_sample: str
    category_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "store_id",
            _required_uuid(self.store_id, "store_id"),
        )
        object.__setattr__(
            self,
            "internal_code",
            _required_text(self.internal_code, "internal_code"),
        )
        object.__setattr__(
            self,
            "raw_name_sample",
            _required_text(self.raw_name_sample, "raw_name_sample"),
        )
        object.__setattr__(
            self,
            "category_id",
            _optional_uuid(self.category_id, "category_id"),
        )

    @property
    def identity(self) -> ProductIdentity:
        return ProductIdentity(self.store_id, self.internal_code)

    def has_same_identity_as(
        self,
        other: ProductIdentity | Product | PurchaseItem,
    ) -> bool:
        return self.identity == product_identity_from(other)


@dataclass(frozen=True, slots=True)
class Category:
    store_id: uuid.UUID
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "store_id",
            _required_uuid(self.store_id, "store_id"),
        )
        object.__setattr__(self, "id", _required_uuid(self.id, "id"))
        object.__setattr__(self, "name", _required_text(self.name, "name"))
        object.__setattr__(
            self,
            "parent_id",
            _optional_uuid(self.parent_id, "parent_id"),
        )


ProductIdentityInput = ProductIdentity | Product | PurchaseItem
StoreScoped = Store | Purchase | PurchaseItem | Product | Category | ProductIdentity


def product_identity_from(value: ProductIdentityInput) -> ProductIdentity:
    if isinstance(value, ProductIdentity):
        return value
    if isinstance(value, Product):
        return value.identity
    if isinstance(value, PurchaseItem):
        return value.product_identity
    raise TypeError("value must be a ProductIdentity, Product, or PurchaseItem")


def _store_id_for(value: StoreScoped) -> uuid.UUID:
    if isinstance(value, Store):
        return value.id
    if isinstance(value, (Purchase, PurchaseItem, Product, Category, ProductIdentity)):
        return value.store_id
    raise TypeError("value must be a store-scoped domain object")


def ensure_same_store(*values: StoreScoped) -> uuid.UUID:
    if not values:
        raise ValueError("at least one domain object is required")

    expected_store_id = _store_id_for(values[0])
    for value in values[1:]:
        current_store_id = _store_id_for(value)
        if current_store_id != expected_store_id:
            raise StoreBoundaryError(
                "related domain objects must belong to the same store"
            )

    return expected_store_id


__all__ = [
    "Category",
    "Product",
    "ProductIdentity",
    "Purchase",
    "PurchaseItem",
    "Store",
    "StoreBoundaryError",
    "ensure_same_store",
    "product_identity_from",
]
