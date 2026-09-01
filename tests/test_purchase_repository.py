"""Tests for the PurchaseRepository."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from nfce_purchase_analyzer.domain.models import (
    Purchase,
    PurchaseItem,
    StoreBoundaryError,
)
from nfce_purchase_analyzer.persistence.paths import StorageLayout
from nfce_purchase_analyzer.persistence.purchases import PurchaseRepository
from nfce_purchase_analyzer.persistence.schemas import read_json


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_STORE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
_STORE_ID_B = uuid.UUID("00000000-0000-4000-8000-000000000002")


def _make_purchase(
    store_id: uuid.UUID = _STORE_ID,
    purchase_id: uuid.UUID | None = None,
    date: datetime | None = None,
    total_value: Decimal | str = "29.90",
    total_items: int = 2,
    source_pdf: str = "nota_001.pdf",
) -> Purchase:
    return Purchase(
        id=purchase_id or uuid.uuid4(),
        store_id=store_id,
        date=date or datetime(2026, 1, 15, 10, 30, 0),
        total_value=total_value,
        total_items=total_items,
        source_pdf=source_pdf,
    )


def _make_item(
    purchase_id: uuid.UUID,
    store_id: uuid.UUID = _STORE_ID,
    internal_code: str = "12345",
    raw_name: str = "Arroz Branco 5kg",
    quantity: Decimal | str = "1.000",
    unit_price: Decimal | str = "19.90",
    total_price: Decimal | str = "19.90",
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


def _make_purchase_with_items(
    store_id: uuid.UUID = _STORE_ID,
    purchase_id: uuid.UUID | None = None,
    date: datetime | None = None,
) -> tuple[Purchase, list[PurchaseItem]]:
    pid = purchase_id or uuid.uuid4()
    purchase = _make_purchase(
        store_id=store_id,
        purchase_id=pid,
        date=date,
        total_value="29.90",
        total_items=2,
    )
    items = [
        _make_item(
            purchase_id=pid,
            store_id=store_id,
            internal_code="12345",
            raw_name="Arroz Branco 5kg",
            quantity="1.000",
            unit_price="19.90",
            total_price="19.90",
        ),
        _make_item(
            purchase_id=pid,
            store_id=store_id,
            internal_code="67890",
            raw_name="Feijao Preto 1kg",
            quantity="2.000",
            unit_price="5.00",
            total_price="10.00",
        ),
    ]
    return purchase, items


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def layout(tmp_path: Path) -> StorageLayout:
    """Return a StorageLayout rooted in a temporary directory."""
    return StorageLayout(tmp_path)


@pytest.fixture()
def repo(layout: StorageLayout) -> PurchaseRepository:
    """Return a PurchaseRepository backed by a temporary directory."""
    return PurchaseRepository(layout)


# ------------------------------------------------------------------
# Empty repository
# ------------------------------------------------------------------


class TestEmptyRepository:
    """A fresh repository without any purchases."""

    def test_get_purchase_returns_none(self, repo: PurchaseRepository) -> None:
        assert repo.get_purchase(_STORE_ID, uuid.uuid4()) is None

    def test_list_purchases_empty(self, repo: PurchaseRepository) -> None:
        assert repo.list_purchases(_STORE_ID) == []

    def test_count_purchases_zero(self, repo: PurchaseRepository) -> None:
        assert repo.count_purchases(_STORE_ID) == 0


# ------------------------------------------------------------------
# Save and retrieve a single purchase
# ------------------------------------------------------------------


class TestSavePurchase:
    """Saving a purchase and retrieving it back."""

    def test_save_and_get_returns_purchase(
        self, repo: PurchaseRepository
    ) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        loaded_purchase, loaded_items = result
        assert loaded_purchase.id == purchase.id
        assert loaded_purchase.store_id == purchase.store_id

    def test_save_and_get_returns_correct_item_count(
        self, repo: PurchaseRepository
    ) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        _, loaded_items = result
        assert len(loaded_items) == 2

    def test_count_after_save(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)
        assert repo.count_purchases(_STORE_ID) == 1

    def test_list_after_save(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)
        results = repo.list_purchases(_STORE_ID)
        assert len(results) == 1
        assert results[0][0].id == purchase.id


# ------------------------------------------------------------------
# Purchase metadata preservation
# ------------------------------------------------------------------


class TestPurchaseMetadata:
    """Verify preservation of fiscal metadata across save/load."""

    def test_date_preserved(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        assert result[0].date == purchase.date

    def test_total_value_preserved(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        assert result[0].total_value == purchase.total_value

    def test_total_items_preserved(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        assert result[0].total_items == purchase.total_items

    def test_source_pdf_preserved(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        assert result[0].source_pdf == purchase.source_pdf


# ------------------------------------------------------------------
# Item details preservation
# ------------------------------------------------------------------


class TestItemDetails:
    """Verify preservation of detailed item data across save/load."""

    def test_internal_code_preserved(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        loaded_items = result[1]
        codes = {item.internal_code for item in loaded_items}
        assert codes == {"12345", "67890"}

    def test_raw_name_preserved(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        loaded_items = result[1]
        names = {item.raw_name for item in loaded_items}
        assert names == {"Arroz Branco 5kg", "Feijao Preto 1kg"}

    def test_quantity_preserved(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        loaded_items = result[1]
        quantities = {item.quantity for item in loaded_items}
        assert Decimal("1.000") in quantities
        assert Decimal("2.000") in quantities

    def test_unit_price_preserved(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        loaded_items = result[1]
        prices = {item.unit_price for item in loaded_items}
        assert Decimal("19.90") in prices
        assert Decimal("5.00") in prices

    def test_total_price_preserved(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        loaded_items = result[1]
        totals = {item.total_price for item in loaded_items}
        assert Decimal("19.90") in totals
        assert Decimal("10.00") in totals

    def test_item_store_id_preserved(self, repo: PurchaseRepository) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        loaded_items = result[1]
        for item in loaded_items:
            assert item.store_id == _STORE_ID

    def test_item_purchase_id_preserved(
        self, repo: PurchaseRepository
    ) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        result = repo.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        loaded_items = result[1]
        for item in loaded_items:
            assert item.purchase_id == purchase.id


# ------------------------------------------------------------------
# Listing purchases ordered by date descending
# ------------------------------------------------------------------


class TestListPurchases:
    """Listing purchases for a store returns them ordered by date descending."""

    def test_multiple_purchases_ordered_by_date_descending(
        self, repo: PurchaseRepository
    ) -> None:
        p1, items1 = _make_purchase_with_items(
            date=datetime(2026, 1, 10, 10, 0, 0),
        )
        p2, items2 = _make_purchase_with_items(
            date=datetime(2026, 3, 20, 14, 30, 0),
        )
        p3, items3 = _make_purchase_with_items(
            date=datetime(2026, 2, 15, 9, 0, 0),
        )

        repo.save_purchase(p1, items1)
        repo.save_purchase(p2, items2)
        repo.save_purchase(p3, items3)

        results = repo.list_purchases(_STORE_ID)
        assert len(results) == 3
        dates = [r[0].date for r in results]
        assert dates == sorted(dates, reverse=True)

    def test_list_returns_items_with_each_purchase(
        self, repo: PurchaseRepository
    ) -> None:
        p1, items1 = _make_purchase_with_items(
            date=datetime(2026, 1, 10, 10, 0, 0),
        )
        repo.save_purchase(p1, items1)

        results = repo.list_purchases(_STORE_ID)
        assert len(results) == 1
        _, loaded_items = results[0]
        assert len(loaded_items) == 2

    def test_list_different_store_returns_empty(
        self, repo: PurchaseRepository
    ) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        # Different store has no purchases.
        assert repo.list_purchases(_STORE_ID_B) == []

    def test_count_different_store_returns_zero(
        self, repo: PurchaseRepository
    ) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)
        assert repo.count_purchases(_STORE_ID_B) == 0


# ------------------------------------------------------------------
# Store boundary validation
# ------------------------------------------------------------------


class TestStoreBoundary:
    """Reject purchases/items with mismatched store_id."""

    def test_item_with_different_store_id_rejected(
        self, repo: PurchaseRepository
    ) -> None:
        purchase = _make_purchase(store_id=_STORE_ID)
        bad_item = _make_item(
            purchase_id=purchase.id,
            store_id=_STORE_ID_B,
        )
        good_item = _make_item(
            purchase_id=purchase.id,
            store_id=_STORE_ID,
            internal_code="67890",
            raw_name="Feijao Preto 1kg",
            quantity="1.000",
            unit_price="10.00",
            total_price="10.00",
        )
        with pytest.raises(StoreBoundaryError):
            repo.save_purchase(purchase, [good_item, bad_item])

    def test_all_items_different_store_rejected(
        self, repo: PurchaseRepository
    ) -> None:
        purchase = _make_purchase(store_id=_STORE_ID)
        item = _make_item(
            purchase_id=purchase.id,
            store_id=_STORE_ID_B,
        )
        with pytest.raises(StoreBoundaryError):
            repo.save_purchase(purchase, [item])


# ------------------------------------------------------------------
# Purchase ID boundary validation
# ------------------------------------------------------------------


class TestPurchaseIdBoundary:
    """Reject items whose purchase_id doesn't match the purchase."""

    def test_item_with_wrong_purchase_id_rejected(
        self, repo: PurchaseRepository
    ) -> None:
        purchase = _make_purchase(store_id=_STORE_ID)
        wrong_pid = uuid.uuid4()
        item = _make_item(
            purchase_id=wrong_pid,
            store_id=_STORE_ID,
        )
        with pytest.raises(ValueError, match="purchase id"):
            repo.save_purchase(purchase, [item])


