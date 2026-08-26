"""Storage path layout for local JSON persistence."""

from __future__ import annotations

from pathlib import Path
import uuid

from nfce_purchase_analyzer.deterministic import uuid_from, uuid_to_string


class StorageLayout:
    """Encapsulates the local storage directory structure.

    Every path produced by this class is guaranteed to reside within the
    configured *root* directory.  The root must be an absolute path.

    Directory layout::

        <root>/
        ├── stores.json
        └── stores/
            └── <store_id>/
                ├── store.json
                ├── purchases/
                │   └── <purchase_id>.json
                ├── products.json
                └── categories.json
    """

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path):
            raise TypeError("root must be a Path")
        if not root.is_absolute():
            raise ValueError("root must be an absolute path")
        self._root = root.resolve()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def root(self) -> Path:
        """Return the resolved root directory."""
        return self._root

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _confined(self, path: Path) -> Path:
        """Resolve *path* and verify it stays inside *root*."""
        resolved = path.resolve()
        try:
            resolved.relative_to(self._root)
        except ValueError:
            raise ValueError(
                f"path escapes storage root: {resolved}"
            )
        return resolved

    def _store_id_str(self, store_id: uuid.UUID | str) -> str:
        return uuid_to_string(uuid_from(store_id))

    # ------------------------------------------------------------------
    # Global paths
    # ------------------------------------------------------------------

    def stores_index(self) -> Path:
        """Return the path to the global stores index file."""
        return self._confined(self._root / "stores.json")

    def stores_dir(self) -> Path:
        """Return the path to the directory containing per-store data."""
        return self._confined(self._root / "stores")

    # ------------------------------------------------------------------
    # Per-store paths
    # ------------------------------------------------------------------

    def store_dir(self, store_id: uuid.UUID | str) -> Path:
        """Return the directory for a specific store."""
        sid = self._store_id_str(store_id)
        return self._confined(self._root / "stores" / sid)

    def store_file(self, store_id: uuid.UUID | str) -> Path:
        """Return the path to a store's metadata file."""
        sid = self._store_id_str(store_id)
        return self._confined(self._root / "stores" / sid / "store.json")

    def purchases_dir(self, store_id: uuid.UUID | str) -> Path:
        """Return the purchases directory for a store."""
        sid = self._store_id_str(store_id)
        return self._confined(self._root / "stores" / sid / "purchases")

    def purchase_file(
        self,
        store_id: uuid.UUID | str,
        purchase_id: uuid.UUID | str,
    ) -> Path:
        """Return the path to a specific purchase file."""
        sid = self._store_id_str(store_id)
        pid = uuid_to_string(uuid_from(purchase_id))
        return self._confined(
            self._root / "stores" / sid / "purchases" / f"{pid}.json"
        )

    def products_file(self, store_id: uuid.UUID | str) -> Path:
        """Return the path to a store's products catalog."""
        sid = self._store_id_str(store_id)
        return self._confined(self._root / "stores" / sid / "products.json")

    def categories_file(self, store_id: uuid.UUID | str) -> Path:
        """Return the path to a store's categories file."""
        sid = self._store_id_str(store_id)
        return self._confined(self._root / "stores" / sid / "categories.json")

    # ------------------------------------------------------------------
    # Directory creation
    # ------------------------------------------------------------------

    def ensure_store_dirs(self, store_id: uuid.UUID | str) -> None:
        """Create the full directory structure for a store.

        Creates the store directory and the purchases subdirectory.
        Existing directories are silently ignored.
        """
        self.store_dir(store_id).mkdir(parents=True, exist_ok=True)
        self.purchases_dir(store_id).mkdir(parents=True, exist_ok=True)


__all__ = [
    "StorageLayout",
]
