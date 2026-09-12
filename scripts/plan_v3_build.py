"""Render a V3 P04-01 build plan from dependency-summary JSON.

The input and output are planning artifacts only.  This command never writes
TDX inputs, analysis rows, publications, or snapshots.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from workbench_service.build_planner import build_plan


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def _ensure_not_tdx(path: Path, tdx_root: Path) -> None:
    resolved = path.resolve()
    root = tdx_root.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return
    raise ValueError(f"TDX_OUTPUT_FORBIDDEN:{resolved}")


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a V3 P04-01 minimum invalidation build plan")
    parser.add_argument("input", type=Path, help="JSON object containing previous/current summaries and planning context")
    parser.add_argument("--output", type=Path, help="optional plan JSON path; stdout is used when omitted")
    parser.add_argument("--tdx-root", type=Path, default=Path("D:/new_tdx"), help="read-only TDX root used for output guard")
    args = parser.parse_args()

    payload = _read(args.input)
    plan = build_plan(
        payload.get("previous"),
        payload["current"],
        sessions=payload["sessions"],
        security_ids=payload.get("security_ids", []),
        sector_ids=payload.get("sector_ids", []),
        security_to_sectors=payload.get("security_to_sectors"),
        sector_members=payload.get("sector_members"),
        cutoff_date=payload.get("cutoff_date"),
        lookbacks=payload.get("lookbacks"),
    )
    if args.output:
        _ensure_not_tdx(args.output, args.tdx_root)
        _atomic_write(args.output, plan)
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
