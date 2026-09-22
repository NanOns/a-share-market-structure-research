"""Non-blocking daily turnover enhancement and shadow observation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from production.release import atomic_write_json  # noqa: E402
from workbench_analysis.turnover_shadow_v3_3 import build_observation, canonical_observations, load_all, report, seal  # noqa: E402
from workbench_service.research_bundle_v3_3 import read_active  # noqa: E402
from workbench_service.today_research_bundle import TodayResearchBundleReader  # noqa: E402
from workbench_service.turnover_enrichment_service import TurnoverEnrichmentService  # noqa: E402


POINTER = ROOT / "data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json"
STORE = ROOT / "data/turnover_shadow_v3_3"
REPORT_ROOT = ROOT / "reports/p12_14/daily"


def run(publication_id: str, trade_date: str) -> dict:
    active = read_active(POINTER)
    if not active:
        return {"status": "OPTIONAL_SKIPPED", "reason": "ACTIVE_BUNDLE_NOT_BUILT", "local_pipeline_blocked": False}
    identity = active["identity"]
    if str(identity.get("publication_id")) != publication_id or str(identity.get("trade_date")) != trade_date:
        return {"status": "OPTIONAL_SKIPPED", "reason": "ACTIVE_IDENTITY_MISMATCH", "local_pipeline_blocked": False}
    existing = canonical_observations(load_all(STORE))
    matched = next((item for item in existing if item["bundle_digest"] == active["output_digest"] and item["trade_date"] == trade_date), None)
    if matched and int(matched.get("bound_count") or 0) > 0:
        summary = report(existing)
        return {"status": "OPTIONAL_READY", "reused": True, "observation_digest": matched["observation_digest"], "bound_count": matched["bound_count"], "summary": summary, "local_pipeline_blocked": False}

    reader = TodayResearchBundleReader(ROOT, POINTER)
    enrichment = TurnoverEnrichmentService(ROOT, reader).load(expected_digest=active["output_digest"])
    observation = build_observation(active=active, enrichment=enrichment, captured_at_utc=datetime.now(timezone.utc).isoformat())
    sealed = seal(STORE, observation)
    summary = report(load_all(STORE))
    receipt = {
        "stage": "P12-14_DAILY_OPTIONAL_TURNOVER",
        "status": "OPTIONAL_READY" if observation["bound_count"] else "OPTIONAL_DEGRADED",
        "reused": sealed["reused"],
        "publication_id": publication_id,
        "trade_date": trade_date,
        "bundle_digest": active["output_digest"],
        "source_status": enrichment.get("status"),
        "source_error": enrichment.get("source_error"),
        "observation_digest": observation["observation_digest"],
        "requested_count": observation["requested_count"],
        "bound_count": observation["bound_count"],
        "summary": summary,
        "local_pipeline_blocked": False,
        "core_score_or_category_rank_changed": False,
        "raw_payload_persisted": False,
    }
    atomic_write_json(REPORT_ROOT / trade_date / f"{observation['observation_digest']}.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publication-id", required=True)
    parser.add_argument("--trade-date", required=True)
    args = parser.parse_args()
    try:
        result = run(args.publication_id, args.trade_date)
    except Exception as exc:
        result = {"status": "OPTIONAL_DEGRADED", "reason": type(exc).__name__, "local_pipeline_blocked": False}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
