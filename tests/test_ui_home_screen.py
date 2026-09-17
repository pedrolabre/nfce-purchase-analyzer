"""Tests for the home screen and new-store dialog in offscreen mode."""

from __future__ import annotations

import os
import sys

import pytest

# Force offscreen rendering before any Qt import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QDialogButtonBox,
    QListWidget,
    QPushButton,
)

from nfce_purchase_analyzer.persistence.paths import StorageLayout  # noqa: E402
from nfce_purchase_analyzer.persistence.stores import StoreRepository  # noqa: E402
from nfce_purchase_analyzer.ui.home_screen import HomeScreen  # noqa: E402
from nfce_purchase_analyzer.ui.new_store_dialog import NewStoreDialog  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication for all UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture()
def store_repo(tmp_path):
    """Create a StoreRepository backed by a temporary directory."""
    layout = StorageLayout(tmp_path)
    return StoreRepository(layout)


@pytest.fixture()
def home(qapp, store_repo):
    """Create a fresh HomeScreen for each test."""
    screen = HomeScreen(store_repo)
    yield screen
    screen.close()


# --- NewStoreDialog tests ----------------------------------------------------


class TestNewStoreDialog:
    """Tests for the new-store creation dialog."""

    def test_dialog_is_modal(self, qapp):
        dialog = NewStoreDialog()
        try:
            assert dialog.isModal()
        finally:
            dialog.close()

    def test_dialog_title(self, qapp):
        dialog = NewStoreDialog()
        try:
            assert dialog.windowTitle() == "Nova Loja"
        finally:
            dialog.close()

    def test_ok_button_disabled_when_empty(self, qapp):
        dialog = NewStoreDialog()
        try:
            ok_btn = dialog._buttons.button(
                QDialogButtonBox.StandardButton.Ok
            )
            assert not ok_btn.isEnabled()
        finally:
            dialog.close()

    def test_ok_button_enabled_when_name_entered(self, qapp):
        dialog = NewStoreDialog()
        try:
            dialog._name_edit.setText("Mercado Teste")
            ok_btn = dialog._buttons.button(
                QDialogButtonBox.StandardButton.Ok
            )
            assert ok_btn.isEnabled()
        finally:
            dialog.close()

    def test_ok_button_disabled_for_whitespace_only(self, qapp):
        dialog = NewStoreDialog()
        try:
            dialog._name_edit.setText("   ")
            ok_btn = dialog._buttons.button(
                QDialogButtonBox.StandardButton.Ok
            )
            assert not ok_btn.isEnabled()
        finally:
            dialog.close()

    def test_store_name_property_trims_whitespace(self, qapp):
        dialog = NewStoreDialog()
        try:
            dialog._name_edit.setText("  Bem Maior  ")
            assert dialog.store_name == "Bem Maior"
        finally:
            dialog.close()

    def test_ok_button_re_disables_on_clear(self, qapp):
        dialog = NewStoreDialog()
        try:
            dialog._name_edit.setText("Teste")
            ok_btn = dialog._buttons.button(
                QDialogButtonBox.StandardButton.Ok
            )
            assert ok_btn.isEnabled()
            dialog._name_edit.clear()
            assert not ok_btn.isEnabled()
        finally:
            dialog.close()


# --- HomeScreen tests --------------------------------------------------------


class TestHomeScreenEmpty:
    """Tests for the home screen with no stores registered."""

    def test_store_list_is_empty(self, home):
        assert home.store_list_widget.count() == 0

    def test_empty_label_not_hidden(self, home):
        assert not home._empty_label.isHidden()

    def test_store_list_hidden(self, home):
        assert home.store_list_widget.isHidden()

    def test_new_store_button_exists(self, home):
        assert isinstance(home.new_store_button, QPushButton)
        assert home.new_store_button.text() == "Nova Loja"

    def test_rejects_non_store_repo(self, qapp):
        with pytest.raises(TypeError, match="StoreRepository"):
            HomeScreen("not a repo")


