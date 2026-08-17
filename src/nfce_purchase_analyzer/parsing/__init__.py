"""Parsing contracts and layout parsers for the NFC-e analyzer."""

from nfce_purchase_analyzer.parsing.bem_maior import (
    BEM_MAIOR_STORE_ID,
    BemMaiorParser,
)
from nfce_purchase_analyzer.parsing.contracts import (
    DiagnosticLevel,
    NfceParser,
    ParseDiagnostic,
    ParseResult,
    ParserLayout,
    ParserRegistry,
)
from nfce_purchase_analyzer.parsing.validation import validate_purchase_total

__all__ = [
    "BEM_MAIOR_STORE_ID",
    "BemMaiorParser",
    "DiagnosticLevel",
    "NfceParser",
    "ParseDiagnostic",
    "ParseResult",
    "ParserLayout",
    "ParserRegistry",
    "validate_purchase_total",
]
