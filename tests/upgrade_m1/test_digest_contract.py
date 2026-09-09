from workbench_db.digest import logical_digest, normalize_csv_row
from datetime import date


def test_digest_is_order_independent_but_column_order_bound():
    rows = [{"id": "2", "value": "x"}, {"id": "1", "value": None}]
    assert logical_digest(rows, ["id", "value"], ["id"])["sha256"] == logical_digest(list(reversed(rows)), ["id", "value"], ["id"])["sha256"]
    assert logical_digest(rows, ["id", "value"], ["id"])["sha256"] != logical_digest(rows, ["value", "id"], ["id"])["sha256"]


def test_csv_empty_is_null_and_string_precision_is_preserved():
    assert normalize_csv_row({"empty": "", "number": "1.2300"}) == {"empty": None, "number": "1.2300"}


def test_temporal_values_use_reconstructable_json_transport_form():
    source = [{"id": "1", "as_of": date(2026, 9, 7)}]
    reconstructed = [{"id": "1", "as_of": "2026-09-07"}]
    assert logical_digest(source, ["id", "as_of"], ["id"])["sha256"] == logical_digest(
        reconstructed, ["id", "as_of"], ["id"]
    )["sha256"]
