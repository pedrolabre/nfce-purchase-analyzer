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
from nfce_purchase_analyzer.analysis.csv_export import (
    export_analysis_summary_csv,
    export_historical_price_variation_csv,
)

__all__ = [
    "AnalysisSelectionError",
    "HistoricalPriceVariationEntry",
    "HistoricalPriceVariationResult",
    "InsufficientPurchasesError",
    "MixedStoreSelectionError",
    "PurchaseAnalysisSelection",
    "PurchaseAnalysisSummary",
    "export_analysis_summary_csv",
    "export_historical_price_variation_csv",
    "calculate_historical_price_variation",
    "select_purchases_for_analysis",
    "summarize_selected_purchases",
]