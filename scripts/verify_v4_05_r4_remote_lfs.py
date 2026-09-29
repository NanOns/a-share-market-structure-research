"""Verify fresh-clone Git LFS restoration for R3 and R4 replay artifacts."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.replay_r4_lfs import parse_pointer, verify_restored

OUT = ROOT / "reports/v4_05/V4_05_R4_REMOTE_LFS_RESTORE.json"
R3_MANIFEST = ROOT / "reports/v4_05/V4_05_R3_STAGE_CANDIDATE_MANIFEST.json"


def sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifacts() -> list[dict]:
    r3 = json.loads(R3_MANIFEST.read_text(encoding="utf-8"))
    result = []
    for name, meta in r3["artifacts"].items():
        if name.startswith("staging/V4_05_R3_") and name.endswith(".jsonl.gz"):
            result.append({"path": "reports/v4_05/" + name, "expected_bytes": meta["byte_count"], "expected_sha256": meta["sha256"]})
    for receipt_name in ("V4_05_R4_PERIOD_ASOF.json", "V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json", "V4_05_R4_CORE_PROFILE_REPLAY.json"):
        receipt = json.loads((ROOT / "reports/v4_05" / receipt_name).read_text(encoding="utf-8"))
        path = ROOT / receipt["artifact_path"]
        result.append({"path": receipt["artifact_path"], "expected_bytes": path.stat().st_size,
                       "expected_sha256": receipt["artifact_sha256"]})
    return result


def main(clone_root: Path) -> dict:
    clone_root = clone_root.resolve()
    if clone_root == ROOT.resolve() or not (clone_root / ".git").exists():
        raise ValueError("a separate fresh clone is required")
    remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=clone_root, check=True, capture_output=True, text=True).stdout.strip()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=clone_root, check=True, capture_output=True, text=True).stdout.strip()
    results = []
    for item in artifacts():
        pointer_raw = subprocess.run(["git", "show", f"HEAD:{item['path']}"], cwd=clone_root, check=True, capture_output=True).stdout
        pointer = parse_pointer(pointer_raw)
        restored = clone_root / item["path"]
        if not restored.is_file():
            results.append({**item, "pointer_oid_sha256": pointer["oid_sha256"], "pointer_size": pointer["size"],
                            "restored_bytes": None, "restored_sha256": None, "status": "BLOCKED_RESTORED_FILE_MISSING"})
            continue
        payload_hash = sha(restored)
        checks = {"pointer_oid_matches_expected": pointer["oid_sha256"] == item["expected_sha256"],
                  "pointer_size_matches_expected": pointer["size"] == item["expected_bytes"],
                  "restored_bytes_match_expected": restored.stat().st_size == item["expected_bytes"],
                  "restored_sha_matches_expected": payload_hash == item["expected_sha256"]}
        results.append({**item, "pointer_oid_sha256": pointer["oid_sha256"], "pointer_size": pointer["size"],
                        "restored_bytes": restored.stat().st_size, "restored_sha256": payload_hash,
                        "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"})
    result = {"contract_id": "V4_05_R4_REMOTE_LFS_RESTORE_V1", "status": "PASS" if results and all(row["status"] == "PASS" for row in results) else "BLOCKED_REMOTE_LFS_OBJECT_UNAVAILABLE",
              "fresh_clone_root": str(clone_root), "remote_origin": remote, "verified_remote_commit": commit,
              "operations": ["git clone with smudge disabled", "git lfs fetch origin HEAD --include=<listed artifacts>",
                             "git lfs checkout <listed artifacts>", "hash restored payloads"],
              "artifact_count": len(results), "artifacts": results}
    temp = OUT.with_suffix(OUT.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, OUT)
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/verify_v4_05_r4_remote_lfs.py <fresh-clone-root>")
    print(json.dumps(main(Path(sys.argv[1])), ensure_ascii=False, sort_keys=True))
