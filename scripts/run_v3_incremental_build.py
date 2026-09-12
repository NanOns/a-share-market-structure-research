"""Run a serialized V3 P04-02 plan against prepared or source-backed input.

The JSON input is an execution hand-off.  It may carry prepared domain frames,
or a read-only parquet source for the explicit daily executor matrix.  The
command validates the plan, delegates to registered P02/P03 writers, and
atomically writes the growth report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_service.build_planner import task_key
from workbench_service.incremental_writer import (
    IncrementalBuildCoordinator,
    PreparedBuildObject,
    ReusedBuildObject,
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
    reused = [ReusedBuildObject(**item) for item in payload.get("reused", [])]
    snapshot_payload = payload.get("snapshot")
    snapshot = SnapshotBinding(**snapshot_payload) if snapshot_payload else None
    coordinator = IncrementalBuildCoordinator(args.database)
    source_parquet = payload.get("source_parquet")
    if source_parquet:
        source_path = Path(source_parquet).resolve()
        if not source_path.is_file():
            raise ValueError(f"SOURCE_PARQUET_NOT_FOUND:{source_path}")
        source = pd.read_parquet(source_path)

        def input_provider(task):
            frame = source
            security_ids = task.get("security_ids")
            security_id = task.get("security_id")
            if security_ids is not None and "security_id" in frame.columns:
                frame = frame[frame["security_id"].astype(str).isin({str(value) for value in security_ids})]
            elif security_id is not None and "security_id" in frame.columns:
                frame = frame[frame["security_id"].astype(str).eq(str(security_id))]
            if "date" in frame.columns:
                frame = frame[pd.to_datetime(frame["date"]).dt.date.astype(str) <= str(task["trade_date"])]
            return {
                "frame": frame.copy(),
                "basis": {"source_parquet": str(source_path)},
            }

        if objects:
            raise ValueError("PREPARED_OBJECTS_AND_SOURCE_PARQUET_ARE_MUTUALLY_EXCLUSIVE")
        report = coordinator.execute_daily(plan, input_provider=input_provider, reused=reused, snapshot=snapshot)
    else:
        report = coordinator.execute(plan, objects, reused=reused, snapshot=snapshot)
    _ensure_not_tdx(args.output, args.tdx_root)
    write_growth_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
