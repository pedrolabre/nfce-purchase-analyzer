"""Tests for the CLI ``import`` subcommand.

Each test injects a synthetic PDF via tmp_path and uses ``input_fn`` to
simulate user confirmation or cancellation without real stdin.
"""

from pathlib import Path

from nfce_purchase_analyzer.cli import main
from nfce_purchase_analyzer.cli.import_cmd import handle_import_command
from nfce_purchase_analyzer.parsing import BEM_MAIOR_STORE_ID
from nfce_purchase_analyzer.persistence import (
    PurchaseRepository,
    StorageLayout,
)

from fixtures import bem_maior_receipt_rounding_warning
from fixtures.pdf_builder import build_text_pdf


def _build_pdf(tmp_path: Path) -> Path:
    """Build a synthetic Bem Maior PDF in *tmp_path* and return its path."""
    lines, _meta = bem_maior_receipt_rounding_warning()
    pdf_path = tmp_path / "nota.pdf"
    pdf_path.write_bytes(build_text_pdf(lines))
    return pdf_path


def _make_args(pdf_path: Path, data_dir: Path):
    """Create a minimal namespace mimicking argparse output."""
    import argparse

    return argparse.Namespace(
        pdf_path=str(pdf_path),
        data_dir=str(data_dir),
    )


# ------------------------------------------------------------------
# Confirmation accepted → data is persisted
# ------------------------------------------------------------------


def test_import_confirmed_persists_data(tmp_path: Path, capsys) -> None:
    pdf_path = _build_pdf(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    args = _make_args(pdf_path, data_dir)
    exit_code = handle_import_command(args, input_fn=lambda _prompt: "sim")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Importação confirmada" in captured.out

    # Verify persistence
    layout = StorageLayout(data_dir)
    repo = PurchaseRepository(layout)
    purchases = repo.list_purchases(BEM_MAIOR_STORE_ID)
    assert len(purchases) == 1

    purchase, items = purchases[0]
    assert purchase.total_items == 1
    assert len(items) == 1


# ------------------------------------------------------------------
# Confirmation denied → no data written
# ------------------------------------------------------------------


def test_import_cancelled_does_not_write(tmp_path: Path, capsys) -> None:
    pdf_path = _build_pdf(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    args = _make_args(pdf_path, data_dir)
    exit_code = handle_import_command(args, input_fn=lambda _prompt: "nao")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "cancelada" in captured.out.lower()

    # No data should exist
    layout = StorageLayout(data_dir)
    repo = PurchaseRepository(layout)
    purchases = repo.list_purchases(BEM_MAIOR_STORE_ID)
    assert len(purchases) == 0


# ------------------------------------------------------------------
# Duplicate import → rejection
# ------------------------------------------------------------------


def test_import_duplicate_is_rejected(tmp_path: Path, capsys) -> None:
    pdf_path = _build_pdf(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    args = _make_args(pdf_path, data_dir)

    # First import succeeds
    exit_code_1 = handle_import_command(args, input_fn=lambda _prompt: "sim")
    assert exit_code_1 == 0

    # Second import of the same PDF is rejected
    exit_code_2 = handle_import_command(args, input_fn=lambda _prompt: "sim")
    captured = capsys.readouterr()
    assert exit_code_2 == 1
    assert "duplicada" in captured.err.lower()


# ------------------------------------------------------------------
# PDF read error → graceful failure
# ------------------------------------------------------------------


def test_import_missing_pdf_returns_error(tmp_path: Path, capsys) -> None:
    missing_pdf = tmp_path / "missing.pdf"
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    args = _make_args(missing_pdf, data_dir)
    exit_code = handle_import_command(args, input_fn=lambda _prompt: "sim")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "file_not_found" in captured.err


# ------------------------------------------------------------------
# Subcommand wired into CLI main
# ------------------------------------------------------------------


def test_import_subcommand_accessible_via_main(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    """Verify the ``import`` subcommand is registered in ``build_parser``."""
    pdf_path = _build_pdf(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Monkeypatch input to cancel so no side-effects occur.
    monkeypatch.setattr("builtins.input", lambda _prompt: "nao")

    exit_code = main([
        "import",
        str(pdf_path),
        "--data-dir",
        str(data_dir),
    ])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "cancelada" in captured.out.lower()


# ------------------------------------------------------------------
# Confirmation with leading/trailing whitespace and mixed case
# ------------------------------------------------------------------


def test_import_accepts_confirmation_with_whitespace(
    tmp_path: Path,
    capsys,
) -> None:
    pdf_path = _build_pdf(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    args = _make_args(pdf_path, data_dir)
    exit_code = handle_import_command(args, input_fn=lambda _prompt: "  SIM  ")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Importação confirmada" in captured.out
