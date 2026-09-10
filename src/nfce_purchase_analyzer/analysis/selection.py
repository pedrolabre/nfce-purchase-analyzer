"""Contracts for selecting purchases for historical analysis."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import uuid

from nfce_purchase_analyzer.domain.models import (
    Purchase,
    StoreBoundaryError,
    ensure_same_store,
)


class AnalysisSelectionError(ValueError):
    """Raised when the analysis selection does not meet business rules."""


class InsufficientPurchasesError(AnalysisSelectionError):
    """Raised when fewer than two purchases are selected."""


class MixedStoreSelectionError(AnalysisSelectionError):
    """Raised when selected purchases belong to different stores."""


def _purchases(value: Iterable[Purchase], field_name: str) -> tuple[Purchase, ...]:
    try:
        purchases = tuple(value)
    except TypeError as exc:
        raise TypeError(f"{field_name} must be an iterable of Purchase") from exc

    if len(purchases) < 2:
        raise InsufficientPurchasesError(
            f"{field_name} must contain at least two purchases"
        )

    for purchase in purchases:
        if not isinstance(purchase, Purchase):
            raise TypeError(f"{field_name} must contain only Purchase instances")

    return purchases


@dataclass(frozen=True, slots=True)
class PurchaseAnalysisSelection:
    """Validated selection of purchases for store-bound historical analysis."""

    purchases: tuple[Purchase, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "purchases", _purchases(self.purchases, "purchases"))

        try:
            ensure_same_store(*self.purchases)
        except StoreBoundaryError as exc:
            raise MixedStoreSelectionError(
                "selected purchases must belong to the same store"
            ) from exc

    @property
    def store_id(self) -> uuid.UUID:
        return self.purchases[0].store_id

    @property
    def purchase_count(self) -> int:
        return len(self.purchases)

    @classmethod
    def from_purchases(
        cls,
        purchases: Iterable[Purchase],
    ) -> PurchaseAnalysisSelection:
        return cls(tuple(purchases))


def select_purchases_for_analysis(
    purchases: Iterable[Purchase],
) -> PurchaseAnalysisSelection:
    """Build a validated analysis selection from raw purchase objects."""

    return PurchaseAnalysisSelection.from_purchases(purchases)


__all__ = [
    "AnalysisSelectionError",
    "InsufficientPurchasesError",
    "MixedStoreSelectionError",
    "PurchaseAnalysisSelection",
    "select_purchases_for_analysis",
]