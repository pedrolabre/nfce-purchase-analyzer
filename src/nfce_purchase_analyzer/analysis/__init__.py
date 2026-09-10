"""Analysis contracts for comparing purchases within one store."""

from nfce_purchase_analyzer.analysis.selection import (
    AnalysisSelectionError,
    InsufficientPurchasesError,
    MixedStoreSelectionError,
    PurchaseAnalysisSelection,
    select_purchases_for_analysis,
)

__all__ = [
    "AnalysisSelectionError",
    "InsufficientPurchasesError",
    "MixedStoreSelectionError",
    "PurchaseAnalysisSelection",
    "select_purchases_for_analysis",
]