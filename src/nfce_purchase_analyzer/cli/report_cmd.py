"""Diagnostic CLI for generating an analytical report from local data.

This module exposes the ``report`` subcommand.  The flow is:

1. Resolve which store to analyse (by id, code, or auto-detection).
2. Load all purchases for that store from local persistence.
3. Validate that the store has at least two purchases (analysis minimum).
4. Run the consolidated analysis engine (summary + historical variation).
5. Print a clean, human-readable report to stdout.

No data is written to disk — this command is strictly read-only.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

from nfce_purchase_analyzer.analysis import (
    calculate_historical_price_variation,
    select_purchases_for_analysis,
    summarize_selected_purchases,
)
from nfce_purchase_analyzer.domain.models import Store
from nfce_purchase_analyzer.persistence import (
    CategoryRepository,
    ProductRepository,
    PurchaseRepository,
    StorageLayout,
    StoreRepository,
)


# ------------------------------------------------------------------
# Store resolution
# ------------------------------------------------------------------


def _resolve_store(
    store_repo: StoreRepository,
    *,
    store_id: str | None,
    store_code: str | None,
) -> Store | None:
    """Resolve the target store from explicit arguments or auto-detect.

    Returns ``None`` when the store cannot be resolved (the caller is
    responsible for printing the appropriate diagnostic).
    """
    if store_id is not None:
        return store_repo.get_store_by_id(store_id)

    if store_code is not None:
        return store_repo.get_store_by_code(store_code)

    # Auto-resolve: only valid when exactly one store exists.
    stores = store_repo.list_stores()
    if len(stores) == 1:
        return stores[0]

    return None


def _resolve_store_diagnostic(
    store_repo: StoreRepository,
    *,
    store_id: str | None,
    store_code: str | None,
) -> str:
    """Return a user-friendly message explaining why the store was not found."""
    if store_id is not None:
        return f"Loja não encontrada para o ID: {store_id}"

    if store_code is not None:
        return f"Loja não encontrada para o código: {store_code}"

    stores = store_repo.list_stores()
    if not stores:
        return "Nenhuma loja cadastrada no diretório de dados informado."

    store_list = ", ".join(
        f"{s.name} (código {s.code})" for s in stores
    )
    return (
        f"Múltiplas lojas cadastradas: {store_list}. "
        "Especifique --store-id ou --store-code."
    )


# ------------------------------------------------------------------
# Report rendering
# ------------------------------------------------------------------

_MONEY_FMT = "R$ {value}"


def _fmt_money(value: Decimal) -> str:
    """Format a Decimal as Brazilian currency."""
    return f"R$ {value:.2f}".replace(".", ",")


def _fmt_pct(value: Decimal) -> str:
    """Format a Decimal as percentage."""
    return f"{value:+.2f}%".replace(".", ",")


def render_report(
    store: Store,
    summary,
    variation,
) -> str:
    """Build the full textual report as a single string."""
    lines: list[str] = []

    # -- Header -------------------------------------------------------
    lines.append("=" * 60)
    lines.append(f"  Relatório de Análise — {store.name} (código {store.code})")
    lines.append("=" * 60)
    lines.append("")

    # -- Summary -------------------------------------------------------
    lines.append(f"Total acumulado: {_fmt_money(summary.total_value)}")
    lines.append("")

    lines.append("Distribuição por categoria:")
    for category_name, value in summary.distribution.items():
        lines.append(f"  {category_name}: {_fmt_money(value)}")
    lines.append("")

    # -- Historical variation -----------------------------------------
    lines.append("Variação histórica de preços:")
    lines.append("-" * 60)

    if not variation.by_product:
        lines.append("  Nenhum dado de variação disponível.")
    else:
        for code, entries in variation.by_product.items():
            for entry in entries:
                var_label = _fmt_pct(entry.percentage_variation)
                abs_label = _fmt_money(entry.absolute_variation)
                lines.append(
                    f"  {entry.product_name} [{code}]: "
                    f"{_fmt_money(entry.previous_unit_price)} → "
                    f"{_fmt_money(entry.current_unit_price)} "
                    f"({abs_label}, {var_label})"
                )

    lines.append("-" * 60)
    return "\n".join(lines)


# ------------------------------------------------------------------
# Command handler
# ------------------------------------------------------------------


def handle_report_command(args: argparse.Namespace) -> int:
    """Execute the report flow.

    Parameters
    ----------
    args:
        Parsed CLI arguments containing ``data_dir`` and optionally
        ``store_id`` / ``store_code``.

    Returns
    -------
    int
        Exit code: ``0`` on success, ``1`` on error.
    """
    data_dir = Path(args.data_dir).resolve()
    layout = StorageLayout(data_dir)
    store_repo = StoreRepository(layout)

    store_id_arg: str | None = getattr(args, "store_id", None)
    store_code_arg: str | None = getattr(args, "store_code", None)

    # 1. Resolve store -------------------------------------------------
    store = _resolve_store(
        store_repo, store_id=store_id_arg, store_code=store_code_arg
    )
    if store is None:
        msg = _resolve_store_diagnostic(
            store_repo, store_id=store_id_arg, store_code=store_code_arg
        )
        print(msg, file=sys.stderr)
        return 1

    # 2. Load purchases ------------------------------------------------
    purchase_repo = PurchaseRepository(layout)
    purchase_pairs = purchase_repo.list_purchases(store.id)

    if len(purchase_pairs) < 2:
        count = len(purchase_pairs)
        noun = "compra" if count == 1 else "compras"
        print(
            f"Histórico insuficiente para análise: {count} {noun} "
            f"encontrada(s) para a loja {store.name} (código {store.code}). "
            f"Mínimo necessário: 2.",
            file=sys.stderr,
        )
        return 1

    # 3. Build analysis selection --------------------------------------
    purchases = [pair[0] for pair in purchase_pairs]
    all_items = []
    for _purchase, items in purchase_pairs:
        all_items.extend(items)

    selection = select_purchases_for_analysis(purchases)

    # 4. Load products and categories ----------------------------------
    product_repo = ProductRepository(layout)
    category_repo = CategoryRepository(layout)

    products = product_repo.list_products(store.id)
    categories = category_repo.list_categories(store.id)

    # 5. Run analysis --------------------------------------------------
    summary = summarize_selected_purchases(
        selection,
        items=all_items,
        products=products,
        categories=categories,
    )
    variation = calculate_historical_price_variation(
        selection,
        items=all_items,
        products=products,
        categories=categories,
    )

    # 6. Print report --------------------------------------------------
    print(render_report(store, summary, variation))
    return 0


# ------------------------------------------------------------------
# Subcommand registration
# ------------------------------------------------------------------


def register_report_subcommand(
    subparsers: argparse._SubParsersAction,
) -> None:
    """Register the ``report`` subcommand on *subparsers*."""
    report_parser = subparsers.add_parser(
        "report",
        help=(
            "Gerar relatório textual de análise a partir de compras "
            "locais persistidas de uma loja."
        ),
    )
    report_parser.add_argument(
        "--data-dir",
        default=".",
        help="Diretório raiz para armazenamento local (padrão: diretório atual).",
    )

    store_group = report_parser.add_mutually_exclusive_group()
    store_group.add_argument(
        "--store-id",
        default=None,
        help="UUID da loja alvo.",
    )
    store_group.add_argument(
        "--store-code",
        default=None,
        help="Código sequencial da loja alvo (ex: 0001).",
    )

    report_parser.set_defaults(handler=handle_report_command)


__all__ = [
    "handle_report_command",
    "register_report_subcommand",
    "render_report",
]