# ------------------------------------------------------------------
# Empty items validation
# ------------------------------------------------------------------


class TestEmptyItemsValidation:
    """Reject save with an empty items list."""

    def test_empty_items_rejected(self, repo: PurchaseRepository) -> None:
        purchase = _make_purchase(store_id=_STORE_ID)
        with pytest.raises(ValueError, match="items must not be empty"):
            repo.save_purchase(purchase, [])


# ------------------------------------------------------------------
# Persistence integrity
# ------------------------------------------------------------------


class TestPersistenceIntegrity:
    """Verify files on disk match the repository state."""

    def test_purchase_file_exists(
        self, repo: PurchaseRepository, layout: StorageLayout
    ) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        path = layout.purchase_file(purchase.store_id, purchase.id)
        assert path.exists()

    def test_purchase_file_contains_valid_json(
        self, repo: PurchaseRepository, layout: StorageLayout
    ) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        path = layout.purchase_file(purchase.store_id, purchase.id)
        data = read_json(path)
        assert isinstance(data, dict)
        assert "id" in data
        assert "items" in data

    def test_json_deterministic_format(
        self, repo: PurchaseRepository, layout: StorageLayout
    ) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        path = layout.purchase_file(purchase.store_id, purchase.id)
        content = path.read_text(encoding="utf-8")
        # Trailing newline
        assert content.endswith("\n")
        # Sorted keys
        parsed = json.loads(content)
        assert list(parsed.keys()) == sorted(parsed.keys())

    def test_purchases_dir_created(
        self, repo: PurchaseRepository, layout: StorageLayout
    ) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)
        assert layout.purchases_dir(purchase.store_id).is_dir()

    def test_overwrite_existing_purchase(
        self, repo: PurchaseRepository
    ) -> None:
        purchase, items = _make_purchase_with_items()
        repo.save_purchase(purchase, items)

        # Save again (overwrite).
        repo.save_purchase(purchase, items)
        assert repo.count_purchases(_STORE_ID) == 1


