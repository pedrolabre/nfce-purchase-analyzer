"""Mathematical validation of NFC-e purchase totals."""

from __future__ import annotations

from decimal import Decimal

from nfce_purchase_analyzer.deterministic import (
    MONEY_TOLERANCE,
    decimal_from,
    quantize_money,
)
from nfce_purchase_analyzer.domain import PendingPurchaseImport
from nfce_purchase_analyzer.parsing.contracts import (
    DiagnosticLevel,
    ParseDiagnostic,
)

_ZERO = Decimal("0")


def validate_purchase_total(
    pending_import: PendingPurchaseImport,
) -> tuple[ParseDiagnostic, ...]:
    """Validate that the sum of item totals matches the declared total.

    Compares the sum of each item's ``total_price`` against the
    ``total_value`` declared on the receipt.  Uses the project's
    ``MONEY_TOLERANCE`` (R$ 0.05) to distinguish rounding warnings
    from hard errors.

    Args:
        pending_import: The pending purchase import to validate.

    Returns:
        A tuple of diagnostics.  Empty when the totals match exactly.
        Contains a single ``WARNING``-level diagnostic when the
        difference is within tolerance (> R$ 0.00 and <= R$ 0.05).
        Contains a single ``ERROR``-level diagnostic when the
        difference exceeds tolerance (> R$ 0.05).
    """
    if not isinstance(pending_import, PendingPurchaseImport):
        raise TypeError("pending_import must be a PendingPurchaseImport")

    calculated_total = quantize_money(
        sum(
            (decimal_from(item.total_price) for item in pending_import.items),
            _ZERO,
        )
    )
    declared_total = quantize_money(pending_import.total_value)
    difference = abs(calculated_total - declared_total)

    if difference == _ZERO:
        return ()

    tolerance = decimal_from(MONEY_TOLERANCE)

    if difference <= tolerance:
        return (
            ParseDiagnostic(
                level=DiagnosticLevel.WARNING,
                code="total_rounding",
                message=(
                    f"Soma dos itens (R$ {calculated_total}) difere do "
                    f"total declarado (R$ {declared_total}) em "
                    f"R$ {difference} (dentro da tolerancia de "
                    f"R$ {tolerance})"
                ),
            ),
        )

    return (
        ParseDiagnostic(
            level=DiagnosticLevel.ERROR,
            code="total_mismatch",
            message=(
                f"Soma dos itens (R$ {calculated_total}) difere do "
                f"total declarado (R$ {declared_total}) em "
                f"R$ {difference} (acima da tolerancia de "
                f"R$ {tolerance})"
            ),
        ),
    )


__all__ = [
    "validate_purchase_total",
]
