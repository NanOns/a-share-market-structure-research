"""Restore and rehash R4.1 LFS outputs from the pushed candidate commit."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/v4_05/V4_05_R4_1_PUBLISHED_LFS_RESTORE.json"
OUTPUTS = (
    "reports/v4_05/staging/V4_05_R4_1_PERIOD_ASOF.jsonl.gz",
    "reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz",
    "reports/v4_05/staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz",
)


def run(args: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr[-6000:]}")
    return result.stdout.strip()


def identity(path: Path) -> dict:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "byte_count": path.stat().st_size}


def pointer(value: str) -> dict:
    result = {}
    for line in value.splitlines():
        if line.startswith("oid sha256:"):
            result["sha256"] = line.removeprefix("oid sha256:")
        elif line.startswith("size "):
            result["byte_count"] = int(line.removeprefix("size "))
    if set(result) != {"sha256", "byte_count"}:
        raise ValueError("commit path is not a complete Git LFS pointer")
    return result


def build() -> dict:
    commit = run(["git", "rev-parse", "HEAD"], ROOT)
    remote = run(["git", "remote", "get-url", "origin"], ROOT)
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    entries = {}
    with tempfile.TemporaryDirectory(prefix="v4_05_r4_1_published_lfs_") as name:
        clone = Path(name) / "checkout"
        run(["git", "clone", "--no-checkout", remote, str(clone)], env=env)
        run(["git", "checkout", "--detach", commit], clone, env)
        pointers = {relative: pointer(run(["git", "show", f"{commit}:{relative}"], clone, env))
                    for relative in OUTPUTS}
        include = ",".join(OUTPUTS)
        run(["git", "lfs", "fetch", "origin", commit, f"--include={include}"], clone, env)
        run(["git", "lfs", "checkout", *OUTPUTS], clone, env)
        for relative in OUTPUTS:
            local, restored = identity(ROOT / relative), identity(clone / relative)
            expected = pointers[relative]
            entries[relative] = {
                "git_lfs_pointer": expected,
                "primary_artifact": local,
                "fresh_clone_restored_artifact": restored,
                "pointer_matches_artifact": expected == local,
                "clone_matches_pointer": expected == restored,
                "artifact_bytes_equal": local == restored,
            }
        clone_head = run(["git", "rev-parse", "HEAD"], clone, env)
    status = "PASS" if all(all(row[key] for key in (
        "pointer_matches_artifact", "clone_matches_pointer", "artifact_bytes_equal"))
        for row in entries.values()) else "FAIL"
    result = {
        "contract_id": "V4_05_R4_1_PUBLISHED_LFS_RESTORE_V1", "status": status,
        "candidate_commit": commit, "fresh_clone_head": clone_head, "clone_source": remote,
        "clone_directory_removed": True, "restored_artifacts": entries,
        "stage_record": {"stage_contract": "V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE",
                         "acceptance_result": status,
                         "evidence": "Pushed R4.1 LFS pointers fetched and restored in a fresh clone, then object OID, size, and SHA-256 compared with primary bytes.",
                         "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_1"},
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temp = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temp.write_bytes((json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(temp, REPORT)
    if status != "PASS":
        raise RuntimeError("published LFS output restore verification failed")
    return {"status": status, "candidate_commit": commit, "restored_outputs": len(entries)}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, sort_keys=True))