class TestHomeScreenWithStores:
    """Tests for the home screen with pre-existing stores."""

    def test_displays_single_store(self, qapp, store_repo):
        store_repo.create_store("Loja Alpha")
        screen = HomeScreen(store_repo)
        try:
            assert screen.store_list_widget.count() == 1
            item = screen.store_list_widget.item(0)
            assert "Loja Alpha" in item.text()
            assert "0001" in item.text()
        finally:
            screen.close()

    def test_displays_multiple_stores(self, qapp, store_repo):
        store_repo.create_store("Loja A")
        store_repo.create_store("Loja B")
        store_repo.create_store("Loja C")
        screen = HomeScreen(store_repo)
        try:
            assert screen.store_list_widget.count() == 3
        finally:
            screen.close()

    def test_store_list_not_hidden_when_stores_exist(self, qapp, store_repo):
        store_repo.create_store("Mercado Teste")
        screen = HomeScreen(store_repo)
        try:
            assert not screen.store_list_widget.isHidden()
            assert screen._empty_label.isHidden()
        finally:
            screen.close()

    def test_store_data_attached_to_item(self, qapp, store_repo):
        created = store_repo.create_store("Mercado X")
        screen = HomeScreen(store_repo)
        try:
            item = screen.store_list_widget.item(0)
            attached_store = item.data(256)  # Qt.UserRole
            assert attached_store.id == created.id
            assert attached_store.name == "Mercado X"
            assert attached_store.code == "0001"
        finally:
            screen.close()

    def test_sequential_codes_displayed(self, qapp, store_repo):
        store_repo.create_store("Loja 1")
        store_repo.create_store("Loja 2")
        screen = HomeScreen(store_repo)
        try:
            item0 = screen.store_list_widget.item(0)
            item1 = screen.store_list_widget.item(1)
            assert "0001" in item0.text()
            assert "0002" in item1.text()
        finally:
            screen.close()


class TestHomeScreenRefresh:
    """Tests for the refresh_stores method."""

    def test_refresh_updates_list(self, qapp, store_repo):
        screen = HomeScreen(store_repo)
        try:
            assert screen.store_list_widget.count() == 0
            store_repo.create_store("Nova Loja Adicionada")
            screen.refresh_stores()
            assert screen.store_list_widget.count() == 1
        finally:
            screen.close()

    def test_refresh_reflects_new_stores(self, qapp, store_repo):
        store_repo.create_store("Loja Existente")
        screen = HomeScreen(store_repo)
        try:
            assert screen.store_list_widget.count() == 1
            store_repo.create_store("Loja Nova")
            screen.refresh_stores()
            assert screen.store_list_widget.count() == 2
        finally:
            screen.close()


class TestHomeScreenSelection:
    """Tests for store selection signal."""

    def test_store_selected_signal_on_activation(self, qapp, store_repo):
        created = store_repo.create_store("Selecionável")
        screen = HomeScreen(store_repo)
        received = []
        screen.store_selected.connect(lambda s: received.append(s))
        try:
            item = screen.store_list_widget.item(0)
            # Simulate item activation (Enter key / double-click).
            screen._on_item_activated(item)
            assert len(received) == 1
            assert received[0].id == created.id
            assert received[0].name == "Selecionável"
        finally:
            screen.close()


# --- MainWindow integration --------------------------------------------------


class TestMainWindowHomeScreen:
    """Tests for home screen integration in MainWindow."""

    def test_main_window_without_repo_has_no_home_screen(self, qapp):
        from nfce_purchase_analyzer.ui.main_window import MainWindow

        win = MainWindow()
        try:
            assert win.home_screen is None
            assert win.stack.count() == 0
        finally:
            win.close()

    def test_main_window_with_repo_has_home_screen(self, qapp, store_repo):
        from nfce_purchase_analyzer.ui.main_window import MainWindow

        win = MainWindow(store_repo=store_repo)
        try:
            assert win.home_screen is not None
            assert isinstance(win.home_screen, HomeScreen)
            assert win.stack.count() == 1
            assert win.stack.currentWidget() is win.home_screen
        finally:
            win.close()

    def test_create_app_wires_home_screen(self, qapp, tmp_path):
        from nfce_purchase_analyzer.ui.app import create_app

        app, win = create_app(argv=[], data_dir=tmp_path)
        try:
            assert win.home_screen is not None
            assert isinstance(win.home_screen, HomeScreen)
        finally:
            win.close()
