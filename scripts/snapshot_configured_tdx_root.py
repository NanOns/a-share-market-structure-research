from __future__ import annotations

"""Create an immutable project-managed copy of read-only configured TDX bars."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.tdx_local_snapshot import build_local_snapshot  # noqa: E402
from common.paths import resolve_tdx_root, resolve_tdx_snapshot_root  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", default=None, help="Override TDX_ROOT/config/paths.yaml")
    parser.add_argument("--output-root", default=None, help="Override TDX_SNAPSHOT_ROOT/config/paths.yaml")
    args = parser.parse_args()
    source_root = resolve_tdx_root(ROOT, args.source_root)
    output_root = resolve_tdx_snapshot_root(ROOT, args.output_root)
    if source_root == output_root or source_root in output_root.parents:
        raise ValueError("SNAPSHOT_OUTPUT_MUST_BE_OUTSIDE_TDX_ROOT")
    result = build_local_snapshot(source_root, output_root)
    result["manifest_path"] = str(Path(result["manifest_path"]).resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
