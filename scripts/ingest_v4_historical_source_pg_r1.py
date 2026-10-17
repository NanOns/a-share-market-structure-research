"""Explicit one-time SourceIngress into the existing V4 PostgreSQL fact store."""
from __future__ import annotations

import argparse
from collections import deque
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from workbench_db.v4_forward_pg_r1 import ForwardFactStore
from workbench_db.v4_historical_source_ingress_pg_r1 import FOLDER, ingest_file, source_id_for_path


def _load_project_environment() -> None:
    env_file = ROOT / "config/.env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True, metavar="PROJECT_RELATIVE_PATH")
    parser.add_argument("--follow-bound-files", action="store_true",
                        help="also ingest exact project-relative path/digest references found in source manifests")
    args = parser.parse_args(argv)
    _load_project_environment()
    store = ForwardFactStore(ROOT, FOLDER)
    results = []
    queue = deque()
    queued: set[tuple[str, str]] = set()
    for relative in args.source:
        if not relative.strip():
            raise ValueError("SOURCE_PROJECT_RELATIVE_PATH_REQUIRED")
        normalized = Path(relative.strip()).as_posix()
        item = (source_id_for_path(normalized), (ROOT / normalized).resolve(), None)
        queue.append(item)
        queued.add((item[0], str(item[1])))
    seen: set[tuple[str, str]] = set()
    while queue:
        source_id, path, expected_sha = queue.popleft()
        resolved = path.resolve()
        if not resolved.is_relative_to(ROOT):
            continue
        marker = (source_id, str(resolved))
        if marker in seen:
            continue
        seen.add(marker)
        try:
            result = ingest_file(ROOT, source_id, resolved, expected_sha256=expected_sha, store=store)
        except ValueError as exc:
            raise ValueError(f"{resolved.relative_to(ROOT).as_posix()}:{exc}") from exc
        results.append(result)
        if not args.follow_bound_files:
            continue
        try:
            decoded = json.loads(resolved.read_bytes())
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        stack = [decoded]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                ref_path = value.get("path")
                ref_sha = value.get("sha256") or value.get("hash")
                if isinstance(ref_path, str) and isinstance(ref_sha, str) and len(ref_sha) == 64:
                    candidate = Path(ref_path)
                    if not candidate.is_absolute():
                        candidate = ROOT / candidate
                    try:
                        candidate = candidate.resolve()
                        candidate.relative_to(ROOT)
                    except (OSError, ValueError):
                        candidate = None
                    if candidate is not None and candidate.is_file():
                        if candidate.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".csv"}:
                            continue
                        if candidate.stat().st_size > 5_000_000:
                            continue
                        relative = candidate.relative_to(ROOT).as_posix()
                        item = (source_id_for_path(relative), candidate, ref_sha if "sha256" in value else None)
                        marker = (item[0], str(item[1]))
                        if marker not in queued:
                            queue.append(item)
                            queued.add(marker)
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
    print(json.dumps({"contract_id": "V4_HISTORICAL_SOURCE_INGRESS_PG_R1",
                      "status": "INGESTED_OR_ALREADY_PRESENT", "source_count": len(results),
                      "sources": [{k: row[k] for k in ("source_id", "source_path", "source_sha256", "source_bytes")}
                                  for row in results]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
