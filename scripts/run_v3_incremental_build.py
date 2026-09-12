"""Run a serialized V3 P04-02 plan against prepared domain frames.

The JSON input is an execution hand-off, not a source snapshot.  Source
readers prepare the frames; this command only validates the plan, delegates to
registered P02/P03 writers, and atomically writes the growth report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from workbench_service.build_planner import task_key
from workbench_service.incremental_writer import (
    IncrementalBuildCoordinator,
    PreparedBuildObject,
    SnapshotBinding,
    write_growth_report,
)


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute a V3 P04-02 incremental build plan")
    parser.add_argument("input", type=Path, help="JSON hand-off containing plan and prepared frame rows")
    parser.add_argument("--database", type=Path, required=True, help="DuckDB database to update")
    parser.add_argument("--output", type=Path, required=True, help="atomic growth-report output path")
    parser.add_argument("--tdx-root", type=Path, default=Path("D:/new_tdx"), help="read-only TDX root used for output guard")
    args = parser.parse_args()

    payload = _read(args.input)
    plan = payload["plan"]
    planned = {task_key(item): item for item in plan.get("tasks", [])}
    objects = []
    for item in payload.get("objects", []):
        item_key = str(item.get("task_key") or "")
        task = planned.get(item_key)
        if task is None:
            raise ValueError(f"OBJECT_NOT_IN_PLAN:{item_key}")
        objects.append(
            PreparedBuildObject.from_frame(
                task,
                pd.DataFrame(item["rows"]),
                plan_id=plan["plan_id"],
                contract_id=item["contract_id"],
                basis=item.get("basis") or {},
                dependency_hash=item.get("dependency_hash"),
                primary_key=item.get("primary_key"),
                slice_id=item.get("slice_id"),
                covered_task_keys=item.get("covered_task_keys", []),
            )
        )
    snapshot_payload = payload.get("snapshot")
    snapshot = SnapshotBinding(**snapshot_payload) if snapshot_payload else None
    report = IncrementalBuildCoordinator(args.database).execute(plan, objects, snapshot=snapshot)
    _ensure_not_tdx(args.output, args.tdx_root)
    write_growth_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
