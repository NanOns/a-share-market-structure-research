import copy
import gzip
import json
from pathlib import Path

import pytest

from scripts.build_v4_03_prior_rps_staging import validate_artifact
from scripts.independent_v4_03_market_path_postcheck import digest
from scripts.verify_v4_03_producer_consistency_r3 import check
from scripts.verify_v4_03_native_rule_contracts_r3 import equal
from src.v4.contracts.native_rule_r3 import execute


ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_prior_artifact_score_and_universe_tamper(tmp_path):
    artifact = ROOT / "reports/v4_03/staging/V4_03_PRIOR_RPS_STAGING_R3.json"
    receipt = ROOT / "reports/v4_03/V4_03_PRIOR_RPS_STAGING_RECEIPT_R3.json"
    validate_artifact(artifact, receipt)
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["rows"][0]["scores"][0][1] = 99.0
    tampered = tmp_path / "scores.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA"):
        validate_artifact(tampered, receipt)
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["rows"][0]["universe_snapshot_id"] = "0" * 64
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA"):
        validate_artifact(tampered, receipt)


def test_market_path_daily_return_tamper_breaks_output_digest():
    path = ROOT / "reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz"
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        next(stream)
        row = json.loads(next(stream))
    assert row["output_digest"] == digest({k: v for k, v in row.items() if k != "output_digest"})
    row["daily_return"] = (row["daily_return"] or 0) + .01
    assert row["output_digest"] != digest({k: v for k, v in row.items() if k != "output_digest"})


def test_native_vectors_and_sector_missing_identity():
    payload = read("config/v4_03_native_rule_contracts_r3.json")
    params = {x["parameter_id"]: x["value"] for x in read("config/v4_03_parameter_registry_v1.json")["entries"]}
    params.update(read("config/v4_03_parameter_set_v1.json")["engineering_candidate_thresholds"])
    assert len(payload["contracts"]) == 4
    sector = next(c for c in payload["contracts"] if c["contract_id"] == "V4_03_SECTOR_NATIVE_PRIMITIVE_V1")
    case = next(x for x in sector["vectors"] if x["vector_id"] == "SECTOR_LOCAL")
    assert execute(sector["rule"], case["input"], params)["raw_quote_coverage"] == .5
    assert not equal(execute(sector["rule"], case["input"], params)["raw_quote_coverage"], .6)
    with pytest.raises(ValueError, match="membership identity missing"):
        execute(sector["rule"], {"members": [], "rows": {}}, params)


def test_market_regime_raw_contract_excludes_membership_churn_and_uses_member_median():
    schema = read("config/v4_03_native_rule_contracts_r3.json")
    params = {x["parameter_id"]: x["value"] for x in read("config/v4_03_parameter_registry_v1.json")["entries"]}
    params.update(read("config/v4_03_parameter_set_v1.json")["engineering_candidate_thresholds"])
    regime = next(c for c in schema["contracts"] if c["contract_id"] == "MARKET_REGIME_V1_PRIMITIVES")
    vectors = {v["vector_id"]: v for v in regime["raw_vectors"]}
    rule = regime["rule"]["raw_primitive_rule"]
    result = execute(rule, vectors["REGIME_RAW_MEMBERSHIP"]["input"], params)
    assert result["breadth_common_count"] == 2 and result["breadth_delta3"] == .5
    assert result["participation_median_amount_ratio20"] == 1
    assert result["stress_same_member_current_ratio"] == .5
    partial = execute(rule, vectors["REGIME_RAW_PARTIAL"]["input"], params)
    assert partial["participation_evaluable_count"] == 1
    assert partial["participation_axis"] == "EXPANDING"


def test_trend_producer_identity_tamper():
    scope = read("config/v4_03_native_scope_map_v1.json")
    registry = read("config/v4_03_native_contract_registry_v1.json")
    schema = read("config/v4_03_output_schema_v1.json")
    contracts = read("config/v4_03_algorithm_contracts_v1.json")
    path = ROOT / "reports/v4_03/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz"
    runtime = json.loads(next(gzip.open(path, "rt", encoding="utf-8")))
    stock_path = ROOT / "reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz"
    stock_runtime = json.loads(next(gzip.open(stock_path, "rt", encoding="utf-8")))
    assert check(scope, registry, schema, contracts, runtime, stock_runtime)[0] == []
    broken = copy.deepcopy(runtime)
    broken["producer_contracts"]["trend_axis"] = "MARKET_REGIME_V1_PRIMITIVES"
    assert "trend_axis_has_multiple_or_mismatched_producers" in check(scope, registry, schema, contracts, broken, stock_runtime)[0]


def test_market_regime_receipt_and_independent_replay():
    receipt = read("reports/v4_03/V4_03_MARKET_REGIME_NATIVE_RECEIPT_R3.json")
    postcheck = read("reports/v4_03/V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3.json")
    assert receipt["rows"] == postcheck["rows_checked"] == 786
    assert postcheck["status"] == "PASS" and postcheck["mismatch_rows"] == 0


def test_sector_capability_remains_blocked_without_accepted_pit_membership():
    scope = read("config/v4_03_native_scope_map_v1.json")
    assert scope["sector_materialization"]["status"] == "BLOCKED_ACCEPTED_SECTOR_MEMBERSHIP_INPUT_NOT_PRESENT_IN_V4_01_V4_02_BASELINE_MANIFEST"
    assert scope["sector_materialization"]["full_market_sector_artifact"] == "NOT_PRODUCED"
