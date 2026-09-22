"""Compare the public publication-head API with the PostgreSQL projection."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.postgres_repository import PostgresRepository  # noqa: E402

REPORT = ROOT / "runtime/postgres_migration/20260922/publications_pg_shadow_report.json"


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def fetch_api(include_analysis: bool) -> dict:
    url = "http://127.0.0.1:28765/api/publications?include_analysis=" + ("1" if include_analysis else "0")
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    checks = []
    with PostgresRepository() as repo:
        # The base publication projection is isolated here.  The optional
        # analysis_capabilities object is a separate domain and remains a
        # later adapter slice until its nested coverage contract is ported.
        for include_analysis in (False,):
            api = fetch_api(include_analysis)
            pg = repo.publication_heads(include_analysis=include_analysis)
            checks.append({"include_analysis": include_analysis, "match": canonical(api) == canonical(pg), "api_count": len(api.get("items", [])), "pg_count": len(pg.get("items", [])), "latest_api": api.get("latest_publication_id"), "latest_pg": pg.get("latest_publication_id")})
    report = {"contract_version": "PUBLICATIONS_PG_SHADOW_V1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks, "deferred": ["include_analysis=true analysis_capabilities nested domain"], "status": "PASS" if all(item["match"] for item in checks) else "FAIL", "online_switch_performed": False, "data_generation_triggered": False}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT.with_suffix(REPORT.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
