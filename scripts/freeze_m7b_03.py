"""Freeze local historical inputs for M7B-03 without touching TDX."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_service.app import Api
from workbench_service.source_freezer import SourceFreezer, verify_source_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze M7B-03 local source manifest")
    parser.add_argument("--root", default=".")
    parser.add_argument("--database")
    parser.add_argument("--publication-id")
    parser.add_argument("--days", type=int, default=250)
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    database = Path(args.database).resolve() if args.database else root / "data/database/market_research.duckdb"
    api = Api(database)
    publication_id = args.publication_id or api.publications()["latest_publication_id"]
    coverage = api.history_coverage(publication_id, args.days, "AUTO")["item"]
    output = Path(args.output) if args.output else root / "reports/upgrade_m7" / f"source_manifest_{coverage['cutoff_date'].replace('-', '')}.json"
    manifest = SourceFreezer(root, database).freeze(publication_id, coverage, output_path=output)
    verification = verify_source_manifest(root, manifest)
    print(json.dumps({"step": "M7B-03", "manifest_path": str(output), "manifest_sha256": manifest["manifest_sha256"], "verification": verification}, ensure_ascii=False, indent=2))
    return 0 if verification["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
