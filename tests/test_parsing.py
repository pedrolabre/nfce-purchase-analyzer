"""Tests for NFC-e parsing contracts."""

from datetime import datetime
from decimal import Decimal
import uuid

import pytest

from nfce_purchase_analyzer.domain import PendingPurchaseImport, PendingPurchaseItem
from nfce_purchase_analyzer.parsing import (
    DiagnosticLevel,
    NfceParser,
    ParseDiagnostic,
    ParseResult,
    ParserLayout,
    ParserRegistry,
)

STORE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _pending_item(
    *,
    store_id: uuid.UUID = STORE_ID,
    internal_code: str = "123",
) -> PendingPurchaseItem:
    return PendingPurchaseItem(
        store_id=store_id,
        internal_code=internal_code,
        raw_name="Cafe Torrado 500g",
        quantity=Decimal("1"),
        unit_price=Decimal("15.00"),
        total_price=Decimal("15.00"),
    )


def _pending_import(
    *,
    store_id: uuid.UUID = STORE_ID,
) -> PendingPurchaseImport:
    return PendingPurchaseImport(
        store_id=store_id,
        date=datetime(2026, 8, 16, 10, 0),
        total_value=Decimal("15.00"),
        source_pdf="notas/compra.pdf",
        items=(_pending_item(store_id=store_id),),
    )


# ---------------------------------------------------------------------------
# Fake parser for contract testing
# ---------------------------------------------------------------------------


class FakeParser:
    """Minimal parser that satisfies the ``NfceParser`` protocol."""

    def __init__(
        self,
        *,
        result: ParseResult | None = None,
        target_layout: ParserLayout = ParserLayout.BEM_MAIOR,
    ) -> None:
        self._layout = target_layout
        self._result = result

    @property
    def layout(self) -> ParserLayout:
        return self._layout

    def parse(self, text_lines: list[str], *, source_pdf: str) -> ParseResult:
        if self._result is not None:
            return self._result
        return ParseResult(
            pending_import=_pending_import(),
            diagnostics=(),
            layout=self._layout,
        )


# ---------------------------------------------------------------------------
# ParserLayout
# ---------------------------------------------------------------------------


def test_parser_layout_has_bem_maior() -> None:
    assert ParserLayout.BEM_MAIOR.value == "bem_maior"


# ---------------------------------------------------------------------------
# DiagnosticLevel
# ---------------------------------------------------------------------------


def test_diagnostic_level_values() -> None:
    assert DiagnosticLevel.WARNING.value == "warning"
    assert DiagnosticLevel.ERROR.value == "error"


# ---------------------------------------------------------------------------
# ParseDiagnostic
# ---------------------------------------------------------------------------


def test_parse_diagnostic_normalizes_fields() -> None:
    diag = ParseDiagnostic(
        level=DiagnosticLevel.WARNING,
        code=" missing_date ",
        message=" Data de emissao ausente ",
    )

    assert diag.level == DiagnosticLevel.WARNING
    assert diag.code == "missing_date"
    assert diag.message == "Data de emissao ausente"


def test_parse_diagnostic_rejects_invalid_level() -> None:
    with pytest.raises(TypeError):
        ParseDiagnostic(level="warning", code="x", message="m")


def test_parse_diagnostic_rejects_empty_code() -> None:
    with pytest.raises(ValueError, match="code"):
        ParseDiagnostic(level=DiagnosticLevel.ERROR, code=" ", message="msg")


def test_parse_diagnostic_rejects_empty_message() -> None:
    with pytest.raises(ValueError, match="message"):
        ParseDiagnostic(level=DiagnosticLevel.ERROR, code="err", message=" ")


# ---------------------------------------------------------------------------
# ParseResult
# ---------------------------------------------------------------------------


def test_parse_result_success_with_data() -> None:
    pending = _pending_import()
    result = ParseResult(
        pending_import=pending,
        diagnostics=(),
        layout=ParserLayout.BEM_MAIOR,
    )

    assert result.ok is True
    assert result.pending_import is pending
    assert result.diagnostics == ()
    assert result.errors == ()
    assert result.warnings == ()
    assert result.layout == ParserLayout.BEM_MAIOR


