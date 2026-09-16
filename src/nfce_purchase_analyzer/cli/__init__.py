"""Command-line entry points for the NFC-e analyzer."""

from nfce_purchase_analyzer.cli.import_cmd import (
    handle_import_command,
    register_import_subcommand,
)
from nfce_purchase_analyzer.cli.parse import (
    build_parser,
    main,
    parse_pdf,
    render_parse_report,
)
from nfce_purchase_analyzer.cli.report_cmd import (
    handle_report_command,
    register_report_subcommand,
    render_report,
)

__all__ = [
    "build_parser",
    "handle_import_command",
    "handle_report_command",
    "main",
    "parse_pdf",
    "register_import_subcommand",
    "register_report_subcommand",
    "render_parse_report",
    "render_report",
]