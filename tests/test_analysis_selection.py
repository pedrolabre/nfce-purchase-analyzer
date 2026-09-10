"""Tests for selecting purchases for historical analysis."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from nfce_purchase_analyzer.analysis import (
    InsufficientPurchasesError,
    MixedStoreSelectionError,
    PurchaseAnalysisSelection,
    select_purchases_for_analysis,
)
from nfce_purchase_analyzer.domain.models import Purchase


STORE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
OTHER_STORE_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")


def _make_purchase(
    *,
    store_id: uuid.UUID = STORE_ID,
    purchase_id: uuid.UUID | None = None,
    source_pdf: str = "nota_001.pdf",
) -> Purchase:
    return Purchase(
        id=purchase_id or uuid.uuid4(),
        store_id=store_id,
        date=datetime(2026, 1, 15, 10, 30, 0),
        total_value="29.90",
        total_items=2,
        source_pdf=source_pdf,
    )


class TestPurchaseAnalysisSelection:
    """Validate the selection contract for historical analysis."""

    def test_selects_two_purchases_from_same_store(self) -> None:
        selection = select_purchases_for_analysis(
            [
                _make_purchase(source_pdf="nota_001.pdf"),
                _make_purchase(
                    purchase_id=uuid.uuid4(),
                    source_pdf="nota_002.pdf",
                ),
            ]
        )

        assert isinstance(selection, PurchaseAnalysisSelection)
        assert selection.purchase_count == 2
        assert selection.store_id == STORE_ID

    def test_rejects_single_purchase(self) -> None:
        with pytest.raises(InsufficientPurchasesError):
            select_purchases_for_analysis([
                _make_purchase(source_pdf="nota_001.pdf"),
            ])

    def test_rejects_mixed_stores(self) -> None:
        with pytest.raises(MixedStoreSelectionError):
            select_purchases_for_analysis(
                [
                    _make_purchase(source_pdf="nota_001.pdf"),
                    _make_purchase(
                        store_id=OTHER_STORE_ID,
                        purchase_id=uuid.uuid4(),
                        source_pdf="nota_002.pdf",
                    ),
                ]
            )