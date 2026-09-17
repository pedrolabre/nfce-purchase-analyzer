"""Home screen widget displaying registered stores."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from nfce_purchase_analyzer.domain.models import Store
from nfce_purchase_analyzer.persistence.stores import StoreRepository
from nfce_purchase_analyzer.ui.new_store_dialog import NewStoreDialog


class HomeScreen(QWidget):
    """Initial screen listing all registered stores.

    Provides a *Nova Loja* button that opens a :class:`NewStoreDialog`
    and a list of store cards.  Selecting a store emits
    :pyqtSignal:`store_selected` carrying the chosen :class:`Store`.
    """

    store_selected = Signal(object)
    """Emitted when the user double-clicks or activates a store item."""

    def __init__(self, store_repo: StoreRepository, parent=None):
        super().__init__(parent)
        if not isinstance(store_repo, StoreRepository):
            raise TypeError("store_repo must be a StoreRepository")

        self._store_repo = store_repo
        self._stores: list[Store] = []

        self._setup_ui()
        self.refresh_stores()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header row: title + "Nova Loja" button.
        header = QHBoxLayout()
        title = QLabel("Lojas Cadastradas")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self._new_store_button = QPushButton("Nova Loja")
        self._new_store_button.clicked.connect(self._on_new_store)
        header.addWidget(self._new_store_button)
        layout.addLayout(header)

        # Store list.
        self._store_list = QListWidget()
        self._store_list.itemDoubleClicked.connect(self._on_item_activated)
        self._store_list.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self._store_list)

        # Empty-state label (shown when no stores exist).
        self._empty_label = QLabel(
            "Nenhuma loja cadastrada.\nClique em \"Nova Loja\" para começar."
        )
        self._empty_label.setAlignment(
            self._empty_label.alignment()
        )
        self._empty_label.setStyleSheet("color: gray; padding: 20px;")
        layout.addWidget(self._empty_label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh_stores(self) -> None:
        """Reload the store list from the repository."""
        self._stores = self._store_repo.list_stores()
        self._store_list.clear()

        for store in self._stores:
            item = QListWidgetItem(f"[{store.code}] {store.name}")
            item.setData(256, store)  # Qt.UserRole == 256
            self._store_list.addItem(item)

        has_stores = len(self._stores) > 0
        self._store_list.setVisible(has_stores)
        self._empty_label.setVisible(not has_stores)

    @property
    def store_list_widget(self) -> QListWidget:
        """Return the internal list widget (for testing)."""
        return self._store_list

    @property
    def new_store_button(self) -> QPushButton:
        """Return the 'Nova Loja' button (for testing)."""
        return self._new_store_button

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_new_store(self) -> None:
        """Open the new-store dialog and create a store on acceptance."""
        dialog = NewStoreDialog(self)
        if dialog.exec() == NewStoreDialog.DialogCode.Accepted:
            name = dialog.store_name
            if name:
                self._store_repo.create_store(name)
                self.refresh_stores()

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        """Emit store_selected when a list item is activated."""
        store = item.data(256)  # Qt.UserRole
        if store is not None:
            self.store_selected.emit(store)


__all__ = [
    "HomeScreen",
]
