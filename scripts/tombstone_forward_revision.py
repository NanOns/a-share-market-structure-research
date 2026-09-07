"""Record an invalid Forward revision without modifying its evidence files."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from forward.live import latest_revision, next_revision_number


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    body = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != body:
            raise RuntimeError("TOMBSTONE_CONFLICT:" + str(path))
        return
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix="." + path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def inventory(path: Path) -> dict[str, str]:
    return {item.name: sha(item) for item in sorted(path.iterdir()) if item.is_file()}


def build(root: Path, cutoff: str, revision: int) -> dict:
    data_dir = root / f"data/forward/observations/{cutoff}/revision_{revision}"
    report_dir = root / f"reports/forward/{cutoff}/revision_{revision}"
    if not data_dir.is_dir() or not report_dir.is_dir():
        raise RuntimeError("REVISION_EVIDENCE_MISSING")
    manifest_path = report_dir / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("REVISION_MANIFEST_MISSING")
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    mismatches = {}
    for name, expected in manifest.get("files", {}).items():
        path = report_dir / name
        if not path.is_file():
            path = data_dir / name
        actual = sha(path) if path.is_file() else None
        if actual != expected:
            mismatches[name] = {"expected": expected, "actual": actual}
    if not mismatches:
        raise RuntimeError("VALID_REVISION_CANNOT_BE_TOMBSTONED")
    latest = latest_revision(root, cutoff)
    return {
        "version": "forward-invalid-revision-tombstone-v1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cutoff": cutoff,
        "revision": revision,
        "status": "INVALID_PRESERVED",
        "reason": "MANIFEST_HASH_MISMATCH",
        "mismatches": mismatches,
        "data_files": inventory(data_dir),
        "report_files": inventory(report_dir),
        "evidence_modified": False,
        "latest_valid_revision": None if latest is None else int(latest.name.split("_")[-1]),
        "next_unused_revision": next_revision_number(root, cutoff),
        "reader_policy": "INVALID_REVISION_SKIPPED",
        "writer_policy": "OCCUPIED_REVISION_NUMBER_NEVER_REUSED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--revision", required=True, type=int)
    args = parser.parse_args()
    value = build(ROOT, args.cutoff, args.revision)
    target = ROOT / f"reports/forward/repairs/{args.cutoff}/revision_{args.revision}/TOMBSTONE.json"
    atomic_json(target, value)
    atomic_json(target.parent / "manifest.json", {"version": "forward-repair-manifest-v1.0", "files": {target.name: sha(target)}})
    print(json.dumps({"status": value["status"], "path": str(target), "next_unused_revision": value["next_unused_revision"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
