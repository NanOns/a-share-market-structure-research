"""Run the exact-candidate regression and PostgreSQL suite from a fresh clone."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/v4_05/V4_05_R4_2_CLEAN_CHECKOUT_RUNTIME.json"
LFS_INPUTS = (
    "data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json",
    "reports/v4_03/staging/V4_03_PRIOR_RPS_STAGING_R3.json",
    "reports/v4_03/V4_03_FINAL_STAGE_RECEIPT_R1_20260928.json",
    "reports/v4_05/staging/V4_05_R3_FULL_SCOPE_FACTORS.jsonl.gz",
    "reports/v4_05/staging/V4_05_R4_PERIOD_ASOF.jsonl.gz",
    "reports/v4_05/staging/V4_05_R4_1_PERIOD_ASOF.jsonl.gz",
    "reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz",
    "reports/v4_05/staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz",
)


def run(args: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr[-10000:]}\n{result.stdout[-5000:]}")
    return result


def object_sha(path: Path) -> dict:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return {"sha256": h.hexdigest(), "byte_count": path.stat().st_size}


def parse_pointer(raw: str) -> dict:
    result = {}
    for line in raw.splitlines():
        if line.startswith("oid sha256:"):
            result["sha256"] = line.removeprefix("oid sha256:")
        elif line.startswith("size "):
            result["byte_count"] = int(line.removeprefix("size "))
    if set(result) != {"sha256", "byte_count"}:
        raise ValueError("R4.1 artifact is not represented by a valid Git LFS pointer")
    return result


def build() -> dict:
    commit = run(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip()
    remote = run(["git", "remote", "get-url", "origin"], cwd=ROOT).stdout.strip()
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    env.pop("DATABASE_URL", None)
    env.pop("PGSERVICE", None)
    lfs_restore = {}
    with tempfile.TemporaryDirectory(prefix="v4_05_r4_2_clean_checkout_") as name:
        clone = Path(name) / "checkout"
        run(["git", "clone", "--no-checkout", remote, str(clone)], env=env)
        run(["git", "checkout", "--detach", commit], cwd=clone, env=env)
        pointers = {path: parse_pointer(run(["git", "show", f"{commit}:{path}"], cwd=clone, env=env).stdout)
                    for path in LFS_INPUTS}
        include = ",".join(LFS_INPUTS)
        run(["git", "lfs", "fetch", "origin", commit, f"--include={include}"], cwd=clone, env=env)
        run(["git", "lfs", "checkout", *LFS_INPUTS], cwd=clone, env=env)
        for relative, expected in pointers.items():
            restored = object_sha(clone / relative)
            lfs_restore[relative] = {"pointer": expected, "restored": restored,
                                     "matches": expected == restored}

        exact_test_command = [sys.executable, "-m", "pytest", "-q", "-rs",
                              "tests/v4_05/test_v4_05_r4_2_exact_candidate_binding.py"]
        exact_test = run(exact_test_command, cwd=clone, env=env)
        exact_test_json = {"command": exact_test_command[1:],
                           "stdout": exact_test.stdout.strip(),
                           "passed": "2 passed" in exact_test.stdout and exact_test.returncode == 0}

        ledger_command = [sys.executable, "scripts/run_v4_05_r4_1_postgres_ledger.py"]
        ledger_result = run(ledger_command, cwd=clone, env=env)
        cli_summary = json.loads(ledger_result.stdout.strip().splitlines()[-1])
        ledger_path = clone / "reports/v4_05/V4_05_R4_2_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        if ledger.get("status") != "PASS" or not ledger.get("cases", {}).get("cases"):
            raise RuntimeError("fresh-clone PostgreSQL runner failed: " + json.dumps({
                "cli_summary": cli_summary, "error": ledger.get("error"),
                "runtime_test_receipt": ledger.get("runtime_test_receipt"),
                "test_stdout": ledger.get("test_stdout"), "test_stderr": ledger.get("test_stderr"),
                "traceback": ledger.get("traceback"), "cleanup": ledger.get("cleanup")},
                ensure_ascii=False))
        cases = ledger["cases"]["cases"]
        i_status = {
            "I01_identical_replay": cases["I01_identical_replay"]["status"],
            "I02_changed_source_revision": cases["I02_changed_source_revision"]["status"],
            "I03_negative_guards": "PASS" if all(row["rejected"] for row in cases["I03_negative_guards"].values()) else "FAIL",
            "I04_transaction_rollback": "PASS" if all(row["passed"] for row in cases["I04_transaction_rollback"]) else "FAIL",
            "I05_prior_state_freeze": "PASS" if cases["I05_prior_state_freeze"]["publication_head_unchanged"]
                and all(cases["I05_prior_state_freeze"][key]["rejected"] for key in (
                    "replace_prior_publication_head", "delete_prior_publication_head",
                    "change_prior_state_head", "change_prior_state_logical_digest")) else "FAIL",
        }
        full_suite = ledger["runtime_test_receipt"]
        lfs_ok = all(item["matches"] for item in lfs_restore.values())
        all_i_pass = all(value == "PASS" for value in i_status.values())
        passed = exact_test_json["passed"] and cli_summary["status"] == "PASS" \
            and ledger["exact_candidate_binding"]["all_exact_bindings_match"] \
            and ledger["exact_candidate_binding"]["old_r4_binding_count"] == 0 \
            and ledger["status"] == "PASS" and full_suite["status"] == "PASS" and all_i_pass and lfs_ok
        clone_head = run(["git", "rev-parse", "HEAD"], cwd=clone, env=env).stdout.strip()
        result = {
            "contract_id": "V4_05_R4_2_CLEAN_CHECKOUT_RUNTIME_V1",
            "status": "PASS" if passed else "FAIL",
            "implementation_commit": commit,
            "clean_checkout_head": clone_head,
            "clone_source": remote,
            "clone_directory_removed": True,
            "lfs_restore": {"status": "PASS" if lfs_ok else "FAIL", "inputs": lfs_restore},
            "exact_candidate_binding_test": exact_test_json,
            "postgres_ledger_run": {
                "status": ledger["status"], "command": ledger_command[1:],
                "isolated_connection_identity": ledger["isolated_connection_identity"],
                "postgres_version": ledger["postgres_version"],
                "applied_migration_count": ledger["applied_migration_count"],
                "production_connection_used": ledger["production_connection_used"],
                "cases": i_status,
                "all_exact_bindings_match": ledger["exact_candidate_binding"]["all_exact_bindings_match"],
                "old_r4_binding_count": ledger["exact_candidate_binding"]["old_r4_binding_count"],
                "state_logical_digest": ledger["actual_state_head"]["logical_digest"],
                "runtime_suite": {
                    "summary": full_suite["summary"],
                    "tests_v4_phase0_test_postgres_schema_ran": full_suite["tests_v4_phase0_test_postgres_schema_ran"],
                    "skipped_test_names_and_reasons": full_suite["skipped_test_names_and_reasons"],
                },
                "cleanup": ledger["cleanup"],
            },
            "stage_record": {"stage_contract": "V4_05_REPLAY_GATE_A_R4_2_EXACT_LEDGER_BINDING",
                             "acceptance_result": "PASS_CANDIDATE_PENDING_EXTERNAL_AUDIT" if passed else "FAIL",
                             "evidence": "Fresh pushed-commit clone restored exact candidate LFS artifacts, ran the binding regression test, then formal PostgreSQL I01-I05 and the complete required pytest suite.",
                             "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_2"},
        }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temp = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temp.write_bytes((json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(temp, REPORT)
    if result["status"] != "PASS":
        raise RuntimeError("R4.2 clean-checkout runtime verification failed")
    return {"status": result["status"], "commit": commit,
            "exact_test": exact_test_json["stdout"], "pytest": full_suite["summary"],
            "cases": i_status}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, sort_keys=True))
