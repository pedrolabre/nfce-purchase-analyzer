from decimal import Decimal
import uuid

import pytest

from nfce_purchase_analyzer.deterministic import (
    MONEY_TOLERANCE,
    decimal_from,
    decimal_to_string,
    deterministic_uuid,
    is_within_money_tolerance,
    quantize_money,
    quantize_quantity,
    to_canonical_json,
    to_json_safe,
    uuid_from,
    uuid_to_string,
)


def test_decimal_from_accepts_only_deterministic_inputs() -> None:
    assert decimal_from("10.50") == Decimal("10.50")
    assert decimal_from(7) == Decimal("7")
    assert decimal_from(Decimal("0.345")) == Decimal("0.345")

    with pytest.raises(TypeError):
        decimal_from(1.2)

    with pytest.raises(TypeError):
        decimal_from(True)


def test_money_quantization_uses_half_up_rounding_to_cents() -> None:
    assert quantize_money("10.125") == Decimal("10.13")
    assert quantize_money("10.124") == Decimal("10.12")


def test_quantity_quantization_uses_three_decimal_places() -> None:
    assert quantize_quantity("0.3456") == Decimal("0.346")
    assert quantize_quantity("2") == Decimal("2.000")


def test_money_tolerance_is_explicit_and_inclusive() -> None:
    assert MONEY_TOLERANCE == Decimal("0.05")
    assert is_within_money_tolerance("100.00", "100.05")
    assert is_within_money_tolerance("100.05", "100.00")
    assert not is_within_money_tolerance("100.00", "100.051")


def test_uuid_helpers_normalize_and_create_deterministic_values() -> None:
    namespace = uuid.UUID("12345678-1234-5678-1234-567812345678")
    text = "ABCDEFAB-CDEF-ABCD-EFAB-CDEFABCDEFAB"

    assert uuid_from(text) == uuid.UUID("abcdefab-cdef-abcd-efab-cdefabcdefab")
    assert uuid_to_string(text) == "abcdefab-cdef-abcd-efab-cdefabcdefab"
    assert deterministic_uuid(namespace, "store:0001") == deterministic_uuid(
        str(namespace),
        "store:0001",
    )
    assert deterministic_uuid(namespace, "store:0001") != deterministic_uuid(
        namespace,
        "store:0002",
    )


def test_json_safe_serialization_preserves_decimal_and_uuid_as_strings() -> None:
    payload = {
        "total": Decimal("10.00"),
        "id": uuid.UUID("abcdefab-cdef-abcd-efab-cdefabcdefab"),
        "items": [Decimal("1.230"), {"quantity": Decimal("0.345")}],
    }

    assert to_json_safe(payload) == {
        "id": "abcdefab-cdef-abcd-efab-cdefabcdefab",
        "items": ["1.230", {"quantity": "0.345"}],
        "total": "10.00",
    }
    assert to_canonical_json(payload) == (
        '{"id":"abcdefab-cdef-abcd-efab-cdefabcdefab",'
        '"items":["1.230",{"quantity":"0.345"}],'
        '"total":"10.00"}'
    )


def test_json_safe_serialization_rejects_float_values() -> None:
    with pytest.raises(TypeError):
        to_json_safe({"total": 10.0})


def test_decimal_string_serialization_never_uses_float_notation() -> None:
    assert decimal_to_string(Decimal("1E+3")) == "1000"
    assert decimal_to_string(Decimal("1.2300")) == "1.2300"
