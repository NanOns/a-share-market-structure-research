"""Backfill V3 source-file manifests from sealed local bundle receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_service.source_catalog import backfill_source_file_catalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    database = (args.database or root / "data/database/market_research.duckdb").resolve()
    receipts = sorted((root / "data/source_bundles").glob("*/source_bundle.json"))
    bundles = [json.loads(path.read_text(encoding="utf-8")) for path in receipts]
    with duckdb.connect(str(database)) as connection:
        result = backfill_source_file_catalog(connection, bundles=bundles)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
