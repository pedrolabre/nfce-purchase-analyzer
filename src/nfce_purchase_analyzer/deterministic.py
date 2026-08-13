"""Deterministic primitives shared by the NFC-e analyzer core."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

DecimalInput = Decimal | int | str
UuidInput = uuid.UUID | str

MONEY_QUANT = Decimal("0.01")
QUANTITY_QUANT = Decimal("0.001")
MONEY_TOLERANCE = Decimal("0.05")
ROUNDING_MODE = ROUND_HALF_UP


def decimal_from(value: DecimalInput) -> Decimal:
    """Return a finite Decimal without accepting float input."""
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("Decimal values must not be created from bool or float")

    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("Decimal string must not be empty")
        try:
            decimal_value = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid decimal value: {value!r}") from exc
    else:
        raise TypeError(f"Unsupported decimal value type: {type(value).__name__}")

    if not decimal_value.is_finite():
        raise ValueError("Decimal value must be finite")
    return decimal_value


def quantize_money(value: DecimalInput) -> Decimal:
    """Quantize a monetary value to cents with the project rounding policy."""
    return decimal_from(value).quantize(MONEY_QUANT, rounding=ROUNDING_MODE)


def quantize_quantity(value: DecimalInput) -> Decimal:
    """Quantize a quantity to three decimal places."""
    return decimal_from(value).quantize(QUANTITY_QUANT, rounding=ROUNDING_MODE)


def is_within_money_tolerance(
    actual: DecimalInput,
    expected: DecimalInput,
    *,
    tolerance: DecimalInput = MONEY_TOLERANCE,
) -> bool:
    """Return whether two monetary values differ by at most the tolerance."""
    difference = abs(decimal_from(actual) - decimal_from(expected))
    return difference <= decimal_from(tolerance)


def uuid_from(value: UuidInput) -> uuid.UUID:
    """Return a UUID instance from a UUID or canonical string value."""
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value.strip())
        except ValueError as exc:
            raise ValueError(f"Invalid UUID value: {value!r}") from exc
    raise TypeError(f"Unsupported UUID value type: {type(value).__name__}")


def deterministic_uuid(namespace: UuidInput, name: str) -> uuid.UUID:
    """Create a deterministic UUID v5 from a namespace and name."""
    if not isinstance(name, str) or not name:
        raise ValueError("UUID name must be a non-empty string")
    return uuid.uuid5(uuid_from(namespace), name)


def uuid_to_string(value: UuidInput) -> str:
    """Serialize a UUID using its canonical lower-case representation."""
    return str(uuid_from(value))


def decimal_to_string(value: DecimalInput) -> str:
    """Serialize a Decimal as a plain string without converting to float."""
    return format(decimal_from(value), "f")


def to_json_safe(value: Any) -> Any:
    """Convert supported values to a JSON-safe deterministic structure."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value

    if isinstance(value, float):
        raise TypeError("JSON-safe serialization does not accept float")
    if isinstance(value, Decimal):
        return decimal_to_string(value)
    if isinstance(value, uuid.UUID):
        return uuid_to_string(value)
    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]
    if isinstance(value, dict):
        safe_items: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON-safe mapping keys must be strings")
            safe_items[key] = to_json_safe(item)
        return {key: safe_items[key] for key in sorted(safe_items)}

    raise TypeError(f"Unsupported JSON-safe value type: {type(value).__name__}")


def to_canonical_json(value: Any) -> str:
    """Serialize supported values to compact JSON with stable key ordering."""
    return json.dumps(
        to_json_safe(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


__all__ = [
    "MONEY_QUANT",
    "MONEY_TOLERANCE",
    "QUANTITY_QUANT",
    "ROUNDING_MODE",
    "decimal_from",
    "decimal_to_string",
    "deterministic_uuid",
    "is_within_money_tolerance",
    "quantize_money",
    "quantize_quantity",
    "to_canonical_json",
    "to_json_safe",
    "uuid_from",
    "uuid_to_string",
]
