"""Tests for the CLI ``report`` subcommand.

Each test builds synthetic store/purchase data via the persistence
layer in ``tmp_path`` and invokes the report command directly.
"""

from __future__ import annotations

import argparse
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from nfce_purchase_analyzer.cli import main
from nfce_purchase_analyzer.cli.report_cmd import handle_report_command
from nfce_purchase_analyzer.domain.models import (
    Product,
    Purchase,
    PurchaseItem,
    Store,
)
from nfce_purchase_analyzer.persistence import (
    ProductRepository,
    PurchaseRepository,
    StorageLayout,
    StoreRepository,
)
from nfce_purchase_analyzer.persistence.schemas import (
    store_to_dict,
    write_json,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_STORE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _setup_store(data_dir: Path) -> Store:
    """Create a single store in the data directory."""
    layout = StorageLayout(data_dir)
    store = Store(id=_STORE_ID, code="0001", name="Loja Teste")

    layout.ensure_store_dirs(store.id)
    write_json(layout.store_file(store.id), store_to_dict(store))
    write_json(layout.stores_index(), [store_to_dict(store)])

    return store


def _add_purchase(
    data_dir: Path,
    *,
    purchase_id: uuid.UUID,
    date: datetime,
    total_value: str,
    items: list[dict],
    source_pdf: str,
) -> None:
    """Add a purchase with items to the store."""
    layout = StorageLayout(data_dir)
    repo = PurchaseRepository(layout)

    purchase = Purchase(
        id=purchase_id,
        store_id=_STORE_ID,
        date=date,
        total_value=Decimal(total_value),
        total_items=len(items),
        source_pdf=source_pdf,
    )

    purchase_items = []
    for item in items:
        purchase_items.append(
            PurchaseItem(
                purchase_id=purchase_id,
                store_id=_STORE_ID,
                internal_code=item["code"],
                raw_name=item["name"],
                quantity=Decimal(item.get("quantity", "1")),
                unit_price=Decimal(item["unit_price"]),
                total_price=Decimal(item["total_price"]),
            )
        )

    repo.save_purchase(purchase, purchase_items)

    # Also register products implicitly.
    product_repo = ProductRepository(layout)
    product_repo.upsert_from_items(_STORE_ID, purchase_items)


def _setup_two_purchases(data_dir: Path) -> None:
    """Create a store with two purchases for a valid report."""
    _setup_store(data_dir)

    _add_purchase(
        data_dir,
        purchase_id=uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001"),
        date=datetime(2026, 7, 10, 9, 0, 0),
        total_value="50.00",
        items=[
            {"code": "000042", "name": "CAFE TORRADO 500G",
             "unit_price": "15.90", "total_price": "15.90"},
            {"code": "000088", "name": "ARROZ BRANCO 5KG",
             "unit_price": "22.50", "total_price": "22.50"},
            {"code": "000101", "name": "OLEO SOJA 900ML",
             "unit_price": "11.60", "total_price": "11.60"},
        ],
        source_pdf="nota_001.pdf",
    )

    _add_purchase(
        data_dir,
        purchase_id=uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002"),
        date=datetime(2026, 8, 15, 14, 30, 0),
        total_value="55.00",
        items=[
            {"code": "000042", "name": "CAFE TORRADO 500G",
             "unit_price": "16.90", "total_price": "16.90"},
            {"code": "000088", "name": "ARROZ BRANCO 5KG",
             "unit_price": "23.50", "total_price": "23.50"},
            {"code": "000101", "name": "OLEO SOJA 900ML",
             "unit_price": "14.60", "total_price": "14.60"},
        ],
        source_pdf="nota_002.pdf",
    )


def _make_args(
    data_dir: Path,
    *,
    store_id: str | None = None,
    store_code: str | None = None,
) -> argparse.Namespace:
    """Create a minimal namespace mimicking argparse output."""
    return argparse.Namespace(
        data_dir=str(data_dir),
        store_id=store_id,
        store_code=store_code,
    )


# ------------------------------------------------------------------
# Happy path — report with 2+ purchases
# ------------------------------------------------------------------


def test_report_with_two_purchases(tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _setup_two_purchases(data_dir)

    args = _make_args(data_dir)
    exit_code = handle_report_command(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Loja Teste" in captured.out
    assert "Total acumulado" in captured.out
    assert "Distribuição por categoria" in captured.out
    assert "Variação histórica de preços" in captured.out
    assert "CAFE TORRADO" in captured.out


# ------------------------------------------------------------------
# Insufficient history — only 1 purchase
# ------------------------------------------------------------------


def test_report_insufficient_purchases(tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _setup_store(data_dir)

    _add_purchase(
        data_dir,
        purchase_id=uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001"),
        date=datetime(2026, 7, 10, 9, 0, 0),
        total_value="50.00",
        items=[
            {"code": "000042", "name": "CAFE TORRADO 500G",
             "unit_price": "15.90", "total_price": "15.90"},
            {"code": "000088", "name": "ARROZ BRANCO 5KG",
             "unit_price": "22.50", "total_price": "22.50"},
            {"code": "000101", "name": "OLEO SOJA 900ML",
             "unit_price": "11.60", "total_price": "11.60"},
        ],
        source_pdf="nota_001.pdf",
    )

    args = _make_args(data_dir)
    exit_code = handle_report_command(args)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "insuficiente" in captured.err.lower()
    assert "1 compra" in captured.err


# ------------------------------------------------------------------
# Store not found by ID
# ------------------------------------------------------------------


def test_report_store_not_found_by_id(tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _setup_store(data_dir)

    args = _make_args(
        data_dir,
        store_id="99999999-9999-9999-9999-999999999999",
    )
    exit_code = handle_report_command(args)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "não encontrada" in captured.err.lower()


# ------------------------------------------------------------------
# Store not found by code
# ------------------------------------------------------------------


def test_report_store_not_found_by_code(tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _setup_store(data_dir)

    args = _make_args(data_dir, store_code="9999")
    exit_code = handle_report_command(args)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "não encontrada" in captured.err.lower()
    assert "9999" in captured.err


# ------------------------------------------------------------------
# No stores at all
# ------------------------------------------------------------------


def test_report_no_stores(tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    args = _make_args(data_dir)
    exit_code = handle_report_command(args)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "nenhuma loja" in captured.err.lower()


# ------------------------------------------------------------------
# Auto-resolve with single store
# ------------------------------------------------------------------


def test_report_auto_resolve_single_store(tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _setup_two_purchases(data_dir)

    # No --store-id or --store-code — should auto-resolve.
    args = _make_args(data_dir)
    exit_code = handle_report_command(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Loja Teste" in captured.out


# ------------------------------------------------------------------
# Multiple stores without explicit selection
# ------------------------------------------------------------------


def test_report_multiple_stores_requires_selection(
    tmp_path: Path, capsys
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    layout = StorageLayout(data_dir)

    store1 = Store(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        code="0001",
        name="Loja A",
    )
    store2 = Store(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        code="0002",
        name="Loja B",
    )
    layout.ensure_store_dirs(store1.id)
    layout.ensure_store_dirs(store2.id)
    write_json(layout.store_file(store1.id), store_to_dict(store1))
    write_json(layout.store_file(store2.id), store_to_dict(store2))
    write_json(
        layout.stores_index(),
        [store_to_dict(store1), store_to_dict(store2)],
    )

    args = _make_args(data_dir)
    exit_code = handle_report_command(args)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "múltiplas lojas" in captured.err.lower()
    assert "--store-id" in captured.err or "--store-code" in captured.err


# ------------------------------------------------------------------
# Explicit --store-code selection
# ------------------------------------------------------------------


def test_report_explicit_store_code(tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _setup_two_purchases(data_dir)

    args = _make_args(data_dir, store_code="0001")
    exit_code = handle_report_command(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Loja Teste" in captured.out


# ------------------------------------------------------------------
# Explicit --store-id selection
# ------------------------------------------------------------------


def test_report_explicit_store_id(tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _setup_two_purchases(data_dir)

    args = _make_args(data_dir, store_id=str(_STORE_ID))
    exit_code = handle_report_command(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Loja Teste" in captured.out


# ------------------------------------------------------------------
# Subcommand wired into CLI main
# ------------------------------------------------------------------


def test_report_subcommand_accessible_via_main(
    tmp_path: Path, capsys
) -> None:
    """Verify the ``report`` subcommand is registered in ``build_parser``."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _setup_two_purchases(data_dir)

    exit_code = main([
        "report",
        "--data-dir",
        str(data_dir),
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Loja Teste" in captured.out


# ------------------------------------------------------------------
# Zero purchases — no data at all for the store
# ------------------------------------------------------------------


def test_report_zero_purchases(tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _setup_store(data_dir)

    args = _make_args(data_dir)
    exit_code = handle_report_command(args)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "insuficiente" in captured.err.lower()
    assert "0 compras" in captured.err
