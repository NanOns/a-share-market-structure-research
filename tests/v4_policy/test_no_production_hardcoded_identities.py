"""Repository-wide admission coverage for fixed business identity literals."""
import ast
import json
from pathlib import Path

import pytest

from scripts.check_v4_business_literals import (
    DATE_RE, SEC_RE, ROOT, active_entrypoint_inventory, date_component_literals, gate_exit_code, global_gate, scan, semantic_candidate_key, tracked_files, verified_false_positive, versioned_market_reference, verified_historical_evidence_binding,
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
        and item["handling"] != "VERSIONED_MARKET_REFERENCE"
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


def test_unverified_maintenance_literal_blocks_global_gate():
    gate=global_gate([{"file":"scripts/manual_builder.py","runtime_reachable":False,
                       "handling":"UNRESOLVED","semantic_key":"manual-script-candidate"}])
    assert gate["status"]=="GLOBAL_RUNTIME_LITERAL_GATE_BLOCKED"
    assert gate["unverified_maintenance_candidates"]==1
    assert gate_exit_code(gate)==1


def test_v4_runtime_entrypoint_inventory_is_explicit_and_tracked():
    entries,evidence=active_entrypoint_inventory(tracked_files())
    assert evidence["status"]=="SOURCE_VERIFIED"
    assert "run_workbench_service.py" in entries
    assert "src/workbench_service/v4_control_server_v2.py" in entries
    assert "run_phase0.py" not in entries


def test_only_sha_bound_versioned_index_reference_is_classified_as_market_reference():
    contract=json.loads((ROOT/"config/core_product_index_benchmark_v1.json").read_text(encoding="utf-8"))
    assert contract["benchmarks"]
    assert all(versioned_market_reference("config/core_product_index_benchmark_v1.json",item["symbol"])
               for item in contract["benchmarks"])


@pytest.mark.parametrize(("rel","category","literal","line","reason"),[
    ("src/tdx/tdx_audit.py","CONSTANT_SECTOR_ID","T0002",'cache = tdx_root / "T0002" / "hq_cache"',"TDX_METADATA_DIRECTORY_COMPONENT"),
    ("src/workbench_analysis/v4_15_settlement.py","CONSTANT_SECTOR_ID","industry:candidates",'if industry:candidates=[r for r in rows]',"PYTHON_IF_SUITE_ASSIGNMENT"),
    ("src/workbench_db/postgres_repository.py","CONSTANT_SECURITY_ID","999999",'coalesce(current_rank,potential_rank,999999)',"SQL_RANK_ORDERING_SENTINEL"),
    ("src/production/workbench.py","CONSTANT_SECURITY_ID","172033",'color:#172033;background:#fff',"CSS_HEX_COLOR"),
])
def test_exact_syntax_literals_are_classified_as_false_positives(rel,category,literal,line,reason):
    assert verified_false_positive(rel,category,literal,line)==reason


def test_historical_path_requires_matching_existing_sha_binding():
    rel="src/v4/scoped_promotions_r3.py"
    source=(ROOT/rel).read_text(encoding="utf-8")
    tree=ast.parse(source)
    assert verified_historical_evidence_binding(rel,"20261002",tree,source)
    unbound=ast.parse("AUTHORITY = 'docs/evidence/next_round_r3/V4_R2_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R2_20261002.md'")
    assert verified_historical_evidence_binding(rel,"20261002",unbound,"") is None


def test_semantic_fingerprint_survives_line_insertion():
    first = semantic_candidate_key("src/v4/sample.py", "CONSTANT_DATE", "2026-10-23", "trade_day = '2026-10-23'")
    after_insertion = semantic_candidate_key("src/v4/sample.py", "CONSTANT_DATE", "2026-10-23", "trade_day = '2026-10-23'")
    assert first == after_insertion


def test_python_date_constructor_is_a_date_candidate():
    tree = ast.parse("from datetime import date\nselected = date(2026, 10, 23)")
    assert date_component_literals(tree) == [(2, "2026-10-23")]


def test_compact_date_and_security_detection_skips_hex_digest_chunks():
    assert DATE_RE.search('"20261023"')
    assert SEC_RE.search('"600000"')
    assert not DATE_RE.search('sha256=ab20261023cd')
    assert not SEC_RE.search('sha256=ab600000cd')


def test_live_forward_finds_sealed_model_by_identity_not_trade_date_path(tmp_path, monkeypatch):
    from run_live_forward import sealed_model_identity

    model_hash = "a" * 64
    module = __import__("run_live_forward")
    monkeypatch.setattr(module, "SEALED_MODEL", model_hash)
    identity = tmp_path / "reports/shadow/v2" / "arbitrary-input-date" / "integrated" / "R3_INTEGRATED_SHADOW_IDENTITY.json"
    identity.parent.mkdir(parents=True)
    identity.write_text(json.dumps({"sha256": model_hash}), encoding="utf-8")
    assert sealed_model_identity(tmp_path) == {"sha256": model_hash}
