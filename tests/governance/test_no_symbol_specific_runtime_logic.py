import ast
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from scan_no_symbol_specific_runtime_logic import _numeric_code_literals, _string_literals, run


def _fixture_project(base, files):
    policy = {
        "policy_id": "NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC",
        "scan_roots": ["src", "scripts", "tests", "config", "docs/evidence", "data"],
        "scan_globs": [],
        "production_entrypoints": ["src/production/daily.py", "run_daily.py"],
        "production_required_modules": [],
        "production_runtime_globs": ["src/production/**/*.py", "run_daily.py"],
        "system_pipeline_globs": ["src/**/*.py", "src/**/*.sql", "scripts/**/*.py", "scripts/**/*.sql"],
        "governance_mutation_globs": ["scripts/promote_*.py", "scripts/accept_*.py", "scripts/materialize_*.py", "scripts/apply_*.py", "scripts/*accepted_head*.py", "scripts/*publication*.py"],
        "test_only_globs": ["tests/**/*.py", "tests/fixtures/**"],
        "evidence_only_globs": ["docs/evidence/**"],
        "runtime_configuration_paths": [],
        "reference_data_paths": ["config/market_reference.json"],
        "immutable_fact_globs": ["data/v4/artifact_store/**/*.json"],
        "user_data_globs": ["data/user/**/*.json", "data/focus/**/*.json"],
        "path_roles": {},
    }
    policy_path = base / "config/runtime_path_policy_v1.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    (base / "run_daily.py").write_text("from production.daily import run\n", encoding="utf-8")
    for rel, content in files.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content) if isinstance(content, bytes) else path.write_text(content, encoding="utf-8")
    return base


def _scan(tmp_path, files):
    return run(_fixture_project(tmp_path, files))


def test_complete_repository_has_no_hard_gated_symbols_or_unclassified_paths():
    result = run(ROOT)
    assert result["status"] == "PASS", result["hard_gated_hits"]
    assert result["hard_gated_equity_symbol_hits"] == 0
    assert result["unclassified_paths"] == []
    assert result["file_receipts"]
    assert all(item.get("sha256") and item.get("byte_count") is not None for item in result["file_receipts"])
    categories = result["category_per_file"]
    assert categories["src/production/daily.py"] == "PRODUCTION_RUNTIME"
    assert categories["src/phase1_runner.py"] == "PRODUCTION_RUNTIME"
    assert categories["src/phase1_qa.py"] == "PRODUCTION_RUNTIME"
    assert categories["config/v4_market_reference_instruments_v1.json"] == "REFERENCE_DATA"


def test_ast_guard_detects_equality_and_set_membership_literals():
    source = 'def equality(security_id): return security_id == "SH.123456"\ndef membership(symbol): return symbol in {"SZ.654321", "BJ.111111"}\n'
    hits = list(_string_literals(ast.parse(source)))
    assert {value for value, _, _ in hits} == {"SH.123456", "SZ.654321", "BJ.111111"}


def test_numeric_security_literals_are_detected_and_docstrings_are_ignored():
    source = '"""SH.999999 is documentation."""\ndef admit(security_code): return security_code == 600519\n'
    tree = ast.parse(source)
    assert [(value, kind) for value, _, kind in _numeric_code_literals(tree)] == [
        ("600519", "NUMERIC_SECURITY_CODE_IN_IDENTIFIER_CONTEXT")
    ]
    assert list(_string_literals(tree)) == []


@pytest.mark.parametrize("source", [
    'def f(security_id): return security_id == "SH.123456"',
    'def f(security_id): return security_id in {"SH.123456"}',
])
def test_injected_production_equality_and_membership_fail(tmp_path, source):
    result = _scan(tmp_path, {"src/production/daily.py": source})
    assert result["status"] == "FAIL"
    assert result["hard_gated_equity_symbol_hits"] == 1


def test_governance_mutation_script_is_hard_gated(tmp_path):
    source = 'from pathlib import Path\ndef promote(security_id): Path("data/v4/V4_01_ACCEPTED_HEAD.json").write_text(security_id + "SH.123456")\n'
    result = _scan(tmp_path, {"scripts/promote_fixture.py": source})
    assert result["status"] == "FAIL"
    assert result["category_per_file"]["scripts/promote_fixture.py"] == "GOVERNANCE_MUTATION"
    assert result["hard_gated_equity_symbol_hits"] == 1


