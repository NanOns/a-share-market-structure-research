"""Helpers for content-checked, immutable slice writes."""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from typing import Any, Iterable, Sequence


def _canonical(value: Any) -> Any:
    """Return a stable, JSON-safe representation for row comparison."""
    if value is None:
        return None
    if hasattr(value, "item") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return _canonical(value.item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple, set)):
        return [_canonical(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return value
        return _canonical(parsed) if isinstance(parsed, (dict, list)) else value
    return value


def row_signature(row: Sequence[Any]) -> str:
    return json.dumps(_canonical(list(row)), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def immutable_slice_state(
    existing_rows: Iterable[Sequence[Any]],
    expected_rows: Iterable[Sequence[Any]],
    *,
    key_indexes: tuple[int, ...],
    conflict_code: str,
) -> bool:
    """Validate an existing slice and return whether it is already present."""
    existing = list(existing_rows)
    expected = list(expected_rows)

    def key(row: Sequence[Any]) -> tuple[str, ...]:
        return tuple(row_signature([row[index]]) for index in key_indexes)

    expected_keys = [key(row) for row in expected]
    actual_keys = [key(row) for row in existing]
    if len(set(expected_keys)) != len(expected_keys) or len(set(actual_keys)) != len(actual_keys):
        raise ValueError(conflict_code)
    if actual_keys and set(actual_keys) != set(expected_keys):
        raise ValueError(conflict_code)
    if not actual_keys:
        return False

    expected_by_key = {key(row): row_signature(row) for row in expected}
    actual_by_key = {key(row): row_signature(row) for row in existing}
    if expected_by_key != actual_by_key:
        raise ValueError(conflict_code)
    return True
