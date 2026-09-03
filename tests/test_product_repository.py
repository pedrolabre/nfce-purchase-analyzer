"""Tests for ProductRepository."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

from nfce_purchase_analyzer.domain.models import (
    Product,
    PurchaseItem,
    StoreBoundaryError,
)
from nfce_purchase_analyzer.persistence.paths import StorageLayout
from nfce_purchase_analyzer.persistence.products import ProductRepository


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _layout(tmp_path: Path) -> StorageLayout:
    return StorageLayout(tmp_path)


def _repo(tmp_path: Path) -> ProductRepository:
    return ProductRepository(_layout(tmp_path))


STORE_A = uuid.uuid4()
STORE_B = uuid.uuid4()
PURCHASE_ID = uuid.uuid4()


def _product(
    store_id: uuid.UUID = STORE_A,
    internal_code: str = "001",
    raw_name_sample: str = "Produto A",
    category_id: uuid.UUID | None = None,
) -> Product:
    return Product(
        store_id=store_id,
        internal_code=internal_code,
        raw_name_sample=raw_name_sample,
        category_id=category_id,
    )


def _item(
    store_id: uuid.UUID = STORE_A,
    purchase_id: uuid.UUID = PURCHASE_ID,
    internal_code: str = "001",
    raw_name: str = "Produto A",
    quantity: Decimal = Decimal("1.000"),
    unit_price: Decimal = Decimal("10.00"),
    total_price: Decimal = Decimal("10.00"),
) -> PurchaseItem:
    return PurchaseItem(
        purchase_id=purchase_id,
        store_id=store_id,
        internal_code=internal_code,
        raw_name=raw_name,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
    )


# ==================================================================
# Empty repository
# ==================================================================


class TestEmptyRepository:
    def test_get_returns_none(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        assert repo.get_product(STORE_A, "001") is None

    def test_list_returns_empty(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        assert repo.list_products(STORE_A) == []

    def test_count_returns_zero(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        assert repo.count_products(STORE_A) == 0


# ==================================================================
# Single product upsert
# ==================================================================


class TestUpsertSingleProduct:
    def test_insert_new_product(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        product = _product()
        result = repo.upsert_product(product)
        assert result.store_id == STORE_A
        assert result.internal_code == "001"
        assert result.raw_name_sample == "Produto A"
        assert result.category_id is None

    def test_get_after_insert(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product())
        found = repo.get_product(STORE_A, "001")
        assert found is not None
        assert found.internal_code == "001"
        assert found.raw_name_sample == "Produto A"

    def test_count_after_insert(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product())
        assert repo.count_products(STORE_A) == 1

    def test_list_after_insert(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product())
        products = repo.list_products(STORE_A)
        assert len(products) == 1
        assert products[0].internal_code == "001"

    def test_not_found_different_code(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product())
        assert repo.get_product(STORE_A, "999") is None

    def test_not_found_different_store(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product())
        assert repo.get_product(STORE_B, "001") is None


# ==================================================================
# Update existing product
# ==================================================================


class TestUpdateExistingProduct:
    def test_update_raw_name_sample(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product(raw_name_sample="Nome Antigo"))
        updated = _product(raw_name_sample="Nome Novo")
        result = repo.upsert_product(updated)
        assert result.raw_name_sample == "Nome Novo"

    def test_preserve_category_on_update(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        cat_id = uuid.uuid4()
        repo.upsert_product(_product(category_id=cat_id))
        # Update without category — it should be preserved.
        updated = _product(raw_name_sample="Nome Novo", category_id=None)
        result = repo.upsert_product(updated)
        assert result.category_id == cat_id

    def test_count_unchanged_after_update(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product())
        repo.upsert_product(_product(raw_name_sample="Outro Nome"))
        assert repo.count_products(STORE_A) == 1

    def test_get_reflects_update(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product(raw_name_sample="Antes"))
        repo.upsert_product(_product(raw_name_sample="Depois"))
        found = repo.get_product(STORE_A, "001")
        assert found is not None
        assert found.raw_name_sample == "Depois"


# ==================================================================
# Multiple products
# ==================================================================


class TestMultipleProducts:
    def test_multiple_codes_same_store(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product(internal_code="002", raw_name_sample="B"))
        repo.upsert_product(_product(internal_code="001", raw_name_sample="A"))
        repo.upsert_product(_product(internal_code="003", raw_name_sample="C"))
        assert repo.count_products(STORE_A) == 3

    def test_list_ordered_by_internal_code(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product(internal_code="003", raw_name_sample="C"))
        repo.upsert_product(_product(internal_code="001", raw_name_sample="A"))
        repo.upsert_product(_product(internal_code="002", raw_name_sample="B"))
        products = repo.list_products(STORE_A)
        codes = [p.internal_code for p in products]
        assert codes == ["001", "002", "003"]

    def test_different_stores_isolated(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product(store_id=STORE_A, internal_code="001"))
        repo.upsert_product(
            _product(
                store_id=STORE_B,
                internal_code="001",
                raw_name_sample="Outro",
            )
        )
        assert repo.count_products(STORE_A) == 1
        assert repo.count_products(STORE_B) == 1
        a = repo.get_product(STORE_A, "001")
        b = repo.get_product(STORE_B, "001")
        assert a is not None
        assert b is not None
        assert a.raw_name_sample == "Produto A"
        assert b.raw_name_sample == "Outro"


# ==================================================================
# Implicit registration from items (upsert_from_items)
# ==================================================================


class TestUpsertFromItems:
    def test_register_new_products(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        items = [
            _item(internal_code="001", raw_name="Arroz 5kg"),
            _item(internal_code="002", raw_name="Feijao 1kg"),
        ]
        products = repo.upsert_from_items(STORE_A, items)
        assert len(products) == 2
        assert products[0].internal_code == "001"
        assert products[0].raw_name_sample == "Arroz 5kg"
        assert products[0].category_id is None
        assert products[1].internal_code == "002"
        assert products[1].raw_name_sample == "Feijao 1kg"
        assert products[1].category_id is None

    def test_update_existing_name(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(
            _product(internal_code="001", raw_name_sample="Nome Antigo")
        )
        items = [_item(internal_code="001", raw_name="Nome Novo")]
        products = repo.upsert_from_items(STORE_A, items)
        assert len(products) == 1
        assert products[0].raw_name_sample == "Nome Novo"

    def test_preserve_category_from_items(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        cat_id = uuid.uuid4()
        repo.upsert_product(
            _product(
                internal_code="001",
                raw_name_sample="Antigo",
                category_id=cat_id,
            )
        )
        items = [_item(internal_code="001", raw_name="Novo")]
        products = repo.upsert_from_items(STORE_A, items)
        assert products[0].category_id == cat_id
        assert products[0].raw_name_sample == "Novo"

    def test_mix_new_and_existing(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(
            _product(internal_code="001", raw_name_sample="Existente")
        )
        items = [
            _item(internal_code="001", raw_name="Atualizado"),
            _item(internal_code="002", raw_name="Novo Produto"),
        ]
        products = repo.upsert_from_items(STORE_A, items)
        assert len(products) == 2
        assert products[0].raw_name_sample == "Atualizado"
        assert products[1].raw_name_sample == "Novo Produto"
        assert products[1].category_id is None

    def test_empty_items_returns_current(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        repo.upsert_product(_product(internal_code="001"))
        products = repo.upsert_from_items(STORE_A, [])
        assert len(products) == 1

    def test_duplicate_items_last_wins(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        items = [
            _item(internal_code="001", raw_name="Primeiro"),
            _item(internal_code="001", raw_name="Segundo"),
        ]
        products = repo.upsert_from_items(STORE_A, items)
        assert len(products) == 1
        assert products[0].raw_name_sample == "Segundo"


# ==================================================================
# Store boundary validation
# ==================================================================


class TestStoreBoundary:
    def test_upsert_from_items_rejects_wrong_store(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path)
        items = [_item(store_id=STORE_B, internal_code="001")]
        with pytest.raises(StoreBoundaryError):
            repo.upsert_from_items(STORE_A, items)

    def test_upsert_from_items_rejects_mixed_stores(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path)
        items = [
            _item(store_id=STORE_A, internal_code="001"),
            _item(store_id=STORE_B, internal_code="002"),
        ]
        with pytest.raises(StoreBoundaryError):
            repo.upsert_from_items(STORE_A, items)


# ==================================================================
# Constructor validation
# ==================================================================


class TestValidation:
    def test_constructor_rejects_non_layout(self) -> None:
        with pytest.raises(TypeError):
            ProductRepository("not_a_layout")  # type: ignore[arg-type]


# ==================================================================
# Persistence integrity
# ==================================================================


class TestPersistenceIntegrity:
    def test_file_exists_after_upsert(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo = ProductRepository(layout)
        repo.upsert_product(_product())
        assert layout.products_file(STORE_A).exists()

    def test_json_is_valid(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo = ProductRepository(layout)
        repo.upsert_product(_product())
        content = layout.products_file(STORE_A).read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_deterministic_order(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo = ProductRepository(layout)
        repo.upsert_product(_product(internal_code="003", raw_name_sample="C"))
        repo.upsert_product(_product(internal_code="001", raw_name_sample="A"))
        repo.upsert_product(_product(internal_code="002", raw_name_sample="B"))
        content = layout.products_file(STORE_A).read_text(encoding="utf-8")
        data = json.loads(content)
        codes = [entry["internal_code"] for entry in data]
        assert codes == ["001", "002", "003"]

    def test_directory_created(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo = ProductRepository(layout)
        repo.upsert_product(_product())
        assert layout.store_dir(STORE_A).is_dir()

    def test_json_ends_with_newline(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo = ProductRepository(layout)
        repo.upsert_product(_product())
        content = layout.products_file(STORE_A).read_text(encoding="utf-8")
        assert content.endswith("\n")


# ==================================================================
# Reload from disk
# ==================================================================


class TestReloadFromDisk:
    def test_get_after_reload(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo1 = ProductRepository(layout)
        repo1.upsert_product(_product())
        repo2 = ProductRepository(layout)
        found = repo2.get_product(STORE_A, "001")
        assert found is not None
        assert found.raw_name_sample == "Produto A"

    def test_list_after_reload(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo1 = ProductRepository(layout)
        repo1.upsert_product(_product(internal_code="001"))
        repo1.upsert_product(_product(internal_code="002", raw_name_sample="B"))
        repo2 = ProductRepository(layout)
        products = repo2.list_products(STORE_A)
        assert len(products) == 2

    def test_count_after_reload(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        repo1 = ProductRepository(layout)
        repo1.upsert_product(_product())
        repo2 = ProductRepository(layout)
        assert repo2.count_products(STORE_A) == 1

    def test_upsert_from_items_after_reload(self, tmp_path: Path) -> None:
        layout = _layout(tmp_path)
        cat_id = uuid.uuid4()
        repo1 = ProductRepository(layout)
        repo1.upsert_product(
            _product(internal_code="001", category_id=cat_id)
        )
        repo2 = ProductRepository(layout)
        items = [_item(internal_code="001", raw_name="Atualizado")]
        products = repo2.upsert_from_items(STORE_A, items)
        assert products[0].raw_name_sample == "Atualizado"
        assert products[0].category_id == cat_id
