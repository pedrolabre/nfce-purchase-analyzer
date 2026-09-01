"""Purchase repository for local JSON persistence."""

from __future__ import annotations

import uuid

from nfce_purchase_analyzer.deterministic import uuid_from
from nfce_purchase_analyzer.domain.models import (
    Purchase,
    PurchaseItem,
    StoreBoundaryError,
    ensure_same_store,
)
from nfce_purchase_analyzer.persistence.paths import StorageLayout
from nfce_purchase_analyzer.persistence.schemas import (
    dict_to_purchase,
    purchase_to_dict,
    read_json,
    write_json,
)


class PurchaseRepository:
    """Manages persistence of purchases with embedded items on local storage.

    Each purchase is stored as a single JSON file at the canonical path
    ``stores/<store_id>/purchases/<purchase_id>.json`` as determined by
    :meth:`StorageLayout.purchase_file`.

    Items are embedded inside the purchase document and are always
    saved and loaded together with their parent purchase.
    """

    def __init__(self, layout: StorageLayout) -> None:
        if not isinstance(layout, StorageLayout):
            raise TypeError("layout must be a StorageLayout")
        self._layout = layout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_purchase(
        self,
        purchase: Purchase,
        items: list[PurchaseItem],
    ) -> None:
        """Save a purchase with its items to local storage.

        Validates that:

        * The purchase and **all** items belong to the same ``store_id``
          (enforced via :func:`ensure_same_store`).
        * Every item references the correct ``purchase_id``.
        * The items list is not empty.

        The store directory structure is created automatically if it
        does not already exist.
        """
        if not items:
            raise ValueError("items must not be empty")

        # Validate store boundary: purchase + all items must share store_id.
        ensure_same_store(purchase, *items)

        # Validate purchase_id consistency.
        for item in items:
            if item.purchase_id != purchase.id:
                raise ValueError(
                    "all items must reference the purchase id"
                )

        # Ensure directory structure exists.
        self._layout.ensure_store_dirs(purchase.store_id)

        # Serialize and write.
        data = purchase_to_dict(purchase, items)
        write_json(
            self._layout.purchase_file(purchase.store_id, purchase.id),
            data,
        )

    def get_purchase(
        self,
        store_id: uuid.UUID | str,
        purchase_id: uuid.UUID | str,
    ) -> tuple[Purchase, list[PurchaseItem]] | None:
        """Load a purchase and its items by store and purchase ID.

        Returns a ``(Purchase, list[PurchaseItem])`` tuple, or ``None``
        if the purchase file does not exist.
        """
        sid = uuid_from(store_id)
        pid = uuid_from(purchase_id)
        path = self._layout.purchase_file(sid, pid)
        if not path.exists():
            return None
        data = read_json(path)
        return dict_to_purchase(data)

    def list_purchases(
        self,
        store_id: uuid.UUID | str,
    ) -> list[tuple[Purchase, list[PurchaseItem]]]:
        """List all purchases for a store, ordered by date descending.

        Returns an empty list if the store has no purchases or if the
        purchases directory does not exist.
        """
        sid = uuid_from(store_id)
        purchases_dir = self._layout.purchases_dir(sid)
        if not purchases_dir.exists():
            return []

        results: list[tuple[Purchase, list[PurchaseItem]]] = []
        for entry in sorted(purchases_dir.iterdir()):
            if entry.suffix == ".json" and entry.is_file():
                data = read_json(entry)
                results.append(dict_to_purchase(data))

        # Sort by date descending.
        results.sort(key=lambda pair: pair[0].date, reverse=True)
        return results

    def count_purchases(
        self,
        store_id: uuid.UUID | str,
    ) -> int:
        """Count the number of purchases for a store.

        Returns ``0`` if the purchases directory does not exist.
        Does not deserialize any files.
        """
        sid = uuid_from(store_id)
        purchases_dir = self._layout.purchases_dir(sid)
        if not purchases_dir.exists():
            return 0

        return sum(
            1
            for entry in purchases_dir.iterdir()
            if entry.suffix == ".json" and entry.is_file()
        )


__all__ = [
    "PurchaseRepository",
]
