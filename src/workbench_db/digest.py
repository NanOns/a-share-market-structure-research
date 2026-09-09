"""Logical content digest independent of physical file bytes."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime
from typing import Any, Iterable


VERSION = "m1-logical-digest-v1.1"


def normalize_csv_row(row: dict[str, str | None]) -> dict[str, Any]:
    return {key: None if value in (None, "") else value for key, value in row.items()}


def _value(value: Any) -> Any:
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NON_FINITE_FLOAT")
        return ["float", format(value, ".17g")]
    # JSON is the repository's canonical payload boundary.  Temporal Arrow
    # scalars therefore normalize to their ISO JSON representation before
    # hashing, so a digest can be reconstructed from the database without
    # guessing source types that JSON does not retain.
    if isinstance(value, (date, datetime)):
        return ["string", value.isoformat()]
    if isinstance(value, dict):
        return ["object", [[str(key), _value(value[key])] for key in sorted(value)]]
    if isinstance(value, (list, tuple)):
        return ["list", [_value(item) for item in value]]
    return ["string", str(value)]


def logical_digest(rows: Iterable[dict[str, Any]], columns: list[str], primary_key: list[str]) -> dict[str, Any]:
    canonical_rows = [[[column, _value(row.get(column))] for column in columns] for row in rows]
    index = {column: position for position, column in enumerate(columns)}
    for key in primary_key:
        if key not in index:
            raise ValueError(f"PRIMARY_KEY_COLUMN_MISSING:{key}")
    def sort_key(row: list[list[Any]]) -> tuple[str, ...]:
        mapped = {column: value for column, value in row}
        return tuple(json.dumps(mapped[key], ensure_ascii=False, separators=(",", ":")) for key in primary_key) + (json.dumps(row, ensure_ascii=False, separators=(",", ":")),)
    canonical_rows.sort(key=sort_key)
    payload = {"version": VERSION, "columns": columns, "primary_key": primary_key, "rows": canonical_rows}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {"version": VERSION, "sha256": hashlib.sha256(encoded).hexdigest(), "row_count": len(canonical_rows), "columns": columns, "primary_key": primary_key}
