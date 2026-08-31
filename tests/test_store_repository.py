"""Tests for the StoreRepository."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nfce_purchase_analyzer.persistence.paths import StorageLayout
from nfce_purchase_analyzer.persistence.stores import StoreRepository
from nfce_purchase_analyzer.persistence.schemas import read_json


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def layout(tmp_path: Path) -> StorageLayout:
    """Return a StorageLayout rooted in a temporary directory."""
    return StorageLayout(tmp_path)


@pytest.fixture()
def repo(layout: StorageLayout) -> StoreRepository:
    """Return a StoreRepository backed by a temporary directory."""
    return StoreRepository(layout)


# ------------------------------------------------------------------
# Empty repository
# ------------------------------------------------------------------


class TestEmptyRepository:
    """A fresh repository without any stores."""

    def test_list_stores_empty(self, repo: StoreRepository) -> None:
        assert repo.list_stores() == []

    def test_get_store_by_id_returns_none(self, repo: StoreRepository) -> None:
        import uuid

        assert repo.get_store_by_id(uuid.uuid4()) is None

    def test_get_store_by_code_returns_none(self, repo: StoreRepository) -> None:
        assert repo.get_store_by_code("0001") is None


# ------------------------------------------------------------------
# Single store creation
# ------------------------------------------------------------------


class TestCreateSingleStore:
    """Creating the first store in a repository."""

    def test_returns_store_with_code_0001(self, repo: StoreRepository) -> None:
        store = repo.create_store("Bem Maior")
        assert store.code == "0001"

    def test_returns_store_with_given_name(self, repo: StoreRepository) -> None:
        store = repo.create_store("Bem Maior")
        assert store.name == "Bem Maior"

    def test_store_has_uuid_id(self, repo: StoreRepository) -> None:
        import uuid

        store = repo.create_store("Bem Maior")
        assert isinstance(store.id, uuid.UUID)

    def test_store_appears_in_list(self, repo: StoreRepository) -> None:
        store = repo.create_store("Bem Maior")
        stores = repo.list_stores()
        assert len(stores) == 1
        assert stores[0].id == store.id

    def test_store_found_by_id(self, repo: StoreRepository) -> None:
        store = repo.create_store("Bem Maior")
        found = repo.get_store_by_id(store.id)
        assert found is not None
        assert found.id == store.id
        assert found.name == "Bem Maior"

    def test_store_found_by_code(self, repo: StoreRepository) -> None:
        store = repo.create_store("Bem Maior")
        found = repo.get_store_by_code("0001")
        assert found is not None
        assert found.id == store.id

    def test_store_not_found_by_wrong_code(self, repo: StoreRepository) -> None:
        repo.create_store("Bem Maior")
        assert repo.get_store_by_code("9999") is None


# ------------------------------------------------------------------
# Multiple store creation
# ------------------------------------------------------------------


class TestCreateMultipleStores:
    """Creating several stores produces sequential codes."""

    def test_sequential_codes(self, repo: StoreRepository) -> None:
        s1 = repo.create_store("Loja A")
        s2 = repo.create_store("Loja B")
        s3 = repo.create_store("Loja C")
        assert s1.code == "0001"
        assert s2.code == "0002"
        assert s3.code == "0003"

    def test_list_ordered_by_code(self, repo: StoreRepository) -> None:
        repo.create_store("Loja C")
        repo.create_store("Loja A")
        repo.create_store("Loja B")
        stores = repo.list_stores()
        codes = [s.code for s in stores]
        assert codes == ["0001", "0002", "0003"]

    def test_each_store_has_unique_id(self, repo: StoreRepository) -> None:
        s1 = repo.create_store("Loja A")
        s2 = repo.create_store("Loja B")
        s3 = repo.create_store("Loja C")
        ids = {s1.id, s2.id, s3.id}
        assert len(ids) == 3


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


class TestValidation:
    """Name validation on store creation."""

    def test_empty_name_rejected(self, repo: StoreRepository) -> None:
        with pytest.raises(ValueError, match="name"):
            repo.create_store("")

    def test_whitespace_only_name_rejected(self, repo: StoreRepository) -> None:
        with pytest.raises(ValueError, match="name"):
            repo.create_store("   ")

    def test_constructor_rejects_non_layout(self) -> None:
        with pytest.raises(TypeError, match="layout"):
            StoreRepository("not a layout")  # type: ignore[arg-type]


# ------------------------------------------------------------------
# Persistence integrity
# ------------------------------------------------------------------


class TestPersistenceIntegrity:
    """Verify files on disk match the repository state."""

    def test_stores_json_written(
        self, repo: StoreRepository, layout: StorageLayout
    ) -> None:
        repo.create_store("Bem Maior")
        index_path = layout.stores_index()
        assert index_path.exists()
        data = read_json(index_path)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["code"] == "0001"
        assert data[0]["name"] == "Bem Maior"

    def test_store_json_written(
        self, repo: StoreRepository, layout: StorageLayout
    ) -> None:
        store = repo.create_store("Bem Maior")
        store_file = layout.store_file(store.id)
        assert store_file.exists()
        data = read_json(store_file)
        assert data["code"] == "0001"
        assert data["name"] == "Bem Maior"

    def test_index_and_detail_match(
        self, repo: StoreRepository, layout: StorageLayout
    ) -> None:
        store = repo.create_store("Bem Maior")
        index_data = read_json(layout.stores_index())
        detail_data = read_json(layout.store_file(store.id))
        assert index_data[0] == detail_data

    def test_store_dirs_created(
        self, repo: StoreRepository, layout: StorageLayout
    ) -> None:
        store = repo.create_store("Bem Maior")
        assert layout.store_dir(store.id).is_dir()
        assert layout.purchases_dir(store.id).is_dir()

    def test_multiple_stores_in_index(
        self, repo: StoreRepository, layout: StorageLayout
    ) -> None:
        repo.create_store("Loja A")
        repo.create_store("Loja B")
        data = read_json(layout.stores_index())
        assert len(data) == 2

    def test_json_deterministic_format(
        self, repo: StoreRepository, layout: StorageLayout
    ) -> None:
        repo.create_store("Bem Maior")
        content = layout.stores_index().read_text(encoding="utf-8")
        # Trailing newline
        assert content.endswith("\n")
        # Sorted keys
        parsed = json.loads(content)
        assert list(parsed[0].keys()) == sorted(parsed[0].keys())


# ------------------------------------------------------------------
# Code continuity after reload
# ------------------------------------------------------------------


class TestCodeContinuity:
    """Codes remain stable and sequential across repository instances."""

    def test_new_repo_instance_continues_codes(
        self, layout: StorageLayout
    ) -> None:
        repo1 = StoreRepository(layout)
        repo1.create_store("Loja A")
        repo1.create_store("Loja B")

        # Create a fresh repository instance over the same layout.
        repo2 = StoreRepository(layout)
        s3 = repo2.create_store("Loja C")
        assert s3.code == "0003"

    def test_list_stores_after_reload(self, layout: StorageLayout) -> None:
        repo1 = StoreRepository(layout)
        repo1.create_store("Loja A")

        repo2 = StoreRepository(layout)
        stores = repo2.list_stores()
        assert len(stores) == 1
        assert stores[0].name == "Loja A"

    def test_lookup_after_reload(self, layout: StorageLayout) -> None:
        repo1 = StoreRepository(layout)
        store = repo1.create_store("Loja A")

        repo2 = StoreRepository(layout)
        found = repo2.get_store_by_id(store.id)
        assert found is not None
        assert found.id == store.id
        assert found.code == "0001"
