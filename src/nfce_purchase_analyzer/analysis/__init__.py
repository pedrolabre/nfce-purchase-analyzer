"""Analysis contracts for comparing purchases within one store."""

from nfce_purchase_analyzer.analysis.selection import (
    AnalysisSelectionError,
    InsufficientPurchasesError,
    MixedStoreSelectionError,
    PurchaseAnalysisSelection,
    select_purchases_for_analysis,
)
from nfce_purchase_analyzer.analysis.historical_variation import (
    HistoricalPriceVariationEntry,
    HistoricalPriceVariationResult,
    calculate_historical_price_variation,
)
from nfce_purchase_analyzer.analysis.summary import (
    PurchaseAnalysisSummary,
    summarize_selected_purchases,
)

__all__ = [
    "AnalysisSelectionError",
    "HistoricalPriceVariationEntry",
    "HistoricalPriceVariationResult",
    "InsufficientPurchasesError",
    "MixedStoreSelectionError",
    "PurchaseAnalysisSelection",
    "PurchaseAnalysisSummary",
    "calculate_historical_price_variation",
    "select_purchases_for_analysis",
    "summarize_selected_purchases",
]