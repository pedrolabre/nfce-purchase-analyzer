"""Import confirmation service for the NFC-e analyzer.

This module connects the in-memory parsed result
(:class:`PendingPurchaseImport`) to the local persistence layer.

The key invariant is that **preview generation never touches disk**.
Data is persisted only when the caller explicitly invokes
:func:`confirm_import`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from nfce_purchase_analyzer.domain.models import (
    PendingPurchaseImport,
    Product,
    Purchase,
    PurchaseItem,
)
from nfce_purchase_analyzer.persistence.paths import StorageLayout
from nfce_purchase_analyzer.persistence.products import ProductRepository
from nfce_purchase_analyzer.persistence.purchases import PurchaseRepository


class DuplicateImportError(ValueError):
    """Raised when an import would duplicate an existing purchase."""


@dataclass(frozen=True, slots=True)
class ImportResult:
    """Result of a successful import confirmation.

    Attributes:
        purchase: The persisted :class:`Purchase`.
        items: The persisted :class:`PurchaseItem` list.
        products: The product catalog snapshot for the store after the
            implicit upsert triggered by the import.
    """

    purchase: Purchase
    items: tuple[PurchaseItem, ...]
    products: tuple[Product, ...]


def confirm_import(
    pending: PendingPurchaseImport,
    layout: StorageLayout,
) -> ImportResult:
    """Persist a pending import after explicit user confirmation.

    This is the **only** entry point that transitions data from the
    in-memory preview state to durable local storage.

    The function orchestrates:

    1. Duplicate detection — rejects re-importing a purchase with the
       same ``source_pdf`` in the same store.
    2. ID generation — creates a fresh UUID for the purchase and binds
       every pending item to it, producing confirmed
       :class:`Purchase` and :class:`PurchaseItem` instances.
    3. Purchase persistence — delegates to
       :meth:`PurchaseRepository.save_purchase`.
    4. Implicit product upsert — delegates to
       :meth:`ProductRepository.upsert_from_items`.

    Parameters:
        pending: A validated :class:`PendingPurchaseImport` produced by
            the parsing pipeline.
        layout: The :class:`StorageLayout` that determines where data is
            written.

    Returns:
        An :class:`ImportResult` containing the persisted purchase,
        items and the updated product catalog snapshot.

    Raises:
        TypeError: If *pending* is not a :class:`PendingPurchaseImport`
            or *layout* is not a :class:`StorageLayout`.
        DuplicateImportError: If a purchase with the same
            ``source_pdf`` already exists for the store.
    """
    if not isinstance(pending, PendingPurchaseImport):
        raise TypeError("pending must be a PendingPurchaseImport")
    if not isinstance(layout, StorageLayout):
        raise TypeError("layout must be a StorageLayout")

    # ------------------------------------------------------------------
    # 1. Duplicate detection
    # ------------------------------------------------------------------
    purchase_repo = PurchaseRepository(layout)
    existing = purchase_repo.list_purchases(pending.store_id)
    for existing_purchase, _existing_items in existing:
        if existing_purchase.source_pdf == pending.source_pdf:
            raise DuplicateImportError(
                f"a purchase from '{pending.source_pdf}' already exists "
                f"for this store"
            )

    # ------------------------------------------------------------------
    # 2. ID generation — create confirmed domain objects
    # ------------------------------------------------------------------
    purchase_id = uuid.uuid4()

    purchase = Purchase(
        id=purchase_id,
        store_id=pending.store_id,
        date=pending.date,
        total_value=pending.total_value,
        total_items=pending.total_items,
        source_pdf=pending.source_pdf,
    )

    items: list[PurchaseItem] = []
    for pending_item in pending.items:
        item = PurchaseItem(
            purchase_id=purchase_id,
            store_id=pending_item.store_id,
            internal_code=pending_item.internal_code,
            raw_name=pending_item.raw_name,
            quantity=pending_item.quantity,
            unit_price=pending_item.unit_price,
            total_price=pending_item.total_price,
        )
        items.append(item)

    # ------------------------------------------------------------------
    # 3. Persist purchase + items
    # ------------------------------------------------------------------
    purchase_repo.save_purchase(purchase, items)

    # ------------------------------------------------------------------
    # 4. Implicit product upsert
    # ------------------------------------------------------------------
    product_repo = ProductRepository(layout)
    products = product_repo.upsert_from_items(pending.store_id, items)

    return ImportResult(
        purchase=purchase,
        items=tuple(items),
        products=tuple(products),
    )


__all__ = [
    "DuplicateImportError",
    "ImportResult",
    "confirm_import",
]
