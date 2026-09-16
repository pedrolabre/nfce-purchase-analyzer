"""Diagnostic CLI for importing an NFC-e PDF with explicit confirmation.

This module exposes the ``import`` subcommand.  The flow is:

1. Parse the PDF using the same logic as the ``parse`` command.
2. Print a human-readable preview of the extraction.
3. Ask the user for explicit textual confirmation (``sim``).
4. Only after confirmation, persist the data via :func:`confirm_import`.

Without confirmation **no data is written to disk**.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nfce_purchase_analyzer.cli.parse import parse_pdf, render_parse_report
from nfce_purchase_analyzer.parsing import BEM_MAIOR_STORE_ID
from nfce_purchase_analyzer.parsing.pdf_reader import PdfReadError
from nfce_purchase_analyzer.persistence import (
    DuplicateImportError,
    StorageLayout,
    StoreRepository,
    confirm_import,
)


_CONFIRMATION_TOKEN = "sim"


def _ensure_store(layout: StorageLayout) -> str:
    """Ensure the Bem Maior store exists and return its name.

    Creates the store on first use so the user does not need a
    separate store-creation step before importing.
    """
    store_repo = StoreRepository(layout)
    store = store_repo.get_store_by_id(BEM_MAIOR_STORE_ID)
    if store is not None:
        return store.name

    # First import — create the canonical Bem Maior store.
    from nfce_purchase_analyzer.domain.models import Store

    store = Store(id=BEM_MAIOR_STORE_ID, code="0001", name="Bem Maior")
    from nfce_purchase_analyzer.persistence.schemas import (
        store_to_dict,
        write_json,
    )

    layout.ensure_store_dirs(store.id)
    write_json(layout.store_file(store.id), store_to_dict(store))

    # Update the global index.
    from nfce_purchase_analyzer.persistence.schemas import read_json

    index_path = layout.stores_index()
    entries: list[dict] = []
    if index_path.exists():
        entries = read_json(index_path)
    entries.append(store_to_dict(store))
    write_json(index_path, entries)

    return store.name


def handle_import_command(
    args: argparse.Namespace,
    *,
    input_fn: object = None,
) -> int:
    """Execute the import flow with explicit confirmation.

    Parameters
    ----------
    args:
        Parsed CLI arguments containing ``pdf_path`` and ``data_dir``.
    input_fn:
        Callable used to read confirmation from the user.  Defaults to
        the built-in :func:`input`.  Accepting this parameter makes the
        function testable without monkey-patching.

    Returns
    -------
    int
        Exit code: ``0`` on successful import, ``1`` on error or
        cancellation.
    """
    if input_fn is None:
        input_fn = input

    pdf_path = Path(args.pdf_path)
    data_dir = Path(args.data_dir).resolve()

    # 1. Parse the PDF -------------------------------------------------
    try:
        result = parse_pdf(pdf_path)
    except PdfReadError as exc:
        print(f"Erro ao ler PDF ({exc.reason}): {exc}", file=sys.stderr)
        return 1

    # 2. Print preview -------------------------------------------------
    print(render_parse_report(result, source_pdf=str(pdf_path)))

    if not result.ok:
        print("\nParse falhou. Importação cancelada.", file=sys.stderr)
        return 1

    # 3. Ask for confirmation ------------------------------------------
    answer = input_fn("\nConfirmar importação? (sim/nao): ")
    if answer.strip().lower() != _CONFIRMATION_TOKEN:
        print("Importação cancelada pelo usuário.")
        return 1

    # 4. Persist -------------------------------------------------------
    layout = StorageLayout(data_dir)
    _ensure_store(layout)

    pending = result.pending_import
    assert pending is not None  # guarded by result.ok above

    try:
        import_result = confirm_import(pending, layout)
    except DuplicateImportError as exc:
        print(f"Importação duplicada: {exc}", file=sys.stderr)
        return 1

    print(
        f"\nImportação confirmada. Compra {import_result.purchase.id} "
        f"gravada com {len(import_result.items)} itens."
    )
    return 0


def register_import_subcommand(
    subparsers: argparse._SubParsersAction,
) -> None:
    """Register the ``import`` subcommand on *subparsers*."""
    import_parser = subparsers.add_parser(
        "import",
        help=(
            "Importar um PDF local de NFC-e após confirmação textual "
            "e persistir os dados localmente."
        ),
    )
    import_parser.add_argument(
        "pdf_path",
        help="Caminho local para o PDF da NFC-e.",
    )
    import_parser.add_argument(
        "--data-dir",
        default=".",
        help="Diretório raiz para armazenamento local (padrão: diretório atual).",
    )
    import_parser.set_defaults(handler=handle_import_command)


__all__ = [
    "handle_import_command",
    "register_import_subcommand",
]
