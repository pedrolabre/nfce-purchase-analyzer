"""Desktop UI package for the NFC-e Purchase Analyzer."""

from nfce_purchase_analyzer.ui.app import create_app, main
from nfce_purchase_analyzer.ui.home_screen import HomeScreen
from nfce_purchase_analyzer.ui.main_window import MainWindow
from nfce_purchase_analyzer.ui.new_store_dialog import NewStoreDialog

__all__ = [
    "HomeScreen",
    "MainWindow",
    "NewStoreDialog",
    "create_app",
    "main",
]
