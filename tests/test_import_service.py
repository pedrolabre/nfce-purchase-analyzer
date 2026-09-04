"""Tests for the import confirmation service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from nfce_purchase_analyzer.domain.models import (
    PendingPurchaseImport,
    PendingPurchaseItem,
    Purchase,
    PurchaseItem,
)
from nfce_purchase_analyzer.persistence import (
    DuplicateImportError,
    ImportResult,
    StorageLayout,
    confirm_import,
)
from nfce_purchase_analyzer.persistence.products import ProductRepository
from nfce_purchase_analyzer.persistence.purchases import PurchaseRepository


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

STORE_ID = uuid.uuid4()


def _make_pending_item(
    *,
    store_id: uuid.UUID = STORE_ID,
    internal_code: str = "001",
    raw_name: str = "Arroz 5kg",
    quantity: Decimal = Decimal("1"),
    unit_price: Decimal = Decimal("25.90"),
    total_price: Decimal = Decimal("25.90"),
) -> PendingPurchaseItem:
    return PendingPurchaseItem(
        store_id=store_id,
        internal_code=internal_code,
        raw_name=raw_name,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
    )


def _make_pending_import(
    *,
    store_id: uuid.UUID = STORE_ID,
    source_pdf: str = "nota_001.pdf",
    items: tuple[PendingPurchaseItem, ...] | None = None,
) -> PendingPurchaseImport:
    if items is None:
        items = (
            _make_pending_item(store_id=store_id, internal_code="001"),
            _make_pending_item(
                store_id=store_id,
                internal_code="002",
                raw_name="Feijao 1kg",
                unit_price=Decimal("8.50"),
                total_price=Decimal("8.50"),
            ),
        )
    total_value = sum(item.total_price for item in items)
    return PendingPurchaseImport(
        store_id=store_id,
        date=datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
        total_value=total_value,
        source_pdf=source_pdf,
        items=items,
    )


# ------------------------------------------------------------------
# Tests: Basic confirmation flow
# ------------------------------------------------------------------


class TestConfirmImportBasic:
    """Test the basic happy-path of confirm_import."""

    def test_returns_import_result(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert isinstance(result, ImportResult)

    def test_result_contains_purchase(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert isinstance(result.purchase, Purchase)

    def test_purchase_has_correct_store_id(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert result.purchase.store_id == STORE_ID

    def test_purchase_has_correct_date(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert result.purchase.date == pending.date

    def test_purchase_has_correct_total_value(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert result.purchase.total_value == pending.total_value

    def test_purchase_has_correct_total_items(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert result.purchase.total_items == pending.total_items

    def test_purchase_has_correct_source_pdf(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert result.purchase.source_pdf == pending.source_pdf

    def test_purchase_has_generated_uuid(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert isinstance(result.purchase.id, uuid.UUID)

    def test_result_contains_items(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert len(result.items) == 2

    def test_items_have_purchase_id(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        for item in result.items:
            assert item.purchase_id == result.purchase.id

    def test_items_preserve_data(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        codes = {item.internal_code for item in result.items}
        assert codes == {"001", "002"}

    def test_result_contains_products(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert len(result.products) == 2


# ------------------------------------------------------------------
# Tests: Persistence verification
# ------------------------------------------------------------------


class TestConfirmImportPersistence:
    """Verify that confirm_import actually writes to disk."""

    def test_purchase_is_persisted(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        repo = PurchaseRepository(layout)
        loaded = repo.get_purchase(STORE_ID, result.purchase.id)
        assert loaded is not None

    def test_persisted_purchase_matches(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        repo = PurchaseRepository(layout)
        purchase, items = repo.get_purchase(STORE_ID, result.purchase.id)
        assert purchase.total_value == pending.total_value
        assert len(items) == 2

    def test_products_are_persisted(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        confirm_import(pending, layout)
        repo = ProductRepository(layout)
        products = repo.list_products(STORE_ID)
        assert len(products) == 2

    def test_product_has_correct_name(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        confirm_import(pending, layout)
        repo = ProductRepository(layout)
        product = repo.get_product(STORE_ID, "001")
        assert product is not None
        assert product.raw_name_sample == "Arroz 5kg"

    def test_product_has_no_category(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        confirm_import(pending, layout)
        repo = ProductRepository(layout)
        product = repo.get_product(STORE_ID, "001")
        assert product.category_id is None

    def test_purchase_count_after_import(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        confirm_import(pending, layout)
        repo = PurchaseRepository(layout)
        assert repo.count_purchases(STORE_ID) == 1


# ------------------------------------------------------------------
# Tests: Preview does not persist
# ------------------------------------------------------------------


class TestPreviewDoesNotPersist:
    """Ensure that generating a preview never touches disk."""

    def test_preview_does_not_write(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        # Generate preview — this must NOT write anything.
        _preview = pending.preview
        repo = PurchaseRepository(layout)
        assert repo.count_purchases(STORE_ID) == 0

    def test_preview_does_not_create_products(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        _preview = pending.preview
        repo = ProductRepository(layout)
        assert repo.count_products(STORE_ID) == 0


# ------------------------------------------------------------------
# Tests: Duplicate detection
# ------------------------------------------------------------------


class TestDuplicateDetection:
    """Test that re-importing the same source_pdf is rejected."""

    def test_duplicate_source_pdf_raises(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import(source_pdf="nota_dup.pdf")
        confirm_import(pending, layout)
        with pytest.raises(DuplicateImportError):
            confirm_import(pending, layout)

    def test_duplicate_message_contains_filename(
        self, tmp_path: Path
    ) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import(source_pdf="nota_dup.pdf")
        confirm_import(pending, layout)
        with pytest.raises(DuplicateImportError, match="nota_dup.pdf"):
            confirm_import(pending, layout)

    def test_different_source_pdf_allowed(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending1 = _make_pending_import(source_pdf="nota_a.pdf")
        pending2 = _make_pending_import(source_pdf="nota_b.pdf")
        confirm_import(pending1, layout)
        result2 = confirm_import(pending2, layout)
        assert result2.purchase.source_pdf == "nota_b.pdf"

    def test_same_pdf_different_store_allowed(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        store_a = uuid.uuid4()
        store_b = uuid.uuid4()
        pending_a = _make_pending_import(
            store_id=store_a,
            source_pdf="nota_shared.pdf",
            items=(
                _make_pending_item(store_id=store_a),
            ),
        )
        pending_b = _make_pending_import(
            store_id=store_b,
            source_pdf="nota_shared.pdf",
            items=(
                _make_pending_item(store_id=store_b),
            ),
        )
        confirm_import(pending_a, layout)
        result_b = confirm_import(pending_b, layout)
        assert result_b.purchase.source_pdf == "nota_shared.pdf"

    def test_no_data_persisted_on_duplicate_rejection(
        self, tmp_path: Path
    ) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import(source_pdf="nota_x.pdf")
        confirm_import(pending, layout)
        repo = PurchaseRepository(layout)
        count_before = repo.count_purchases(STORE_ID)
        with pytest.raises(DuplicateImportError):
            confirm_import(pending, layout)
        assert repo.count_purchases(STORE_ID) == count_before


# ------------------------------------------------------------------
# Tests: Multiple imports
# ------------------------------------------------------------------


class TestMultipleImports:
    """Test multiple successive imports."""

    def test_two_imports_create_two_purchases(
        self, tmp_path: Path
    ) -> None:
        layout = StorageLayout(tmp_path)
        pending1 = _make_pending_import(source_pdf="nota_1.pdf")
        pending2 = _make_pending_import(source_pdf="nota_2.pdf")
        confirm_import(pending1, layout)
        confirm_import(pending2, layout)
        repo = PurchaseRepository(layout)
        assert repo.count_purchases(STORE_ID) == 2

    def test_product_upsert_across_imports(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending1 = _make_pending_import(source_pdf="nota_1.pdf")
        pending2 = _make_pending_import(
            source_pdf="nota_2.pdf",
            items=(
                _make_pending_item(
                    internal_code="001",
                    raw_name="Arroz Integral 5kg",
                ),
            ),
        )
        confirm_import(pending1, layout)
        confirm_import(pending2, layout)
        repo = ProductRepository(layout)
        product = repo.get_product(STORE_ID, "001")
        # The last import should update the raw_name_sample.
        assert product.raw_name_sample == "Arroz Integral 5kg"

    def test_product_count_with_overlapping_items(
        self, tmp_path: Path
    ) -> None:
        layout = StorageLayout(tmp_path)
        pending1 = _make_pending_import(source_pdf="nota_1.pdf")
        pending2 = _make_pending_import(
            source_pdf="nota_2.pdf",
            items=(
                _make_pending_item(internal_code="001"),
                _make_pending_item(
                    internal_code="003",
                    raw_name="Leite 1L",
                    unit_price=Decimal("6.50"),
                    total_price=Decimal("6.50"),
                ),
            ),
        )
        confirm_import(pending1, layout)
        confirm_import(pending2, layout)
        repo = ProductRepository(layout)
        # 001, 002 from first + 003 from second = 3 unique products.
        assert repo.count_products(STORE_ID) == 3

    def test_each_import_gets_unique_purchase_id(
        self, tmp_path: Path
    ) -> None:
        layout = StorageLayout(tmp_path)
        pending1 = _make_pending_import(source_pdf="nota_1.pdf")
        pending2 = _make_pending_import(source_pdf="nota_2.pdf")
        result1 = confirm_import(pending1, layout)
        result2 = confirm_import(pending2, layout)
        assert result1.purchase.id != result2.purchase.id


# ------------------------------------------------------------------
# Tests: Validation
# ------------------------------------------------------------------


class TestConfirmImportValidation:
    """Test type validation of confirm_import arguments."""

    def test_rejects_non_pending_import(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        with pytest.raises(TypeError, match="PendingPurchaseImport"):
            confirm_import("not a pending import", layout)

    def test_rejects_non_storage_layout(self) -> None:
        pending = _make_pending_import()
        with pytest.raises(TypeError, match="StorageLayout"):
            confirm_import(pending, "not a layout")


# ------------------------------------------------------------------
# Tests: Store boundary
# ------------------------------------------------------------------


class TestStoreBoundary:
    """Verify store isolation in import confirmation."""

    def test_imports_isolated_by_store(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        store_a = uuid.uuid4()
        store_b = uuid.uuid4()

        pending_a = _make_pending_import(
            store_id=store_a,
            source_pdf="nota_a.pdf",
            items=(_make_pending_item(store_id=store_a),),
        )
        pending_b = _make_pending_import(
            store_id=store_b,
            source_pdf="nota_b.pdf",
            items=(_make_pending_item(store_id=store_b),),
        )

        confirm_import(pending_a, layout)
        confirm_import(pending_b, layout)

        repo = PurchaseRepository(layout)
        assert repo.count_purchases(store_a) == 1
        assert repo.count_purchases(store_b) == 1

    def test_products_isolated_by_store(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        store_a = uuid.uuid4()
        store_b = uuid.uuid4()

        pending_a = _make_pending_import(
            store_id=store_a,
            source_pdf="nota_a.pdf",
            items=(
                _make_pending_item(store_id=store_a, internal_code="001"),
                _make_pending_item(store_id=store_a, internal_code="002"),
            ),
        )
        pending_b = _make_pending_import(
            store_id=store_b,
            source_pdf="nota_b.pdf",
            items=(
                _make_pending_item(store_id=store_b, internal_code="001"),
            ),
        )

        confirm_import(pending_a, layout)
        confirm_import(pending_b, layout)

        repo = ProductRepository(layout)
        assert repo.count_products(store_a) == 2
        assert repo.count_products(store_b) == 1


# ------------------------------------------------------------------
# Tests: ImportResult frozen
# ------------------------------------------------------------------


class TestImportResultFrozen:
    """Verify ImportResult is immutable."""

    def test_import_result_is_frozen(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        with pytest.raises(AttributeError):
            result.purchase = None  # type: ignore[misc]

    def test_items_is_tuple(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert isinstance(result.items, tuple)

    def test_products_is_tuple(self, tmp_path: Path) -> None:
        layout = StorageLayout(tmp_path)
        pending = _make_pending_import()
        result = confirm_import(pending, layout)
        assert isinstance(result.products, tuple)
