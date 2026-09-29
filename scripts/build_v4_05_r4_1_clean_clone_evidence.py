"""Rebuild R4.1 in an exact-commit clone and verify LFS source restoration."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/v4_05/V4_05_R4_1_CLEAN_CLONE_DETERMINISM.json"
BUILDS = (
    "scripts/build_v4_05_r4_periods.py",
    "scripts/build_v4_05_r4_market_reference.py",
    "scripts/build_v4_05_r4_full_scope_factors.py",
    "scripts/build_v4_05_r4_market_regime.py",
    "scripts/build_v4_05_r4_core_profile.py",
)
LFS_INPUTS = (
    "reports/v4_05/staging/V4_05_R3_T0_COORDINATE_DAILY_HISTORY.jsonl.gz",
    "reports/v4_05/staging/V4_05_R3_FULL_SCOPE_FACTORS.jsonl.gz",
    "reports/v4_05/staging/V4_05_R4_PERIOD_ASOF.jsonl.gz",
    "reports/v4_05/staging/V4_05_R4_FULL_SCOPE_FACTORS.jsonl.gz",
    "reports/v4_05/staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz",
    "data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz",
    "data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz",
)
CHECKED_IN_INPUTS = ("reports/v4_02/staging/V4_02_GO_FORWARD_ADJUSTED_T0_CANDIDATE_R3.jsonl.gz",)
OUTPUTS = (
    "reports/v4_05/staging/V4_05_R4_1_PERIOD_ASOF.jsonl.gz",
    "reports/v4_05/V4_05_R4_1_PERIOD_ASOF.json",
    "reports/v4_05/V4_05_R4_1_TARGET_MARKET_SNAPSHOT.json",
    "reports/v4_05/V4_05_R4_1_MARKET_SNAPSHOT_IDENTITY.json",
    "reports/v4_05/V4_05_R4_1_MARKET_REFERENCE.json",
    "reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz",
    "reports/v4_05/V4_05_R4_1_FULL_SCOPE_FACTORS_RECEIPT.json",
    "reports/v4_05/V4_05_R4_1_MARKET_REGIME.json",
    "reports/v4_05/staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz",
    "reports/v4_05/V4_05_R4_1_CORE_PROFILE_REPLAY.json",
)


def run(args: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
        stdout=None) -> subprocess.CompletedProcess:
    if stdout is None:
        stdout = subprocess.PIPE
    result = subprocess.run(args, cwd=cwd, env=env, text=True, stdout=stdout,
                            stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr[-6000:]}")
    return result


def file_identity(path: Path) -> dict:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return {"sha256": h.hexdigest(), "byte_count": path.stat().st_size}


def lfs_pointer(path: Path) -> dict:
    fields = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith("oid sha256:"):
            fields["oid"] = line.removeprefix("oid sha256:")
        elif line.startswith("size "):
            fields["size"] = int(line.removeprefix("size "))
    if not fields.get("oid") or fields.get("size") is None:
        raise ValueError(f"not a valid Git LFS pointer: {path}")
    return fields


def logical_projection(root: Path) -> dict:
    def load(path: str) -> dict:
        return json.loads((root / path).read_text(encoding="utf-8"))

    period = load("reports/v4_05/V4_05_R4_1_PERIOD_ASOF.json")
    factor = load("reports/v4_05/V4_05_R4_1_FULL_SCOPE_FACTORS_RECEIPT.json")
    regime = load("reports/v4_05/V4_05_R4_1_MARKET_REGIME.json")
    profile = load("reports/v4_05/V4_05_R4_1_CORE_PROFILE_REPLAY.json")
    reference = load("reports/v4_05/V4_05_R4_1_MARKET_REFERENCE.json")
    identity = load("reports/v4_05/V4_05_R4_1_MARKET_SNAPSHOT_IDENTITY.json")
    return {
        "period": {key: period[key] for key in ("row_count", "logical_digest", "source_daily_digest")},
        "reference": {"target_trade_date": reference["target_trade_date"],
                      "target_market_snapshot_id": reference["target_market_snapshot_id"],
                      "horizons": {h: {key: row[key] for key in (
                          "reference_return", "universe_count", "evaluable_count", "missing_count", "coverage",
                          "quality_state", "unknown_reason", "max_source_trade_date")}
                                   for h, row in reference["horizons"].items()}},
        "market_snapshot": {key: identity[key] for key in (
            "target_market_snapshot_id", "target_market_snapshot_sha256", "target_market_snapshot_hash_algorithm",
            "target_member_count", "target_adjustment_basis_id")},
        "factor": {key: factor[key] for key in (
            "logical_digest", "row_count", "field_quality_count", "market_reference_sha256",
            "market_reference_hash_algorithm", "max_source_trade_date")},
        "regime": {"identity": regime["identity"], "target_row": regime["target_row"],
                    "axes": regime["axes"], "trend": regime["trend"], "regime_ui": regime["regime_ui"]},
        "core_profile": {key: profile[key] for key in (
            "logical_digest", "row_count", "source_digest", "contract_digest", "quality_counts")
            if key in profile},
    }


def build() -> dict:
    commit = run(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip()
    remote = run(["git", "remote", "get-url", "origin"], cwd=ROOT).stdout.strip()
    source_env = os.environ.copy()
    source_env["GIT_LFS_SKIP_SMUDGE"] = "1"
    artifacts: dict[str, dict] = {}
    restored: dict[str, dict] = {}
    checked_in: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="v4_05_r4_1_clean_clone_") as temp_name:
        clone = Path(temp_name) / "checkout"
        run(["git", "clone", "--no-checkout", remote, str(clone)], env=source_env)
        run(["git", "checkout", "--detach", commit], cwd=clone, env=source_env)
        pointers = {}
        for relative in LFS_INPUTS:
            pointer_bytes = run(["git", "show", f"{commit}:{relative}"], cwd=clone).stdout.encode("utf-8")
            pointer_text = pointer_bytes.decode("ascii")
            pointer_file = Path(tempfile.gettempdir()) / ("v4_05_pointer_" + sha256(relative.encode()).hexdigest())
            pointer_file.write_text(pointer_text, encoding="ascii")
            pointers[relative] = lfs_pointer(pointer_file)
            pointer_file.unlink(missing_ok=True)
        include = ",".join(LFS_INPUTS)
        lfs_env = source_env.copy()
        lfs_env["GIT_LFS_SKIP_SMUDGE"] = "1"
        run(["git", "lfs", "fetch", "origin", commit, f"--include={include}"], cwd=clone, env=lfs_env)
        run(["git", "lfs", "checkout", *LFS_INPUTS], cwd=clone, env=lfs_env)
        for relative in LFS_INPUTS:
            source_path, clone_path = ROOT / relative, clone / relative
            source_identity, clone_identity = file_identity(source_path), file_identity(clone_path)
            pointer = pointers[relative]
            restored[relative] = {
                "lfs_oid": pointer["oid"], "lfs_size": pointer["size"],
                "working_tree_sha256": source_identity["sha256"], "clone_sha256": clone_identity["sha256"],
                "pointer_matches_working_tree": pointer["oid"] == source_identity["sha256"]
                    and pointer["size"] == source_identity["byte_count"],
                "clone_matches_pointer": pointer["oid"] == clone_identity["sha256"]
                    and pointer["size"] == clone_identity["byte_count"],
            }
        for relative in CHECKED_IN_INPUTS:
            source_identity = file_identity(ROOT / relative)
            clone_identity = file_identity(clone / relative)
            checked_in[relative] = {"working_tree": source_identity, "clone": clone_identity,
                                    "identical": source_identity == clone_identity}
        for script in BUILDS:
            with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
                env = source_env.copy()
                env["V4_05_BUILD_ID"] = "R4_1"
                env["GIT_LFS_SKIP_SMUDGE"] = "1"
                run([sys.executable, script], cwd=clone, env=env, stdout=log)
        for relative in OUTPUTS:
            primary = file_identity(ROOT / relative)
            rebuilt = file_identity(clone / relative)
            artifacts[relative] = {"primary": primary, "clean_clone": rebuilt,
                                   "identical": primary == rebuilt}
        logical_equal = logical_projection(ROOT) == logical_projection(clone)
        all_lfs_restored = all(row["pointer_matches_working_tree"] and row["clone_matches_pointer"]
                               for row in restored.values())
        all_checked_in_inputs = all(row["identical"] for row in checked_in.values())
        outputs_equal = all(row["identical"] for row in artifacts.values())
        build_head = run(["git", "rev-parse", "HEAD"], cwd=clone).stdout.strip()
    status = "PASS" if all_lfs_restored and all_checked_in_inputs and outputs_equal and logical_equal else "FAIL"
    result = {
        "contract_id": "V4_05_R4_1_CLEAN_CLONE_DETERMINISM_V1", "status": status,
        "implementation_commit": commit, "clean_clone_head": build_head,
        "clone_source": remote, "clone_directory_removed": True,
        "lfs_restore": {"status": "PASS" if all_lfs_restored else "FAIL", "inputs": restored},
        "git_blob_inputs": {"status": "PASS" if all_checked_in_inputs else "FAIL", "inputs": checked_in},
        "build_steps": list(BUILDS), "deterministic_outputs": artifacts,
        "all_output_bytes_equal": outputs_equal, "logical_digest_and_business_projection_equal": logical_equal,
        "stage_record": {"stage_contract": "V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE",
                         "acceptance_result": status,
                         "evidence": "Exact pushed implementation commit cloned; required LFS inputs restored by OID; all R4.1 outputs and logical projections re-built and compared byte for byte.",
                         "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_1"},
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temp = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temp.write_bytes((json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(temp, REPORT)
    if status != "PASS":
        raise RuntimeError("clean-clone or LFS restore verification failed")
    return {"status": status, "implementation_commit": commit, "outputs": len(artifacts),
            "lfs_inputs": len(restored), "clone_head": build_head}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, sort_keys=True))
