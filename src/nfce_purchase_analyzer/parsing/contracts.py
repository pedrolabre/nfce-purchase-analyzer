"""Contracts for NFC-e parser by layout."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import Protocol

from nfce_purchase_analyzer.domain import PendingPurchaseImport


@unique
class ParserLayout(Enum):
    """Known NFC-e PDF layouts.

    Each member identifies a specific visual layout produced by a
    store's fiscal printer or electronic invoice system.  Parsers
    register themselves under exactly one layout value.
    """

    BEM_MAIOR = "bem_maior"


@unique
class DiagnosticLevel(Enum):
    """Severity of a parse diagnostic."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ParseDiagnostic:
    """A single structured diagnostic emitted during parsing.

    Attributes:
        level: Severity of the diagnostic.
        code: Machine-readable identifier (e.g. ``"missing_date"``).
        message: Human-readable description of the issue.
    """

    level: DiagnosticLevel
    code: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.level, DiagnosticLevel):
            raise TypeError("level must be a DiagnosticLevel")
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("code must be a non-empty string")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be a non-empty string")
        object.__setattr__(self, "code", self.code.strip())
        object.__setattr__(self, "message", self.message.strip())


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Outcome of parsing an NFC-e document.

    A successful parse populates ``pending_import`` with the extracted
    data.  A failed parse sets ``pending_import`` to ``None`` and
    provides at least one error-level diagnostic.

    In both cases ``diagnostics`` may contain warnings about
    non-critical issues found during extraction.

    Attributes:
        pending_import: Extracted data ready for review, or ``None``
            if parsing failed.
        diagnostics: Ordered sequence of diagnostics emitted during
            parsing, possibly empty on a clean success.
        layout: The parser layout that produced this result.
    """

    pending_import: PendingPurchaseImport | None
    diagnostics: tuple[ParseDiagnostic, ...]
    layout: ParserLayout

    def __post_init__(self) -> None:
        if self.pending_import is not None and not isinstance(
            self.pending_import, PendingPurchaseImport
        ):
            raise TypeError(
                "pending_import must be a PendingPurchaseImport or None"
            )
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be a tuple of ParseDiagnostic")
        for diag in self.diagnostics:
            if not isinstance(diag, ParseDiagnostic):
                raise TypeError(
                    "diagnostics must contain only ParseDiagnostic instances"
                )
        if not isinstance(self.layout, ParserLayout):
            raise TypeError("layout must be a ParserLayout")

    @property
    def ok(self) -> bool:
        """Return ``True`` when parsing produced usable data."""
        return self.pending_import is not None

    @property
    def errors(self) -> tuple[ParseDiagnostic, ...]:
        """Return only error-level diagnostics."""
        return tuple(
            d for d in self.diagnostics if d.level == DiagnosticLevel.ERROR
        )

    @property
    def warnings(self) -> tuple[ParseDiagnostic, ...]:
        """Return only warning-level diagnostics."""
        return tuple(
            d for d in self.diagnostics if d.level == DiagnosticLevel.WARNING
        )


class NfceParser(Protocol):
    """Protocol that every layout-specific NFC-e parser must satisfy.

    Implementations receive raw text lines extracted from a PDF and
    return a ``ParseResult``.  They must **not** read files, access
    the network, or write to disk.
    """

    @property
    def layout(self) -> ParserLayout:
        """The layout this parser handles."""
        ...

    def parse(self, text_lines: list[str], *, source_pdf: str) -> ParseResult:
        """Parse NFC-e text lines into a ``ParseResult``.

        Args:
            text_lines: Ordered lines of text extracted from the PDF.
            source_pdf: Path or identifier of the source PDF file,
                carried through to the resulting ``PendingPurchaseImport``.

        Returns:
            A ``ParseResult`` with extracted data or error diagnostics.
        """
        ...


class ParserRegistry:
    """Registry for selecting parsers by layout.

    Parsers are registered explicitly.  There is no dynamic discovery.
    """

    def __init__(self) -> None:
        self._parsers: dict[ParserLayout, NfceParser] = {}

    def register(self, parser: NfceParser) -> None:
        """Register a parser for its declared layout.

        Raises:
            TypeError: If *parser* does not expose a ``layout`` attribute
                that is a ``ParserLayout``.
            ValueError: If a parser is already registered for the same
                layout.
        """
        if not isinstance(getattr(parser, "layout", None), ParserLayout):
            raise TypeError(
                "parser must expose a 'layout' attribute of type ParserLayout"
            )
        if parser.layout in self._parsers:
            raise ValueError(
                f"a parser is already registered for layout {parser.layout.value!r}"
            )
        self._parsers[parser.layout] = parser

    def get(self, layout: ParserLayout) -> NfceParser | None:
        """Return the parser registered for *layout*, or ``None``."""
        return self._parsers.get(layout)

    @property
    def available_layouts(self) -> tuple[ParserLayout, ...]:
        """Return layouts for which a parser is registered."""
        return tuple(sorted(self._parsers, key=lambda l: l.value))

    def __len__(self) -> int:
        return len(self._parsers)

    def __contains__(self, layout: ParserLayout) -> bool:
        return layout in self._parsers


__all__ = [
    "DiagnosticLevel",
    "NfceParser",
    "ParseDiagnostic",
    "ParseResult",
    "ParserLayout",
    "ParserRegistry",
]
