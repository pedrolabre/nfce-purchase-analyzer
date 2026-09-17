"""Tests for the PySide6 application shell (MainWindow) in offscreen mode."""

from __future__ import annotations

import os
import sys

import pytest

# Force offscreen rendering before any Qt import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QStackedWidget, QStatusBar  # noqa: E402

from nfce_purchase_analyzer.ui.app import create_app  # noqa: E402
from nfce_purchase_analyzer.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication for all UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture()
def window(qapp):
    """Create a fresh MainWindow for each test."""
    win = MainWindow()
    yield win
    win.close()


# --- MainWindow tests -------------------------------------------------------


class TestMainWindowCreation:
    """Tests for basic MainWindow instantiation and properties."""

    def test_window_is_created(self, window):
        assert isinstance(window, MainWindow)

    def test_window_title(self, window):
        assert window.windowTitle() == "NFC-e Purchase Analyzer"

    def test_minimum_width(self, window):
        assert window.minimumWidth() == 800

    def test_minimum_height(self, window):
        assert window.minimumHeight() == 600

    def test_central_widget_is_stacked(self, window):
        assert isinstance(window.centralWidget(), QStackedWidget)

    def test_stack_property(self, window):
        assert window.stack is window.centralWidget()

    def test_stack_starts_empty(self, window):
        assert window.stack.count() == 0

    def test_status_bar_exists(self, window):
        assert isinstance(window.statusBar(), QStatusBar)

    def test_initial_status_message(self, window):
        assert window.statusBar().currentMessage() == "Pronto."

    def test_show_status_message(self, window):
        window.show_status_message("Importando...", 0)
        assert window.statusBar().currentMessage() == "Importando..."


# --- create_app tests --------------------------------------------------------


class TestCreateApp:
    """Tests for the application factory."""

    def test_create_app_returns_tuple(self, qapp):
        app, win = create_app([])
        try:
            assert app is qapp
            assert isinstance(win, MainWindow)
        finally:
            win.close()

    def test_create_app_reuses_existing_qapp(self, qapp):
        app, win = create_app([])
        try:
            assert app is qapp
        finally:
            win.close()
