from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify every file bound by the V4-07 stage manifest.")
    parser.add_argument("manifest", nargs="?", default="reports/v4_07/V4_07_STAGE_CANDIDATE_MANIFEST.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    manifest_path = manifest_path.resolve(strict=True)
    if not manifest_path.is_relative_to(root.resolve()):
        raise ValueError("manifest must be inside the repository root")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ValueError("manifest.files must be an array")
    if manifest.get("scoped_file_count") != len(files):
        raise ValueError("manifest scoped_file_count does not match files array")

    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("each manifest entry must contain a relative path")
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe manifest path: {entry['path']}")
        normalized = relative.as_posix()
        if normalized in seen:
            raise ValueError(f"duplicate manifest path: {normalized}")
        seen.add(normalized)
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f"manifest entry is not a repository file: {normalized}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        size = path.stat().st_size
        if digest != entry.get("sha256") or size != entry.get("byte_count"):
            raise ValueError(f"manifest mismatch: {normalized}")

    if manifest_path.relative_to(root.resolve()).as_posix() in seen:
        raise ValueError("manifest must exclude itself to avoid recursive hashing")
    print(json.dumps({"status": "PASS_MANIFEST_HASHES_AND_BYTE_COUNTS", "verified_file_count": len(files)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
