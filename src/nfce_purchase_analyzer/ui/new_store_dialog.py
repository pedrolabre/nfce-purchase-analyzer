"""Dialog for creating a new store."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class NewStoreDialog(QDialog):
    """Modal dialog that collects a store name for creation.

    The dialog provides a single text field for the store name.
    The *Create* button is disabled when the name field is empty or
    contains only whitespace.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nova Loja")
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Label and input field.
        self._label = QLabel("Nome da loja:")
        layout.addWidget(self._label)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Ex: Supermercado Bem Maior")
        self._name_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._name_edit)

        # Dialog buttons.
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_button = self._buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )
        self._ok_button.setText("Criar")
        self._ok_button.setEnabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._name_edit.setFocus()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def store_name(self) -> str:
        """Return the trimmed store name entered by the user."""
        return self._name_edit.text().strip()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_text_changed(self, text: str) -> None:
        """Enable the OK button only when the name is non-empty."""
        self._ok_button.setEnabled(bool(text.strip()))


__all__ = [
    "NewStoreDialog",
]
