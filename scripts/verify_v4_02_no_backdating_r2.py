"""Negative test: a later-only <=T0 event cannot enter the frozen T0 result."""

from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from adjustment.tdx_adjustment import XrxdEvent, build_affine_factors  # noqa: E402

GBBQ_ID = "sha256-775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e"


def main() -> None:
    samples = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_ADJUSTMENT_SAMPLES_R2.json").read_text(encoding="utf-8"))
    example = samples["sample_kinds"]["cash_dividend"]
    key = example["row"]["source_security_key"]
    events = []
    for event in example["visible_event_set"]:
        if event["category"] == 1:
            c = event["c"]
            events.append(XrxdEvent(key, event["date"], Decimal(str(c[0])).quantize(Decimal(".01")),
                                    Decimal(str(c[1])).quantize(Decimal(".01")),
                                    Decimal(str(c[2])).quantize(Decimal(".01")),
                                    Decimal(str(c[3])).quantize(Decimal(".01")), event["index"]))
    dates = [20260924, 20260928]
    baseline = build_affine_factors(dates, events)[20260924]
    later_only = XrxdEvent(key, 20260928, cash_dividend_per_10=Decimal("10"), source_record_index=999999999)
    tagged = [(GBBQ_ID, e) for e in events] + [("SYNTHETIC_LATER_SNAPSHOT", later_only)]
    selected = [e for source_id, e in tagged if source_id == GBBQ_ID]
    frozen = build_affine_factors(dates, selected)[20260924]
    polluted = build_affine_factors(dates, [e for _, e in tagged])[20260924]
    assert (frozen.qfq_mul, frozen.qfq_add) == (baseline.qfq_mul, baseline.qfq_add)
    assert (polluted.qfq_mul, polluted.qfq_add) != (baseline.qfq_mul, baseline.qfq_add)
    later = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_GBBQ_LATER_REVISION_R2.json").read_text(encoding="utf-8"))
    assert later["price_affected_security_count"] == 0
    assert later["later_records_used_for_t0_qfq"] is False
    receipt = {"contract_id": "V4_02_GO_FORWARD_NO_BACKDATING_R2", "status": "PASS",
               "target_trade_date": "2026-09-28", "sample_security_key": key,
               "frozen_snapshot_id": GBBQ_ID, "synthetic_later_only_event_effective_date": 20260928,
               "baseline_pre_t0_factor": [str(baseline.qfq_mul), str(baseline.qfq_add)],
               "frozen_with_later_only_record_factor": [str(frozen.qfq_mul), str(frozen.qfq_add)],
               "polluted_factor_if_later_record_incorrectly_used": [str(polluted.qfq_mul), str(polluted.qfq_add)],
               "later_only_record_influenced_t0": False,
               "actual_later_snapshot_available": True,
               "actual_later_snapshot_id": later["later_snapshot_id"],
               "actual_revision_comparison": later["classification_counts"],
               "actual_late_le_t0_price_affected_security_count": 0}
    path = ROOT / "reports/v4_02/V4_02_GO_FORWARD_NO_BACKDATING_R2.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(receipt["status"])


if __name__ == "__main__":
    main()
