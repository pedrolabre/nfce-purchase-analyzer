"""Tests for local storage layout, paths, and JSON schemas."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from nfce_purchase_analyzer.domain.models import (
    Category,
    Product,
    Purchase,
    PurchaseItem,
    Store,
)
from nfce_purchase_analyzer.persistence.paths import StorageLayout
from nfce_purchase_analyzer.persistence.schemas import (
    category_to_dict,
    dict_to_category,
    dict_to_product,
    dict_to_purchase,
    dict_to_purchase_item,
    dict_to_store,
    product_to_dict,
    purchase_item_to_dict,
    purchase_to_dict,
    read_json,
    store_to_dict,
    write_json,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

STORE_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PURCHASE_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
CATEGORY_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
PARENT_CATEGORY_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
BRT = timezone(timedelta(hours=-3))
PURCHASE_DATE = datetime(2026, 1, 15, 14, 30, 0, tzinfo=BRT)


def _make_store() -> Store:
    return Store(id=STORE_ID, code="0001", name="Bem Maior")


def _make_purchase() -> Purchase:
    return Purchase(
        id=PURCHASE_ID,
        store_id=STORE_ID,
        date=PURCHASE_DATE,
        total_value=Decimal("125.50"),
        total_items=2,
        source_pdf="compras/nota-001.pdf",
    )


def _make_items() -> list[PurchaseItem]:
    return [
        PurchaseItem(
            purchase_id=PURCHASE_ID,
            store_id=STORE_ID,
            internal_code="1001",
            raw_name="ARROZ BRANCO 5KG",
            quantity=Decimal("2.000"),
            unit_price=Decimal("24.90"),
            total_price=Decimal("49.80"),
        ),
        PurchaseItem(
            purchase_id=PURCHASE_ID,
            store_id=STORE_ID,
            internal_code="2002",
            raw_name="BANANA PRATA",
            quantity=Decimal("1.542"),
            unit_price=Decimal("4.99"),
            total_price=Decimal("7.69"),
        ),
    ]


def _make_product() -> Product:
    return Product(
        store_id=STORE_ID,
        internal_code="1001",
        raw_name_sample="ARROZ BRANCO 5KG",
        category_id=CATEGORY_ID,
    )


def _make_product_no_category() -> Product:
    return Product(
        store_id=STORE_ID,
        internal_code="2002",
        raw_name_sample="BANANA PRATA",
    )


def _make_category() -> Category:
    return Category(
        store_id=STORE_ID,
        id=CATEGORY_ID,
        name="Alimentos",
        parent_id=PARENT_CATEGORY_ID,
    )


def _make_category_no_parent() -> Category:
    return Category(
        store_id=STORE_ID,
        id=CATEGORY_ID,
        name="Alimentos",
    )


# ==================================================================
# StorageLayout — path generation
# ==================================================================


class TestStorageLayoutPaths:
    """StorageLayout generates the expected paths within root."""

    def test_root_property(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        assert layout.root == tmp_path.resolve()

    def test_stores_index(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        assert layout.stores_index() == tmp_path / "stores.json"

    def test_stores_dir(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        assert layout.stores_dir() == tmp_path / "stores"

    def test_store_dir(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        expected = tmp_path / "stores" / str(STORE_ID)
        assert layout.store_dir(STORE_ID) == expected

    def test_store_file(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        expected = tmp_path / "stores" / str(STORE_ID) / "store.json"
        assert layout.store_file(STORE_ID) == expected

    def test_purchases_dir(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        expected = tmp_path / "stores" / str(STORE_ID) / "purchases"
        assert layout.purchases_dir(STORE_ID) == expected

    def test_purchase_file(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        expected = (
            tmp_path
            / "stores"
            / str(STORE_ID)
            / "purchases"
            / f"{PURCHASE_ID}.json"
        )
        assert layout.purchase_file(STORE_ID, PURCHASE_ID) == expected

    def test_products_file(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        expected = tmp_path / "stores" / str(STORE_ID) / "products.json"
        assert layout.products_file(STORE_ID) == expected

    def test_categories_file(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        expected = tmp_path / "stores" / str(STORE_ID) / "categories.json"
        assert layout.categories_file(STORE_ID) == expected

    def test_accepts_string_uuid(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        sid = str(STORE_ID)
        assert layout.store_dir(sid) == layout.store_dir(STORE_ID)

    def test_uuid_is_lowercase(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        sid_upper = str(STORE_ID).upper()
        path = layout.store_dir(sid_upper)
        assert str(STORE_ID) in str(path)


# ==================================================================
# StorageLayout — confinement
# ==================================================================


class TestStorageLayoutConfinement:
    """All paths must stay inside the root directory."""

    def test_rejects_relative_root(self) -> None:
        with pytest.raises(ValueError, match="absolute"):
            StorageLayout(Path("relative/path"))

    def test_rejects_non_path_root(self) -> None:
        with pytest.raises(TypeError, match="Path"):
            StorageLayout("/some/path")  # type: ignore[arg-type]

    def test_paths_are_confined(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        all_paths = [
            layout.stores_index(),
            layout.stores_dir(),
            layout.store_dir(STORE_ID),
            layout.store_file(STORE_ID),
            layout.purchases_dir(STORE_ID),
            layout.purchase_file(STORE_ID, PURCHASE_ID),
            layout.products_file(STORE_ID),
            layout.categories_file(STORE_ID),
        ]
        for path in all_paths:
            assert str(path.resolve()).startswith(str(tmp_path.resolve()))


# ==================================================================
# StorageLayout — directory creation
# ==================================================================


class TestStorageLayoutDirCreation:
    """ensure_store_dirs creates the expected directory structure."""

    def test_creates_store_and_purchases_dirs(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        layout.ensure_store_dirs(STORE_ID)
        assert layout.store_dir(STORE_ID).is_dir()
        assert layout.purchases_dir(STORE_ID).is_dir()

    def test_idempotent(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        layout.ensure_store_dirs(STORE_ID)
        layout.ensure_store_dirs(STORE_ID)
        assert layout.store_dir(STORE_ID).is_dir()
        assert layout.purchases_dir(STORE_ID).is_dir()


# ==================================================================
# JSON file I/O — write_json / read_json
# ==================================================================


class TestJsonFileIO:
    """write_json and read_json produce correct files in tmp_path."""

    def test_write_and_read_roundtrip(self, tmp_path: Path) -> None:
        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        path = tmp_path / "test.json"
        write_json(path, data)
        result = read_json(path)
        assert result == data

    def test_sorted_keys(self, tmp_path: Path) -> None:
        data = {"zebra": 1, "alpha": 2, "middle": 3}
        path = tmp_path / "sorted.json"
        write_json(path, data)
        content = path.read_text(encoding="utf-8")
        keys_positions = [content.index(f'"{k}"') for k in ["alpha", "middle", "zebra"]]
        assert keys_positions == sorted(keys_positions)

    def test_two_space_indent(self, tmp_path: Path) -> None:
        data = {"nested": {"key": "value"}}
        path = tmp_path / "indent.json"
        write_json(path, data)
        content = path.read_text(encoding="utf-8")
        assert '  "nested"' in content
        assert '    "key"' in content

    def test_trailing_newline(self, tmp_path: Path) -> None:
        data = {"key": "value"}
        path = tmp_path / "newline.json"
        write_json(path, data)
        content = path.read_bytes()
        assert content.endswith(b"\n")

    def test_utf8_encoding(self, tmp_path: Path) -> None:
        data = {"name": "Açaí com Côco"}
        path = tmp_path / "utf8.json"
        write_json(path, data)
        content = path.read_bytes()
        assert "Açaí com Côco".encode("utf-8") in content

    def test_deterministic_output(self, tmp_path: Path) -> None:
        data = {"b": 2, "a": 1, "c": [3, 4]}
        path1 = tmp_path / "det1.json"
        path2 = tmp_path / "det2.json"
        write_json(path1, data)
        write_json(path2, data)
        assert path1.read_bytes() == path2.read_bytes()


# ==================================================================
# Store serialization
# ==================================================================


class TestStoreSchema:
    """Store serialization and deserialization."""

    def test_roundtrip(self) -> None:
        store = _make_store()
        data = store_to_dict(store)
        restored = dict_to_store(data)
        assert restored.id == store.id
        assert restored.code == store.code
        assert restored.name == store.name

    def test_dict_structure(self) -> None:
        store = _make_store()
        data = store_to_dict(store)
        assert data["id"] == str(STORE_ID)
        assert data["code"] == "0001"
        assert data["name"] == "Bem Maior"

    def test_json_roundtrip(self, tmp_path: Path) -> None:
        store = _make_store()
        path = tmp_path / "store.json"
        write_json(path, store_to_dict(store))
        restored = dict_to_store(read_json(path))
        assert restored.id == store.id
        assert restored.code == store.code
        assert restored.name == store.name


# ==================================================================
# PurchaseItem serialization
# ==================================================================


class TestPurchaseItemSchema:
    """PurchaseItem serialization and deserialization."""

    def test_roundtrip(self) -> None:
        items = _make_items()
        for item in items:
            data = purchase_item_to_dict(item)
            restored = dict_to_purchase_item(data, item.purchase_id)
            assert restored.purchase_id == item.purchase_id
            assert restored.store_id == item.store_id
            assert restored.internal_code == item.internal_code
            assert restored.raw_name == item.raw_name
            assert restored.quantity == item.quantity
            assert restored.unit_price == item.unit_price
            assert restored.total_price == item.total_price

    def test_decimal_as_string(self) -> None:
        item = _make_items()[1]  # banana with 1.542 kg
        data = purchase_item_to_dict(item)
        assert isinstance(data["quantity"], str)
        assert data["quantity"] == "1.542"
        assert isinstance(data["unit_price"], str)
        assert isinstance(data["total_price"], str)

    def test_uuid_as_string(self) -> None:
        item = _make_items()[0]
        data = purchase_item_to_dict(item)
        assert isinstance(data["purchase_id"], str)
        assert isinstance(data["store_id"], str)


# ==================================================================
# Purchase (with items) serialization
# ==================================================================


class TestPurchaseSchema:
    """Purchase serialization with embedded items."""

    def test_roundtrip(self) -> None:
        purchase = _make_purchase()
        items = _make_items()
        data = purchase_to_dict(purchase, items)
        restored_purchase, restored_items = dict_to_purchase(data)
        assert restored_purchase.id == purchase.id
        assert restored_purchase.store_id == purchase.store_id
        assert restored_purchase.date == purchase.date
        assert restored_purchase.total_value == purchase.total_value
        assert restored_purchase.total_items == purchase.total_items
        assert restored_purchase.source_pdf == purchase.source_pdf
        assert len(restored_items) == len(items)

    def test_date_iso_format(self) -> None:
        purchase = _make_purchase()
        data = purchase_to_dict(purchase, [])
        assert isinstance(data["date"], str)
        # Must be parseable back
        parsed = datetime.fromisoformat(data["date"])
        assert parsed == PURCHASE_DATE

    def test_total_value_as_string(self) -> None:
        purchase = _make_purchase()
        data = purchase_to_dict(purchase, [])
        assert isinstance(data["total_value"], str)
        assert data["total_value"] == "125.50"

    def test_total_items_as_int(self) -> None:
        purchase = _make_purchase()
        data = purchase_to_dict(purchase, [])
        assert isinstance(data["total_items"], int)
        assert data["total_items"] == 2

    def test_items_embedded(self) -> None:
        purchase = _make_purchase()
        items = _make_items()
        data = purchase_to_dict(purchase, items)
        assert "items" in data
        assert len(data["items"]) == 2

    def test_json_roundtrip(self, tmp_path: Path) -> None:
        purchase = _make_purchase()
        items = _make_items()
        path = tmp_path / "purchase.json"
        write_json(path, purchase_to_dict(purchase, items))
        restored_purchase, restored_items = dict_to_purchase(read_json(path))
        assert restored_purchase.id == purchase.id
        assert restored_purchase.date == purchase.date
        assert restored_purchase.total_value == purchase.total_value
        assert len(restored_items) == 2
        assert restored_items[0].internal_code == "1001"
        assert restored_items[1].quantity == Decimal("1.542")


# ==================================================================
# Product serialization
# ==================================================================


class TestProductSchema:
    """Product serialization and deserialization."""

    def test_roundtrip_with_category(self) -> None:
        product = _make_product()
        data = product_to_dict(product)
        restored = dict_to_product(data)
        assert restored.store_id == product.store_id
        assert restored.internal_code == product.internal_code
        assert restored.raw_name_sample == product.raw_name_sample
        assert restored.category_id == product.category_id

    def test_roundtrip_without_category(self) -> None:
        product = _make_product_no_category()
        data = product_to_dict(product)
        restored = dict_to_product(data)
        assert restored.category_id is None

    def test_category_id_null_in_json(self) -> None:
        product = _make_product_no_category()
        data = product_to_dict(product)
        assert data["category_id"] is None

    def test_json_roundtrip(self, tmp_path: Path) -> None:
        product = _make_product()
        path = tmp_path / "product.json"
        write_json(path, product_to_dict(product))
        restored = dict_to_product(read_json(path))
        assert restored.store_id == product.store_id
        assert restored.category_id == CATEGORY_ID


# ==================================================================
# Category serialization
# ==================================================================


class TestCategorySchema:
    """Category serialization and deserialization."""

    def test_roundtrip_with_parent(self) -> None:
        category = _make_category()
        data = category_to_dict(category)
        restored = dict_to_category(data)
        assert restored.store_id == category.store_id
        assert restored.id == category.id
        assert restored.name == category.name
        assert restored.parent_id == category.parent_id

    def test_roundtrip_without_parent(self) -> None:
        category = _make_category_no_parent()
        data = category_to_dict(category)
        restored = dict_to_category(data)
        assert restored.parent_id is None

    def test_parent_id_null_in_json(self) -> None:
        category = _make_category_no_parent()
        data = category_to_dict(category)
        assert data["parent_id"] is None

    def test_json_roundtrip(self, tmp_path: Path) -> None:
        category = _make_category()
        path = tmp_path / "category.json"
        write_json(path, category_to_dict(category))
        restored = dict_to_category(read_json(path))
        assert restored.id == CATEGORY_ID
        assert restored.parent_id == PARENT_CATEGORY_ID


# ==================================================================
# Full storage integration
# ==================================================================


class TestStorageIntegration:
    """End-to-end test: layout + schemas + file I/O in tmp_path."""

    def test_full_store_persistence(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        layout.ensure_store_dirs(STORE_ID)

        # Write store
        store = _make_store()
        write_json(layout.store_file(STORE_ID), store_to_dict(store))

        # Write stores index
        write_json(layout.stores_index(), [store_to_dict(store)])

        # Write purchase with items
        purchase = _make_purchase()
        items = _make_items()
        write_json(
            layout.purchase_file(STORE_ID, PURCHASE_ID),
            purchase_to_dict(purchase, items),
        )

        # Write products
        products = [_make_product(), _make_product_no_category()]
        write_json(
            layout.products_file(STORE_ID),
            [product_to_dict(p) for p in products],
        )

        # Write categories
        categories = [_make_category()]
        write_json(
            layout.categories_file(STORE_ID),
            [category_to_dict(c) for c in categories],
        )

        # --- Read back and verify ---

        # Store
        restored_store = dict_to_store(read_json(layout.store_file(STORE_ID)))
        assert restored_store.id == STORE_ID
        assert restored_store.name == "Bem Maior"

        # Stores index
        index_data = read_json(layout.stores_index())
        assert len(index_data) == 1
        assert dict_to_store(index_data[0]).id == STORE_ID

        # Purchase
        purchase_data = read_json(layout.purchase_file(STORE_ID, PURCHASE_ID))
        restored_purchase, restored_items = dict_to_purchase(purchase_data)
        assert restored_purchase.total_value == Decimal("125.50")
        assert len(restored_items) == 2
        assert restored_items[1].quantity == Decimal("1.542")

        # Products
        products_data = read_json(layout.products_file(STORE_ID))
        restored_products = [dict_to_product(d) for d in products_data]
        assert len(restored_products) == 2
        assert restored_products[0].category_id == CATEGORY_ID
        assert restored_products[1].category_id is None

        # Categories
        categories_data = read_json(layout.categories_file(STORE_ID))
        restored_categories = [dict_to_category(d) for d in categories_data]
        assert len(restored_categories) == 1
        assert restored_categories[0].parent_id == PARENT_CATEGORY_ID

    def test_all_files_inside_tmp_path(self, tmp_path: Path) -> None:
        """Verify no file is written outside tmp_path."""
        layout = StorageLayout(tmp_path)
        layout.ensure_store_dirs(STORE_ID)

        store = _make_store()
        write_json(layout.store_file(STORE_ID), store_to_dict(store))
        write_json(layout.stores_index(), [store_to_dict(store)])

        purchase = _make_purchase()
        items = _make_items()
        write_json(
            layout.purchase_file(STORE_ID, PURCHASE_ID),
            purchase_to_dict(purchase, items),
        )

        # Walk all files and check confinement
        root_str = str(tmp_path.resolve())
        for file_path in tmp_path.rglob("*"):
            assert str(file_path.resolve()).startswith(root_str)
