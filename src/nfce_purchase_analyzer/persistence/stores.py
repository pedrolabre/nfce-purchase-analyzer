"""Store repository for local JSON persistence."""

from __future__ import annotations

import uuid

from nfce_purchase_analyzer.domain.models import Store
from nfce_purchase_analyzer.persistence.paths import StorageLayout
from nfce_purchase_analyzer.persistence.schemas import (
    dict_to_store,
    read_json,
    store_to_dict,
    write_json,
)


class StoreRepository:
    """Manages creation, listing and lookup of stores on local storage.

    Stores are persisted in two places kept in sync:

    * ``stores.json`` — global index listing all stores.
    * ``stores/<store_id>/store.json`` — individual store detail.

    Store codes are sequential 4-digit strings (``0001``, ``0002``, …)
    calculated from the highest existing numeric code in the index.
    """

    def __init__(self, layout: StorageLayout) -> None:
        if not isinstance(layout, StorageLayout):
            raise TypeError("layout must be a StorageLayout")
        self._layout = layout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_index(self) -> list[dict]:
        """Read the global stores index, returning an empty list if absent."""
        index_path = self._layout.stores_index()
        if not index_path.exists():
            return []
        return read_json(index_path)

    def _write_index(self, entries: list[dict]) -> None:
        """Write the global stores index."""
        write_json(self._layout.stores_index(), entries)

    def _next_code(self, entries: list[dict]) -> str:
        """Calculate the next sequential 4-digit store code.

        Scans all existing codes for the highest numeric value and
        returns the next integer formatted with zero-fill.  Codes
        that are not purely numeric are silently ignored.
        """
        max_num = 0
        for entry in entries:
            code = entry.get("code", "")
            if code.isdigit():
                num = int(code)
                if num > max_num:
                    max_num = num
        return f"{max_num + 1:04d}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_store(self, name: str) -> Store:
        """Create a new store with a sequential code.

        The store name is validated by the domain ``Store`` constructor
        (must be a non-empty string).  The store ID is a new UUID4 and
        the code is the next sequential 4-digit number.

        Both the global index and the individual store file are written
        atomically.  The store directory structure is created via
        ``StorageLayout.ensure_store_dirs``.

        Returns the newly created ``Store``.
        """
        entries = self._read_index()
        code = self._next_code(entries)
        store_id = uuid.uuid4()

        store = Store(id=store_id, code=code, name=name)

        # Ensure directory structure exists.
        self._layout.ensure_store_dirs(store.id)

        # Write individual store file.
        store_dict = store_to_dict(store)
        write_json(self._layout.store_file(store.id), store_dict)

        # Update global index.
        entries.append(store_dict)
        self._write_index(entries)

        return store

    def list_stores(self) -> list[Store]:
        """Return all stores ordered by code (ascending)."""
        entries = self._read_index()
        stores = [dict_to_store(entry) for entry in entries]
        stores.sort(key=lambda s: s.code)
        return stores

    def get_store_by_id(self, store_id: uuid.UUID | str) -> Store | None:
        """Find a store by its UUID.  Returns ``None`` if not found."""
        from nfce_purchase_analyzer.deterministic import uuid_from

        target = uuid_from(store_id)
        for entry in self._read_index():
            store = dict_to_store(entry)
            if store.id == target:
                return store
        return None

    def get_store_by_code(self, code: str) -> Store | None:
        """Find a store by its sequential code.  Returns ``None`` if not found."""
        for entry in self._read_index():
            store = dict_to_store(entry)
            if store.code == code:
                return store
        return None


__all__ = [
    "StoreRepository",
]