def test_parse_result_success_with_warnings() -> None:
    pending = _pending_import()
    warning = ParseDiagnostic(
        level=DiagnosticLevel.WARNING,
        code="rounding",
        message="Total difere por centavos",
    )
    result = ParseResult(
        pending_import=pending,
        diagnostics=(warning,),
        layout=ParserLayout.BEM_MAIOR,
    )

    assert result.ok is True
    assert result.warnings == (warning,)
    assert result.errors == ()


def test_parse_result_failure_with_errors() -> None:
    error = ParseDiagnostic(
        level=DiagnosticLevel.ERROR,
        code="no_items",
        message="Nenhum item encontrado",
    )
    result = ParseResult(
        pending_import=None,
        diagnostics=(error,),
        layout=ParserLayout.BEM_MAIOR,
    )

    assert result.ok is False
    assert result.pending_import is None
    assert result.errors == (error,)
    assert result.warnings == ()


def test_parse_result_mixed_diagnostics() -> None:
    warning = ParseDiagnostic(
        level=DiagnosticLevel.WARNING,
        code="rounding",
        message="Total difere por centavos",
    )
    error = ParseDiagnostic(
        level=DiagnosticLevel.ERROR,
        code="missing_total",
        message="Total geral nao encontrado",
    )
    result = ParseResult(
        pending_import=None,
        diagnostics=(warning, error),
        layout=ParserLayout.BEM_MAIOR,
    )

    assert result.ok is False
    assert result.warnings == (warning,)
    assert result.errors == (error,)


def test_parse_result_rejects_invalid_pending_import() -> None:
    with pytest.raises(TypeError):
        ParseResult(
            pending_import="not_an_import",
            diagnostics=(),
            layout=ParserLayout.BEM_MAIOR,
        )


def test_parse_result_rejects_invalid_diagnostics_type() -> None:
    with pytest.raises(TypeError):
        ParseResult(
            pending_import=None,
            diagnostics=["not_a_diagnostic"],
            layout=ParserLayout.BEM_MAIOR,
        )


def test_parse_result_rejects_invalid_layout() -> None:
    with pytest.raises(TypeError):
        ParseResult(
            pending_import=None,
            diagnostics=(),
            layout="bem_maior",
        )


# ---------------------------------------------------------------------------
# NfceParser protocol (via FakeParser)
# ---------------------------------------------------------------------------


def test_fake_parser_satisfies_protocol() -> None:
    parser = FakeParser()
    result = parser.parse(["line1", "line2"], source_pdf="compra.pdf")

    assert parser.layout == ParserLayout.BEM_MAIOR
    assert result.ok is True
    assert result.pending_import is not None
    assert result.layout == ParserLayout.BEM_MAIOR


def test_fake_parser_returns_custom_result() -> None:
    error = ParseDiagnostic(
        level=DiagnosticLevel.ERROR,
        code="parse_failed",
        message="Formato desconhecido",
    )
    custom_result = ParseResult(
        pending_import=None,
        diagnostics=(error,),
        layout=ParserLayout.BEM_MAIOR,
    )
    parser = FakeParser(result=custom_result)
    result = parser.parse([], source_pdf="bad.pdf")

    assert result.ok is False
    assert result is custom_result


# ---------------------------------------------------------------------------
# ParserRegistry
# ---------------------------------------------------------------------------


def test_registry_starts_empty() -> None:
    registry = ParserRegistry()

    assert len(registry) == 0
    assert registry.available_layouts == ()
    assert registry.get(ParserLayout.BEM_MAIOR) is None
    assert ParserLayout.BEM_MAIOR not in registry


def test_registry_register_and_retrieve() -> None:
    registry = ParserRegistry()
    parser = FakeParser()

    registry.register(parser)

    assert len(registry) == 1
    assert ParserLayout.BEM_MAIOR in registry
    assert registry.get(ParserLayout.BEM_MAIOR) is parser
    assert registry.available_layouts == (ParserLayout.BEM_MAIOR,)


def test_registry_rejects_duplicate_layout() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeParser())


def test_registry_rejects_parser_without_layout() -> None:
    registry = ParserRegistry()

    with pytest.raises(TypeError, match="ParserLayout"):
        registry.register(object())


def test_registry_get_returns_none_for_unregistered() -> None:
    registry = ParserRegistry()

    assert registry.get(ParserLayout.BEM_MAIOR) is None


def test_registry_contains_check() -> None:
    registry = ParserRegistry()
    parser = FakeParser()
    registry.register(parser)

    assert ParserLayout.BEM_MAIOR in registry
