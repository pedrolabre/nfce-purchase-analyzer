"""Diagnostic CLI for parsing a local NFC-e PDF and printing a summary."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from nfce_purchase_analyzer.parsing import BemMaiorParser, ParseResult
from nfce_purchase_analyzer.parsing.pdf_reader import (
    PdfReadError,
    extract_text_from_pdf,
)


def _flatten_pages(pages: list[str]) -> list[str]:
    lines: list[str] = []
    for page in pages:
        lines.extend(page.splitlines())
    return lines


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "N/D"
    return value.strftime("%d/%m/%Y %H:%M:%S")


def _format_money(value: Decimal | None) -> str:
    if value is None:
        return "N/D"
    return f"R$ {value:.2f}".replace(".", ",")


def parse_pdf(pdf_path: str | Path) -> ParseResult:
    path = Path(pdf_path)
    pages = extract_text_from_pdf(path)
    text_lines = _flatten_pages(pages)
    parser = BemMaiorParser()
    direct_result = parser.parse(text_lines, source_pdf=str(path))
    if direct_result.ok:
        return direct_result

    reversed_result = parser.parse(list(reversed(text_lines)), source_pdf=str(path))
    if reversed_result.ok:
        return reversed_result

    return direct_result


def render_parse_report(result: ParseResult, *, source_pdf: str) -> str:
    lines: list[str] = [f"Arquivo: {source_pdf}"]
    pending = result.pending_import

    if pending is None:
        lines.extend([
            "Data da nota: N/D",
            "Total geral: N/D",
            "Quantidade de itens: N/D",
        ])
    else:
        lines.extend([
            f"Data da nota: {_format_datetime(pending.date)}",
            f"Total geral: {_format_money(pending.total_value)}",
            f"Quantidade de itens: {pending.total_items}",
        ])

    lines.append(f"Diagnósticos ({len(result.diagnostics)}):")
    if result.diagnostics:
        for diagnostic in result.diagnostics:
            lines.append(
                f"- {diagnostic.level.value} {diagnostic.code}: {diagnostic.message}"
            )
    else:
        lines.append("- nenhum")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nfce-purchase-analyzer",
        description="Ferramenta local de diagnóstico para parse de NFC-e em PDF.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_parser = subparsers.add_parser(
        "parse",
        help="Ler um PDF local de NFC-e e imprimir um resumo da extração.",
    )
    parse_parser.add_argument(
        "pdf_path",
        help="Caminho local para o PDF da NFC-e.",
    )
    parse_parser.set_defaults(handler=_handle_parse_command)

    from nfce_purchase_analyzer.cli.import_cmd import register_import_subcommand
    register_import_subcommand(subparsers)

    from nfce_purchase_analyzer.cli.report_cmd import register_report_subcommand
    register_report_subcommand(subparsers)

    return parser


def _handle_parse_command(args: argparse.Namespace) -> int:
    pdf_path = Path(args.pdf_path)

    try:
        result = parse_pdf(pdf_path)
    except PdfReadError as exc:
        print(f"Erro ao ler PDF ({exc.reason}): {exc}", file=sys.stderr)
        return 1

    print(render_parse_report(result, source_pdf=str(pdf_path)))
    return 0 if result.pending_import is not None else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.error("nenhum comando informado")
    return handler(args)


__all__ = [
    "build_parser",
    "main",
    "parse_pdf",
    "render_parse_report",
]