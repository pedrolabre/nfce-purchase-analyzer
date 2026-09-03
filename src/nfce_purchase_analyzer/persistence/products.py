"""Product repository for local JSON persistence."""

from __future__ import annotations

import uuid

from nfce_purchase_analyzer.deterministic import uuid_from
from nfce_purchase_analyzer.domain.models import (
    Product,
    PurchaseItem,
    StoreBoundaryError,
    ensure_same_store,
)
from nfce_purchase_analyzer.persistence.paths import StorageLayout
from nfce_purchase_analyzer.persistence.schemas import (
    dict_to_product,
    product_to_dict,
    read_json,
    write_json,
)


class ProductRepository:
    """Manages persistence of products per store on local storage.

    Products are stored in a single JSON file per store at the canonical
    path ``stores/<store_id>/products.json`` as determined by
    :meth:`StorageLayout.products_file`.

    Products are identified strictly by ``(store_id, internal_code)``.
    Products from different stores are never mixed or merged.
    """

    def __init__(self, layout: StorageLayout) -> None:
        if not isinstance(layout, StorageLayout):
            raise TypeError("layout must be a StorageLayout")
        self._layout = layout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_products(self, store_id: uuid.UUID) -> list[dict]:
        """Read the products file, returning an empty list if absent."""
        path = self._layout.products_file(store_id)
        if not path.exists():
            return []
        return read_json(path)

    def _write_products(
        self,
        store_id: uuid.UUID,
        entries: list[dict],
    ) -> None:
        """Write the products file with deterministic ordering."""
        # Sort by internal_code for deterministic output.
        entries.sort(key=lambda e: e["internal_code"])
        write_json(self._layout.products_file(store_id), entries)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_product(
        self,
        store_id: uuid.UUID | str,
        internal_code: str,
    ) -> Product | None:
        """Find a product by store ID and internal code.

        Returns ``None`` if the product does not exist.
        """
        sid = uuid_from(store_id)
        for entry in self._read_products(sid):
            if entry["internal_code"] == internal_code:
                return dict_to_product(entry)
        return None

    def list_products(
        self,
        store_id: uuid.UUID | str,
    ) -> list[Product]:
        """Return all products for a store, ordered by internal_code."""
        sid = uuid_from(store_id)
        entries = self._read_products(sid)
        products = [dict_to_product(entry) for entry in entries]
        products.sort(key=lambda p: p.internal_code)
        return products

    def count_products(
        self,
        store_id: uuid.UUID | str,
    ) -> int:
        """Count the number of products for a store.

        Returns ``0`` if the products file does not exist.
        """
        sid = uuid_from(store_id)
        return len(self._read_products(sid))

    def upsert_product(
        self,
        product: Product,
    ) -> Product:
        """Insert or update a single product.

        If a product with the same ``(store_id, internal_code)`` already
        exists, its ``raw_name_sample`` is updated to the new value and
        the existing ``category_id`` is preserved.

        If the product is new, it is inserted as-is.

        Returns the product as stored after the operation.
        """
        sid = product.store_id
        entries = self._read_products(sid)

        found = False
        stored_product = product
        for i, entry in enumerate(entries):
            if entry["internal_code"] == product.internal_code:
                # Update: keep existing category_id, update raw_name_sample.
                existing = dict_to_product(entry)
                stored_product = Product(
                    store_id=product.store_id,
                    internal_code=product.internal_code,
                    raw_name_sample=product.raw_name_sample,
                    category_id=existing.category_id,
                )
                entries[i] = product_to_dict(stored_product)
                found = True
                break

        if not found:
            stored_product = product
            entries.append(product_to_dict(product))

        # Ensure store directories exist before writing.
        self._layout.ensure_store_dirs(sid)
        self._write_products(sid, entries)
        return stored_product

    def upsert_from_items(
        self,
        store_id: uuid.UUID | str,
        items: list[PurchaseItem],
    ) -> list[Product]:
        """Implicitly register or update products from purchase items.

        For each item:

        * If the product is new, it is created with
          ``raw_name_sample = item.raw_name`` and ``category_id = None``.
        * If the product already exists, ``raw_name_sample`` is updated
          to the item's ``raw_name`` (the most recent name) and the
          existing ``category_id`` is preserved.

        All items must belong to the given ``store_id``; a
        :class:`StoreBoundaryError` is raised otherwise.

        Returns the list of products as stored after the operation,
        ordered by ``internal_code``.
        """
        sid = uuid_from(store_id)

        if not items:
            return self.list_products(sid)

        # Validate boundary: all items must share the given store_id.
        # Build a lightweight boundary check via Product stub.
        _boundary_ref = Product(
            store_id=sid,
            internal_code="__boundary__",
            raw_name_sample="__boundary__",
        )
        try:
            ensure_same_store(_boundary_ref, *items)
        except StoreBoundaryError:
            raise StoreBoundaryError(
                "all items must belong to the specified store_id"
            )

        entries = self._read_products(sid)

        # Build a lookup by internal_code for efficient updates.
        index: dict[str, int] = {}
        for i, entry in enumerate(entries):
            index[entry["internal_code"]] = i

        for item in items:
            code = item.internal_code
            if code in index:
                # Update existing product: preserve category_id.
                existing = dict_to_product(entries[index[code]])
                updated = Product(
                    store_id=sid,
                    internal_code=code,
                    raw_name_sample=item.raw_name,
                    category_id=existing.category_id,
                )
                entries[index[code]] = product_to_dict(updated)
            else:
                # New product: no category.
                new_product = Product(
                    store_id=sid,
                    internal_code=code,
                    raw_name_sample=item.raw_name,
                    category_id=None,
                )
                entries.append(product_to_dict(new_product))
                index[code] = len(entries) - 1

        # Ensure store directories exist before writing.
        self._layout.ensure_store_dirs(sid)
        self._write_products(sid, entries)

        return self.list_products(sid)


__all__ = [
    "ProductRepository",
]