def test_scripts_default_to_system_pipeline_and_audit_role_is_source_hash_bound(tmp_path):
    source = 'def audit(): return "SH.123456"\n'
    path = tmp_path / "scripts/history_probe.py"
    path.parent.mkdir(parents=True)
    path.write_text(source, encoding="utf-8")
    default_result = _scan(tmp_path, {"scripts/history_probe.py": source})
    assert default_result["category_per_file"]["scripts/history_probe.py"] == "SYSTEM_PIPELINE"
    assert default_result["status"] == "FAIL"

    policy_path = tmp_path / "config/runtime_path_policy_v1.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["path_roles"] = {"scripts/history_probe.py": {
        "category": "AUDIT_ONLY", "runtime_authorized": False,
        "does_not_write_accepted_heads": True, "does_not_write_runtime_artifacts": True,
        "not_called_by_production": True, "attestation_basis": "Read-only evidence probe.",
        "reviewed_source_sha256": "0" * 64,
    }}
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    failed_attestation = run(tmp_path)
    assert failed_attestation["category_per_file"]["scripts/history_probe.py"] == "UNCLASSIFIED_FAIL_CLOSED"
    assert failed_attestation["status"] == "FAIL"

    policy["path_roles"]["scripts/history_probe.py"]["reviewed_source_sha256"] = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    attested_result = run(tmp_path)
    assert attested_result["category_per_file"]["scripts/history_probe.py"] == "AUDIT_ONLY"
    assert attested_result["status"] == "PASS"


def test_transitive_data_v4_writer_is_governance_mutation(tmp_path):
    source = '''from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data/v4/artifact_store"
OUTPUT = STORE / "accepted_fact.json"
def atomic_write(path, payload): pass
def build(): atomic_write(OUTPUT, "SH.123456")
'''
    result = _scan(tmp_path, {"scripts/legacy_builder.py": source})
    assert result["status"] == "FAIL"
    assert result["category_per_file"]["scripts/legacy_builder.py"] == "GOVERNANCE_MUTATION"
    assert result["hard_gated_equity_symbol_hits"] == 1


def test_runtime_json_and_sql_security_filter_fail(tmp_path):
    result = _scan(tmp_path, {
        "config/runtime.json": '{"threshold_by_symbol":{"SH.123456":0.9,"123457":0.8}}',
        "src/workbench_db/filter.sql": "SELECT CASE WHEN security_code IN ('123456') THEN 1 END, CASE security_code WHEN '123458' THEN 1 END;",
    })
    assert result["status"] == "FAIL"
    assert result["category_per_file"]["config/runtime.json"] == "RUNTIME_CONFIGURATION"
    assert result["category_per_file"]["src/workbench_db/filter.sql"] == "SYSTEM_PIPELINE"
    assert result["hard_gated_equity_symbol_hits"] == 4


@pytest.mark.parametrize("module", ["qa", "runner"])
def test_production_imports_cannot_downgrade_qa_or_runner(tmp_path, module):
    result = _scan(tmp_path, {
        "src/production/daily.py": f"import {module}\ndef run(): return {module}.run()\n",
        f"src/{module}.py": 'def run(): return "SZ.123456"\n',
    })
    assert result["status"] == "FAIL"
    assert result["category_per_file"][f"src/{module}.py"] == "PRODUCTION_RUNTIME"
    assert any(edge["from"] == "production.daily" and edge["to"] == module
               for edge in result["production_call_graph"]["edges"])
    assert result["hard_gated_equity_symbol_hits"] == 1


def test_allowed_test_evidence_user_data_and_market_index_reference_pass(tmp_path):
    result = _scan(tmp_path, {
        "tests/fixtures/symbol_fixture.py": 'SAMPLE = "SH.123456"\n',
        "docs/evidence/lifecycle.json": '{"security_id":"SZ.654321"}',
        "data/user/focus.json": '{"security_id":"BJ.111111"}',
        "config/market_reference.json": json.dumps({
            "classification": "REFERENCE_DATA", "contract_id": "MARKET_REFERENCE_V1",
            "runtime_authorized": True,
            "instruments": [{"instrument_id": "SH.000001", "instrument_type": "MARKET_INDEX"}],
        }),
    })
    assert result["status"] == "PASS"
    assert result["hard_gated_equity_symbol_hits"] == 0
    categories = result["category_per_file"]
    assert categories["tests/fixtures/symbol_fixture.py"] == "TEST_ONLY"
    assert categories["docs/evidence/lifecycle.json"] == "EVIDENCE_ONLY"
    assert categories["data/user/focus.json"] == "USER_DATA"
    assert categories["config/market_reference.json"] == "REFERENCE_DATA"
