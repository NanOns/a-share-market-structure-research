import hashlib
import json
from pathlib import Path

from workbench_analysis.limit_rules import validate_rule_versions


ROOT = Path(__file__).parents[2]


def _config():
    return json.loads((ROOT / "config/m8c_limit_rules_public_20260911.json").read_text(encoding="utf-8"))


def test_public_registry_v11_is_effective_dated_and_source_bound():
    config = _config()
    evidence_hash = hashlib.sha256((ROOT / "config/m8c_rule_source_evidence_v11.json").read_bytes()).hexdigest()
    assert config["contract_id"] == "LIMIT_RULES_V1_1"
    assert len(validate_rule_versions(config["rules"])) == 11
    assert all(rule["source_sha256"] == evidence_hash for rule in config["rules"])
    assert {rule["rule_id"] for rule in config["rules"] if rule["risk_status"] == "RISK_WARNING" and rule["exchange"] == "SZ"} >= {
        "SZSE_MAIN_RISK_WARNING_20230410_V11",
        "SZSE_MAIN_RISK_WARNING_20260706_V11",
    }


def test_unresolved_bse_risk_branch_cannot_become_verified():
    rule = next(rule for rule in _config()["rules"] if rule["rule_id"] == "BSE_RISK_WARNING_20260706_V11")
    assert rule["rule_verified"] is False
    assert rule["audit_status"] == "PENDING_REVIEW"
