"""Command-line entry points for the NFC-e analyzer."""

from nfce_purchase_analyzer.cli.parse import (
    build_parser,
    main,
    parse_pdf,
    render_parse_report,
)

__all__ = [
    "build_parser",
    "main",
    "parse_pdf",
    "render_parse_report",
]