"""Main window shell for the NFC-e Purchase Analyzer desktop application."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QStatusBar


class MainWindow(QMainWindow):
    """Primary application window with stacked navigation."""

    _WINDOW_TITLE = "NFC-e Purchase Analyzer"
    _MIN_WIDTH = 800
    _MIN_HEIGHT = 600

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self._WINDOW_TITLE)
        self.setMinimumSize(self._MIN_WIDTH, self._MIN_HEIGHT)

        # Central stacked widget for future screen navigation.
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Status bar for transient messages.
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Pronto.", 0)

    @property
    def stack(self) -> QStackedWidget:
        """Return the central stacked widget used for navigation."""
        return self._stack

    def show_status_message(self, message: str, timeout_ms: int = 5000) -> None:
        """Display a transient message in the status bar.

        Args:
            message: Text to display.
            timeout_ms: Duration in milliseconds. 0 means permanent.
        """
        self._status_bar.showMessage(message, timeout_ms)
