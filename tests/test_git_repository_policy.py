from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import git_repository_policy as policy


def test_allowed_code_and_report_contract():
    assert policy.classify_path("src/workbench/example.py") is None
    assert policy.classify_path("docs/spec/source-contract.md") is None
    assert policy.classify_path("docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1.md") is None
    assert policy.classify_path("docs/upgrade/V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md") == "PROCESS_UPGRADE_DOCUMENT"
    assert policy.classify_path("reports/stage/V4_GOVERNANCE_COMPREHENSIVE_TEST_REPORT_20261016_R1.md") is None
    assert policy.classify_path("run_workbench_service.py") is None


def test_report_and_data_cannot_be_renamed_into_allowed_paths():
    assert policy.classify_path("reports/audits/renamed.md") == "FORBIDDEN_REPORT_PATH"
    findings = policy.inspect_blob("config/release.json", b'{"task_id":"old-run","payload":[]}')
    assert "PROCESS_PAYLOAD_MASQUERADE" in {item.code for item in findings}


def test_chinese_and_space_paths_are_parsed_as_single_names():
    parsed = policy.parse_name_status("M\0docs/spec/治理 说明.md\0R100\0reports/audits/旧文件.md\0docs/spec/新 文件.md\0".encode())
    assert parsed == [("M", "docs/spec/治理 说明.md"), ("R100", "docs/spec/新 文件.md")]


def test_lfs_pointer_requires_a_matching_local_object(monkeypatch):
    payload = b"small approved fixture"
    oid = hashlib.sha256(payload).hexdigest()
    pointer = f"version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {len(payload)}\n".encode()
    monkeypatch.setattr(policy, "_read_lfs_object", lambda _oid: payload)
    assert not policy.inspect_blob("docs/spec/source-contract.md", pointer)
    monkeypatch.setattr(policy, "_read_lfs_object", lambda _oid: b"tampered")
    assert "LFS_OBJECT_MISMATCH" in {item.code for item in policy.inspect_blob("docs/spec/source-contract.md", pointer)}


def test_real_security_ids_are_allowed_in_tests_but_production_branch_is_not():
    assert policy.inspect_blob("tests/test_market_case.py", b"assert symbol == '600000'\n") == []
    findings = policy.inspect_blob("src/ui/market.js", b"if (code == '600000') { return true; }\n")
    assert "TARGET_SPECIFIC_BRANCH" in {item.code for item in findings}


def test_large_formal_document_requires_review_and_large_data_is_rejected():
    body = b"x" * (policy.MAX_BLOB_BYTES + 1)
    assert "MANUAL_REVIEW_REQUIRED" in {item.code for item in policy.inspect_blob("docs/requirements/large.md", body)}
    assert "BLOB_TOO_LARGE" in {item.code for item in policy.inspect_blob("src/large.py", body)}


def test_machine_paths_credentials_and_dynamic_sql_are_flagged_without_echoing_values():
    findings = policy.inspect_blob(
        "src/db/query.sql",
        b"-- D:/new_tdx\nSELECT * FROM t WHERE id = ' + user_id\n"
        + b"# pass" + b"word = SuperSecretValue\n",
    )
    codes = {item.code for item in findings}
    assert {"MACHINE_PATH", "CREDENTIAL_PATTERN", "DYNAMIC_SQL"} <= codes
    assert all("SuperSecretValue" not in item.detail for item in findings)


def test_stage_report_requires_schema():
    findings = policy.inspect_blob(
        "reports/stage/V4_GOVERNANCE_COMPREHENSIVE_TEST_REPORT_20261016_R1.md",
        b"# Preliminary\n",
    )
    assert {"STAGE_REPORT_SCHEMA", "STAGE_REPORT_TEMPLATE"} <= {item.code for item in findings}


def _git(cwd: Path, *args: str):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_staged_cli_blocks_modification_of_an_already_tracked_report(tmp_path):
    repo = tmp_path / "tracked-report-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Policy Test")
    _git(repo, "config", "user.email", "policy@example.invalid")
    report = repo / "reports" / "audits" / "tracked.md"
    report.parent.mkdir(parents=True)
    report.write_text("old content\n", encoding="utf-8")
    _git(repo, "add", "-f", "reports/audits/tracked.md")
    _git(repo, "commit", "-qm", "baseline")
    report.write_text("modified content\n", encoding="utf-8")
    _git(repo, "add", "-f", "reports/audits/tracked.md")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "git_repository_policy.py"), "--staged"],
        cwd=repo, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 1
    assert "FORBIDDEN_REPORT_PATH" in result.stdout


def test_ci_diff_checks_the_destination_blob_after_a_disguising_rename(tmp_path):
    repo = tmp_path / "rename-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Policy Test")
    _git(repo, "config", "user.email", "policy@example.invalid")
    original = repo / "reports" / "audits" / "old evidence.md"
    original.parent.mkdir(parents=True)
    original.write_text('{"task_id":"legacy"}\n', encoding="utf-8")
    _git(repo, "add", "-f", "reports/audits/old evidence.md")
    _git(repo, "commit", "-qm", "baseline")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    destination = repo / "config" / "正常配置.md"
    destination.parent.mkdir()
    original.rename(destination)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "rename")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "git_repository_policy.py"), "--diff-base", base, "--diff-head", "HEAD"],
        cwd=repo, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 1
    assert "PROCESS_PAYLOAD_MASQUERADE" in result.stdout
    assert "config/正常配置.md" in result.stdout
