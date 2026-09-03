"""Category repository for local JSON persistence."""

from __future__ import annotations

import uuid

from nfce_purchase_analyzer.deterministic import uuid_from
from nfce_purchase_analyzer.domain.models import Category
from nfce_purchase_analyzer.persistence.paths import StorageLayout
from nfce_purchase_analyzer.persistence.schemas import (
    category_to_dict,
    dict_to_category,
    read_json,
    write_json,
)


class CategoryRepository:
    """Manages persistence of categories per store on local storage.

    Categories are stored in a single JSON file per store at the canonical
    path ``stores/<store_id>/categories.json`` as determined by
    :meth:`StorageLayout.categories_file`.

    Categories are identified by their ``id`` (UUID) and belong strictly
    to a single ``store_id``.  An optional ``parent_id`` allows building
    a hierarchy; the parent must exist in the same store.
    """

    def __init__(self, layout: StorageLayout) -> None:
        if not isinstance(layout, StorageLayout):
            raise TypeError("layout must be a StorageLayout")
        self._layout = layout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_categories(self, store_id: uuid.UUID) -> list[dict]:
        """Read the categories file, returning an empty list if absent."""
        path = self._layout.categories_file(store_id)
        if not path.exists():
            return []
        return read_json(path)

    def _write_categories(
        self,
        store_id: uuid.UUID,
        entries: list[dict],
    ) -> None:
        """Write the categories file with deterministic ordering."""
        # Sort by name for deterministic output.
        entries.sort(key=lambda e: e["name"])
        write_json(self._layout.categories_file(store_id), entries)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_category(
        self,
        store_id: uuid.UUID | str,
        name: str,
        parent_id: uuid.UUID | str | None = None,
    ) -> Category:
        """Create a new category for a store.

        The category receives a freshly generated UUID.  If *parent_id*
        is provided, it must reference an existing category in the same
        store; otherwise a :class:`ValueError` is raised.

        The store directory structure is created automatically if needed.

        Returns the newly created :class:`Category`.
        """
        sid = uuid_from(store_id)
        pid: uuid.UUID | None = None
        if parent_id is not None:
            pid = uuid_from(parent_id)

        entries = self._read_categories(sid)

        # Validate parent_id if provided.
        if pid is not None:
            parent_found = False
            for entry in entries:
                if entry["id"] == str(pid):
                    parent_found = True
                    break
            if not parent_found:
                raise ValueError(
                    "parent_id must reference an existing category "
                    "in the same store"
                )

        category_id = uuid.uuid4()
        category = Category(
            store_id=sid,
            id=category_id,
            name=name,
            parent_id=pid,
        )

        entries.append(category_to_dict(category))

        # Ensure store directories exist before writing.
        self._layout.ensure_store_dirs(sid)
        self._write_categories(sid, entries)
        return category

    def get_category(
        self,
        store_id: uuid.UUID | str,
        category_id: uuid.UUID | str,
    ) -> Category | None:
        """Find a category by store ID and category ID.

        Returns ``None`` if the category does not exist.
        """
        sid = uuid_from(store_id)
        cid = uuid_from(category_id)
        cid_str = str(cid)
        for entry in self._read_categories(sid):
            if entry["id"] == cid_str:
                return dict_to_category(entry)
        return None

    def list_categories(
        self,
        store_id: uuid.UUID | str,
        *,
        order_by: str = "name",
    ) -> list[Category]:
        """Return all categories for a store.

        The *order_by* parameter controls sorting:

        * ``"name"`` (default) — alphabetical by category name.
        * ``"id"`` — lexicographic by category UUID string.

        Raises :class:`ValueError` for unknown *order_by* values.
        """
        sid = uuid_from(store_id)
        entries = self._read_categories(sid)
        categories = [dict_to_category(entry) for entry in entries]

        if order_by == "name":
            categories.sort(key=lambda c: c.name)
        elif order_by == "id":
            categories.sort(key=lambda c: str(c.id))
        else:
            raise ValueError(f"unknown order_by value: {order_by!r}")

        return categories

    def count_categories(
        self,
        store_id: uuid.UUID | str,
    ) -> int:
        """Count the number of categories for a store.

        Returns ``0`` if the categories file does not exist.
        """
        sid = uuid_from(store_id)
        return len(self._read_categories(sid))


__all__ = [
    "CategoryRepository",
]
