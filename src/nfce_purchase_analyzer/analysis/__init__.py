"""Analysis contracts for comparing purchases within one store."""

from nfce_purchase_analyzer.analysis.selection import (
    AnalysisSelectionError,
    InsufficientPurchasesError,
    MixedStoreSelectionError,
    PurchaseAnalysisSelection,
    select_purchases_for_analysis,
)
from nfce_purchase_analyzer.analysis.summary import (
    PurchaseAnalysisSummary,
    summarize_selected_purchases,
)

__all__ = [
    "AnalysisSelectionError",
    "InsufficientPurchasesError",
    "MixedStoreSelectionError",
    "PurchaseAnalysisSelection",
    "PurchaseAnalysisSummary",
    "select_purchases_for_analysis",
    "summarize_selected_purchases",
]