# ------------------------------------------------------------------
# Reload from fresh instance
# ------------------------------------------------------------------


class TestReloadFromDisk:
    """Data survives across repository instances."""

    def test_get_after_reload(self, layout: StorageLayout) -> None:
        repo1 = PurchaseRepository(layout)
        purchase, items = _make_purchase_with_items()
        repo1.save_purchase(purchase, items)

        repo2 = PurchaseRepository(layout)
        result = repo2.get_purchase(_STORE_ID, purchase.id)
        assert result is not None
        assert result[0].id == purchase.id

    def test_list_after_reload(self, layout: StorageLayout) -> None:
        repo1 = PurchaseRepository(layout)
        purchase, items = _make_purchase_with_items()
        repo1.save_purchase(purchase, items)

        repo2 = PurchaseRepository(layout)
        results = repo2.list_purchases(_STORE_ID)
        assert len(results) == 1

    def test_count_after_reload(self, layout: StorageLayout) -> None:
        repo1 = PurchaseRepository(layout)
        purchase, items = _make_purchase_with_items()
        repo1.save_purchase(purchase, items)

        repo2 = PurchaseRepository(layout)
        assert repo2.count_purchases(_STORE_ID) == 1


# ------------------------------------------------------------------
# Constructor validation
# ------------------------------------------------------------------


class TestValidation:
    """Constructor argument validation."""

    def test_constructor_rejects_non_layout(self) -> None:
        with pytest.raises(TypeError, match="layout"):
            PurchaseRepository("not a layout")  # type: ignore[arg-type]
