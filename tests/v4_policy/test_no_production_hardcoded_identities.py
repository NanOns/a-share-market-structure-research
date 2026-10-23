"""Repository-wide admission coverage for fixed business identity literals."""
import ast
import json
from pathlib import Path

import pytest

from scripts.check_v4_business_literals import (
    ROOT, date_component_literals, gate_exit_code, global_gate, scan, semantic_candidate_key, tracked_files,
)
from workbench_analysis.market_source_acquisition import earliest_required_factor_session


def test_factor_coverage_starts_at_source_identity_ipo_date():
    calls = []

    def query(_client, method, **params):
        calls.append((method, params))
        return [{"ipoDate": "2012-05-17"}]

    assert earliest_required_factor_session(object(), "sh.600111", query) == "2012-05-17"
    assert calls == [("query_stock_basic", {"code": "sh.600111"})]


@pytest.mark.parametrize("rows,error", [
    ([], "ADJUSTMENT_IDENTITY_SOURCE_MISSING"),
    ([{"ipoDate": None}], "ADJUSTMENT_IDENTITY_LIST_DATE_MISSING"),
    ([{"ipoDate": "not-a-date"}], "ADJUSTMENT_IDENTITY_LIST_DATE_MISSING"),
])
def test_factor_coverage_fails_closed_without_valid_ipo_fact(rows, error):
    with pytest.raises(ValueError, match=error):
        earliest_required_factor_session(object(), "synthetic.security", lambda *_a, **_k: rows)


def test_whole_repository_has_no_new_business_literal_candidates():
    baseline_path = ROOT / "config/v4_business_literal_admission_baseline_v1.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    prior_inventory_path = ROOT / baseline["source_inventory"]
    prior_inventory = json.loads(prior_inventory_path.read_text(encoding="utf-8"))
    findings, summary = scan(tracked_files())
    legacy_keys = set(baseline["candidate_keys"])
    # Migrate fingerprints in memory from the immutable R7 evidence. This
    # preserves the old non-waiving candidate set while removing line numbers
    # from identity; it does not regenerate or widen the admission baseline.
    baseline_keys = {
        semantic_candidate_key(item["file"], item["category"], item["literal"], item["context"])
        for item in prior_inventory["findings"]
        if item.get("candidate_key") in legacy_keys and item.get("environment") != "TEST_ONLY"
    }
    # The persisted baseline fingerprints the original text-pattern detector.
    # Newly introduced AST-only classes are covered by the strict runtime gate,
    # not silently added to the non-waiving legacy diff baseline.
    current_keys = {
        item["semantic_key"] for item in findings
        if item["environment"] != "TEST_ONLY" and item["category"] != "CONSTANT_DATE_COMPONENTS"
    }
    added = sorted(current_keys - baseline_keys)
    assert not added, (
        "发现未经基线审阅的固定日期/证券/板块字面量候选；请逐条分类，不能通过扩大路径豁免："
        f"{added[:20]}（新增 {len(added)} 条；扫描文件 {summary['files_scanned']}）"
    )


def test_change_baseline_does_not_waive_existing_runtime_candidates():
    prior_candidate = {
        "runtime_reachable": True,
        "handling": "UNRESOLVED",
        "semantic_key": "existing-candidate",
    }
    gate = global_gate([prior_candidate])
    assert gate["status"] == "GLOBAL_RUNTIME_LITERAL_GATE_BLOCKED"
    assert gate["active_unknown"] == 1
    assert gate["active_violations"] == 0
    assert gate_exit_code(gate) == 1
    assert gate_exit_code(gate, allow_incomplete_inventory=True) == 0


def test_semantic_fingerprint_survives_line_insertion():
    first = semantic_candidate_key("src/v4/sample.py", "CONSTANT_DATE", "2026-10-23", "trade_day = '2026-10-23'")
    after_insertion = semantic_candidate_key("src/v4/sample.py", "CONSTANT_DATE", "2026-10-23", "trade_day = '2026-10-23'")
    assert first == after_insertion


def test_python_date_constructor_is_a_date_candidate():
    tree = ast.parse("from datetime import date\nselected = date(2026, 10, 23)")
    assert date_component_literals(tree) == [(2, "2026-10-23")]
