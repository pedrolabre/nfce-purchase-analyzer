"""Application factory and desktop entry point for the NFC-e Purchase Analyzer."""

from __future__ import annotations

import sys
from typing import Sequence

from PySide6.QtWidgets import QApplication

from nfce_purchase_analyzer.ui.main_window import MainWindow


def create_app(
    argv: Sequence[str] | None = None,
) -> tuple[QApplication, MainWindow]:
    """Create the QApplication and MainWindow instances.

    If a ``QApplication`` already exists (e.g. in tests), it is reused
    instead of creating a new one.

    Args:
        argv: Command-line arguments forwarded to ``QApplication``.
              Defaults to ``sys.argv`` when *None*.

    Returns:
        A ``(app, window)`` tuple ready for display and event-loop execution.
    """
    if argv is None:
        argv = sys.argv

    app = QApplication.instance()
    if app is None:
        app = QApplication(list(argv))

    window = MainWindow()
    return app, window


def main() -> int:
    """Desktop entry point: create, show and run the application.

    Returns:
        Process exit code from the Qt event loop.
    """
    app, window = create_app()
    window.show()
    return app.exec()
