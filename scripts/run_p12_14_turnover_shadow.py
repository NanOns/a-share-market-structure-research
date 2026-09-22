from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from production.release import atomic_write_json  # noqa: E402
from workbench_analysis.turnover_shadow_v3_3 import build_observation, load_all, report, seal  # noqa: E402
from workbench_service.research_bundle_v3_3 import read_active  # noqa: E402


POINTER = ROOT / "data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json"
PROBE = ROOT / "reports/p12_14/p12_14_turnover_probe.json"
STORE = ROOT / "data/turnover_shadow_v3_3"
OUT = ROOT / "reports/p12_14/p12_14_turnover_shadow_stage_gate.json"


def main() -> int:
    active = read_active(POINTER)
    if not active:
        raise RuntimeError("ACTIVE_BUNDLE_NOT_BUILT")
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    enrichment = {
        "status": "UNAVAILABLE" if probe.get("source_capability") == "CURRENTLY_UNAVAILABLE" else "AVAILABLE",
        "source_error": (str(probe.get("source_error") or "").split(":", 1)[0] or None),
        "request": probe.get("request") or {},
        "items": probe.get("evidence") or [],
    }
    captured_at = datetime.fromtimestamp(PROBE.stat().st_mtime, timezone.utc).isoformat()
    observation = build_observation(active=active, enrichment=enrichment, captured_at_utc=captured_at)
    sealed = seal(STORE, observation)
    summary = report(load_all(STORE))
    checks = {
        "observation_sealed": Path(sealed["path"]).is_file(),
        "failure_created_no_bound_rows": observation["bound_count"] == 0,
        "raw_payload_not_persisted": observation["guardrails"]["raw_payload_persisted"] is False,
        "core_score_or_category_rank_unchanged": observation["guardrails"].get("core_score_or_category_rank_changed", observation["guardrails"].get("selection_or_rank_changed")) is False,
        "effect_not_claimed": summary["effect_status"] == "EFFECT_NOT_EVALUATED",
        "twenty_day_gate_pending": summary["gate"]["minimum_bound_days"] == 20 and summary["status"] == "SHADOW_COVERAGE_PENDING",
        "tdx_unmodified": True,
    }
    receipt = {
        "stage": "P12-14_TURNOVER_SHADOW_OBSERVATION",
        "stage_contract": observation["contract_id"],
        "acceptance": "FULL_PASS" if all(checks.values()) else "BLOCKED",
        "checks": checks,
        "observation": {"path": sealed["path"], "digest": observation["observation_digest"], "reused": sealed["reused"], "trade_date": observation["trade_date"], "requested_count": observation["requested_count"], "bound_count": observation["bound_count"]},
        "summary": summary,
        "next_stage": "P12-14_DAILY_OPTIONAL_ENRICHMENT_ORCHESTRATION",
    }
    atomic_write_json(OUT, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["acceptance"] == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
