from __future__ import annotations

"""Create an immutable project-managed copy of read-only configured TDX bars."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.tdx_local_snapshot import build_local_snapshot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", default="D:/new_tdx")
    parser.add_argument("--output-root", default=str(ROOT / "data/v4/local_tdx_snapshots"))
    args = parser.parse_args()
    output_root = Path(args.output_root).resolve()
    if not output_root.is_relative_to(ROOT.resolve()):
        raise ValueError("SNAPSHOT_OUTPUT_MUST_BE_PROJECT_MANAGED")
    result = build_local_snapshot(Path(args.source_root), output_root)
    result["manifest_path"] = str(Path(result["manifest_path"]).resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
