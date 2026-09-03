"""Tests for CategoryRepository."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from nfce_purchase_analyzer.domain.models import Product
from nfce_purchase_analyzer.persistence.paths import StorageLayout
from nfce_purchase_analyzer.persistence.categories import CategoryRepository


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _layout(tmp_path: Path) -> StorageLayout:
    return StorageLayout(tmp_path)


def _repo(tmp_path: Path) -> CategoryRepository:
    return CategoryRepository(_layout(tmp_path))


STORE_A = uuid.uuid4()
STORE_B = uuid.uuid4()


# ==================================================================
# Empty repository
# ==================================================================


class TestEmptyRepository:
    def test_get_returns_none(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        assert repo.get_category(STORE_A, uuid.uuid4()) is None

    def test_list_returns_empty(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        assert repo.list_categories(STORE_A) == []

    def test_count_returns_zero(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        assert repo.count_categories(STORE_A) == 0


# ==================================================================
# Create single category
# ==================================================================


class TestCreateSingleCategory:
    def test_create_returns_category(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        cat = repo.create_category(STORE_A, "Alimentos")
        assert cat.store_id == STORE_A
        assert cat.name == "Alimentos"
        assert cat.parent_id is None
        assert isinstance(cat.id, uuid.UUID)

    def test_get_after_create(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        cat = repo.create_category(STORE_A, "Alimentos")
        found = repo.get_category(STORE_A, cat.id)
        assert found is not None
        assert found.id == cat.id
        assert found.name == "Alimentos"
        assert found.store_id == STORE_A

    def test_count_after_create(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.create_category(STORE_A, "Alimentos")
        assert repo.count_categories(STORE_A) == 1

    def test_list_after_create(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.create_category(STORE_A, "Alimentos")
        cats = repo.list_categories(STORE_A)
        assert len(cats) == 1
        assert cats[0].name == "Alimentos"

    def test_not_found_different_store(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        cat = repo.create_category(STORE_A, "Alimentos")
        assert repo.get_category(STORE_B, cat.id) is None

    def test_not_found_different_id(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.create_category(STORE_A, "Alimentos")
        assert repo.get_category(STORE_A, uuid.uuid4()) is None


# ==================================================================
# Subcategories (parent_id)
# ==================================================================


class TestSubcategories:
    def test_create_with_parent(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        parent = repo.create_category(STORE_A, "Alimentos")
        child = repo.create_category(STORE_A, "Frutas", parent_id=parent.id)
        assert child.parent_id == parent.id
        assert child.store_id == STORE_A

    def test_get_subcategory(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        parent = repo.create_category(STORE_A, "Alimentos")
        child = repo.create_category(STORE_A, "Frutas", parent_id=parent.id)
        found = repo.get_category(STORE_A, child.id)
        assert found is not None
        assert found.parent_id == parent.id

    def test_nested_subcategories(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        root = repo.create_category(STORE_A, "Alimentos")
        mid = repo.create_category(STORE_A, "Frutas", parent_id=root.id)
        leaf = repo.create_category(STORE_A, "Citricos", parent_id=mid.id)
        assert leaf.parent_id == mid.id
        assert repo.count_categories(STORE_A) == 3

    def test_reject_nonexistent_parent(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        with pytest.raises(ValueError, match="parent_id"):
            repo.create_category(STORE_A, "Frutas", parent_id=uuid.uuid4())

    def test_reject_parent_from_different_store(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path)
        parent_b = repo.create_category(STORE_B, "Bebidas")
        # parent_b exists in STORE_B, not STORE_A
        with pytest.raises(ValueError, match="parent_id"):
            repo.create_category(STORE_A, "Sucos", parent_id=parent_b.id)


# ==================================================================
# Multiple categories
# ==================================================================


class TestMultipleCategories:
    def test_multiple_categories_same_store(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.create_category(STORE_A, "Alimentos")
        repo.create_category(STORE_A, "Bebidas")
        repo.create_category(STORE_A, "Limpeza")
        assert repo.count_categories(STORE_A) == 3

    def test_list_ordered_by_name(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.create_category(STORE_A, "Limpeza")
        repo.create_category(STORE_A, "Alimentos")
        repo.create_category(STORE_A, "Bebidas")
        cats = repo.list_categories(STORE_A, order_by="name")
        names = [c.name for c in cats]
        assert names == ["Alimentos", "Bebidas", "Limpeza"]

    def test_list_ordered_by_id(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        c1 = repo.create_category(STORE_A, "Limpeza")
        c2 = repo.create_category(STORE_A, "Alimentos")
        c3 = repo.create_category(STORE_A, "Bebidas")
        cats = repo.list_categories(STORE_A, order_by="id")
        ids = [c.id for c in cats]
        expected = sorted([c1.id, c2.id, c3.id], key=str)
        assert ids == expected

    def test_invalid_order_by_raises(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.create_category(STORE_A, "Alimentos")
        with pytest.raises(ValueError, match="unknown order_by"):
            repo.list_categories(STORE_A, order_by="invalid")


# ==================================================================
# Store isolation
# ==================================================================


class TestStoreIsolation:
    def test_different_stores_isolated(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.create_category(STORE_A, "Alimentos")
        repo.create_category(STORE_B, "Bebidas")
        assert repo.count_categories(STORE_A) == 1
        assert repo.count_categories(STORE_B) == 1

    def test_list_only_own_store(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.create_category(STORE_A, "Alimentos")
        repo.create_category(STORE_A, "Limpeza")
        repo.create_category(STORE_B, "Bebidas")
        cats_a = repo.list_categories(STORE_A)
        cats_b = repo.list_categories(STORE_B)
        assert len(cats_a) == 2
        assert len(cats_b) == 1
        assert all(c.store_id == STORE_A for c in cats_a)
        assert all(c.store_id == STORE_B for c in cats_b)


# ==================================================================
# Product without category remains valid
# ==================================================================


class TestProductWithoutCategory:
    def test_product_without_category(self) -> None:
        """Products with category_id=None remain valid and constructable."""
        product = Product(
            store_id=STORE_A,
            internal_code="001",
            raw_name_sample="Arroz 5kg",
            category_id=None,
        )
        assert product.category_id is None
        assert product.internal_code == "001"


# ==================================================================
# Constructor validation
# ==================================================================


class TestValidation:
    def test_constructor_rejects_non_layout(self) -> None:
        with pytest.raises(TypeError):
            CategoryRepository("not_a_layout")  # type: ignore[arg-type]


# ==================================================================
# Persistence integrity
# ==================================================================


class TestPersistenceIntegrity:
    def test_file_exists_after_create(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo = CategoryRepository(layout)
        repo.create_category(STORE_A, "Alimentos")
        assert layout.categories_file(STORE_A).exists()

    def test_json_is_valid(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo = CategoryRepository(layout)
        repo.create_category(STORE_A, "Alimentos")
        content = layout.categories_file(STORE_A).read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_deterministic_order(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo = CategoryRepository(layout)
        repo.create_category(STORE_A, "Limpeza")
        repo.create_category(STORE_A, "Alimentos")
        repo.create_category(STORE_A, "Bebidas")
        content = layout.categories_file(STORE_A).read_text(encoding="utf-8")
        data = json.loads(content)
        names = [entry["name"] for entry in data]
        assert names == ["Alimentos", "Bebidas", "Limpeza"]

    def test_directory_created(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo = CategoryRepository(layout)
        repo.create_category(STORE_A, "Alimentos")
        assert layout.store_dir(STORE_A).is_dir()

    def test_json_ends_with_newline(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo = CategoryRepository(layout)
        repo.create_category(STORE_A, "Alimentos")
        content = layout.categories_file(STORE_A).read_text(encoding="utf-8")
        assert content.endswith("\n")


# ==================================================================
# Reload from disk
# ==================================================================


class TestReloadFromDisk:
    def test_get_after_reload(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo1 = CategoryRepository(layout)
        cat = repo1.create_category(STORE_A, "Alimentos")
        repo2 = CategoryRepository(layout)
        found = repo2.get_category(STORE_A, cat.id)
        assert found is not None
        assert found.name == "Alimentos"

    def test_list_after_reload(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo1 = CategoryRepository(layout)
        repo1.create_category(STORE_A, "Alimentos")
        repo1.create_category(STORE_A, "Bebidas")
        repo2 = CategoryRepository(layout)
        cats = repo2.list_categories(STORE_A)
        assert len(cats) == 2

    def test_count_after_reload(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo1 = CategoryRepository(layout)
        repo1.create_category(STORE_A, "Alimentos")
        repo2 = CategoryRepository(layout)
        assert repo2.count_categories(STORE_A) == 1

    def test_subcategory_after_reload(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo1 = CategoryRepository(layout)
        parent = repo1.create_category(STORE_A, "Alimentos")
        child = repo1.create_category(
            STORE_A, "Frutas", parent_id=parent.id
        )
        repo2 = CategoryRepository(layout)
        found = repo2.get_category(STORE_A, child.id)
        assert found is not None
        assert found.parent_id == parent.id
