"""Desktop UI package for the NFC-e Purchase Analyzer."""

from nfce_purchase_analyzer.ui.app import create_app, main
from nfce_purchase_analyzer.ui.main_window import MainWindow

__all__ = [
    "MainWindow",
    "create_app",
    "main",
]
