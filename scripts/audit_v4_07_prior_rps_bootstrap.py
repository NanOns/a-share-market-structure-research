from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def write_json(path: Path, value: dict) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")


def read_jsonl_gzip(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def main() -> int:
    v405_head_path = ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json"
    v405_head = json.loads(v405_head_path.read_text(encoding="utf-8"))
    accepted_factors = v405_head["accepted_artifacts"]["full_scope_factors"]
    accepted_path = ROOT / accepted_factors["path"]
    accepted_rows = list(read_jsonl_gzip(accepted_path))
    factor_names = ("rps5_delta1", "rps5_delta3", "rps20_delta3")
    accepted_quality = Counter()
    accepted_reasons = Counter()
    accepted_null_values = Counter()
    output_digest_null = Counter()
    for row in accepted_rows:
        for name in factor_names:
            value = row.get("fields", {}).get(name, {})
            accepted_quality[f"{name}:{value.get('quality_state')}"] += 1
            if value.get("unknown_reason"):
                accepted_reasons[f"{name}:{value['unknown_reason']}"] += 1
            if value.get("value") is None:
                accepted_null_values[name] += 1
            if value.get("output_digest") is None:
                output_digest_null[name] += 1

    r3_prior_path = ROOT / "reports/v4_03/staging/V4_03_PRIOR_RPS_STAGING_R3.json"
    r3_prior_receipt_path = ROOT / "reports/v4_03/V4_03_PRIOR_RPS_STAGING_RECEIPT_R3.json"
    r3_scope_path = ROOT / "reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz"
    r3_scope_receipt_path = ROOT / "reports/v4_03/V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_R3.json"
    r3_postcheck_path = ROOT / "reports/v4_03/V4_03_INDEPENDENT_POSTCHECK_R3.json"
    r3_prior_receipt = json.loads(r3_prior_receipt_path.read_text(encoding="utf-8"))
    r3_scope_receipt = json.loads(r3_scope_receipt_path.read_text(encoding="utf-8"))
    r3_postcheck = json.loads(r3_postcheck_path.read_text(encoding="utf-8"))
    r3_rows = list(read_jsonl_gzip(r3_scope_path))
    r3_quality = Counter()
    sample = None
    for row in r3_rows:
        for name in factor_names:
            value = row.get("fields", {}).get(name, {})
            r3_quality[f"{name}:{value.get('quality_state')}"] += 1
        if sample is None:
            candidate = row.get("fields", {}).get("rps5_delta3", {})
            if candidate.get("quality_state") == "OBSERVED":
                sample = {
                    "security_id": row.get("security_id"), "field": "rps5_delta3",
                    "value": candidate.get("value"), "start_session": candidate.get("start_session"),
                    "end_session": candidate.get("end_session"),
                    "start_universe_snapshot_id": candidate.get("start_universe_snapshot_id"),
                    "universe_snapshot_id": candidate.get("universe_snapshot_id"),
                    "adjustment_basis_id": candidate.get("adjustment_basis_id"),
                    "output_digest": candidate.get("output_digest"),
                }
    rev2_path = ROOT / "docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md"
    relative_path = ROOT / "src/v4/factors/relative.py"
    open_audit_path = ROOT / "reports/audits/V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_AUDIT_20260930.md"
    accepted_artifact_keys = sorted(v405_head.get("accepted_artifacts", {}).keys())
    source_bindings = {
        path.relative_to(ROOT).as_posix(): {"sha256": sha(path), "byte_count": path.stat().st_size}
        for path in (
            v405_head_path, accepted_path, r3_prior_path, r3_prior_receipt_path, r3_scope_path,
            r3_scope_receipt_path, r3_postcheck_path, rev2_path, relative_path, open_audit_path,
        )
    }
    checks = {
        "accepted_factor_artifact_hash_matches_head": sha(accepted_path) == accepted_factors["sha256"],
        "accepted_factor_row_count_matches_head": len(accepted_rows) == 5222,
        "accepted_prior_rps_delta_fields_all_unknown": all(accepted_quality[f"{name}:UNKNOWN"] == 5222 for name in factor_names),
        "accepted_prior_rps_unknown_reason_is_bootstrap": all(accepted_reasons[f"{name}:BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY"] == 5222 for name in factor_names),
        "accepted_delta_output_digests_absent": all(output_digest_null[name] == 5222 for name in factor_names),
        "r3_prior_artifact_hash_matches_receipt": sha(r3_prior_path) == r3_prior_receipt["artifact_sha256"],
        "r3_prior_receipt_is_not_acceptance": r3_prior_receipt["status"] == "STAGING_NOT_STAGE_ACCEPTANCE",
        "r3_full_scope_hash_matches_receipt": sha(r3_scope_path) == r3_scope_receipt["output_sha256"],
        "r3_postcheck_passes_for_same_prior_artifact": r3_postcheck["status"] == "PASS" and r3_postcheck["prior_artifact_sha256"] == r3_prior_receipt["artifact_sha256"],
        "r3_candidate_not_stage_accepted": r3_scope_receipt["status"] == "FULL_47_FIELD_CANDIDATE_NOT_STAGE_ACCEPTANCE",
        "accepted_v405_head_has_no_prior_rps_artifact_binding": not any("prior_rps" in str(key).lower() for key in accepted_artifact_keys),
    }
    evidence = {
        "contract_id": "V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R1",
        "audit_item": "V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01",
        "status": "INVESTIGATION_COMPLETE_REPAIR_AND_NEW_ACCEPTED_PUBLICATION_OPEN",
        "audit_status": "OPEN",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source_bindings": source_bindings,
        "accepted_v405": {
            "accepted_head_path": v405_head_path.relative_to(ROOT).as_posix(), "accepted_head_sha256": sha(v405_head_path),
            "target_trade_date": v405_head["target_trade_date"], "formal_publication_at": "2026-09-29T06:53:52Z",
            "core_logical_digest": v405_head["accepted_artifacts"]["core_profile"]["logical_digest"],
            "factor_artifact_path": accepted_factors["path"], "factor_artifact_sha256": sha(accepted_path),
            "factor_artifact_logical_digest": accepted_factors["logical_digest"], "row_count": len(accepted_rows),
            "prior_rps_quality_counts": dict(sorted(accepted_quality.items())),
            "prior_rps_unknown_reason_counts": dict(sorted(accepted_reasons.items())),
            "null_values_by_field": dict(sorted(accepted_null_values.items())),
            "null_output_digests_by_field": dict(sorted(output_digest_null.items())),
            "accepted_artifact_keys": accepted_artifact_keys,
        },
        "v403_r3_staging": {
            "prior_rps_artifact_path": r3_prior_path.relative_to(ROOT).as_posix(),
            "prior_rps_artifact_sha256": sha(r3_prior_path),
            "prior_rps_source_digest": r3_prior_receipt["source_digest"],
            "prior_rps_receipt_status": r3_prior_receipt["status"],
            "prior_rps_coordinates": r3_prior_receipt["prior_coordinates"],
            "full_scope_candidate_path": r3_scope_path.relative_to(ROOT).as_posix(),
            "full_scope_candidate_sha256": sha(r3_scope_path),
            "full_scope_candidate_status": r3_scope_receipt["status"],
            "full_scope_candidate_rows": len(r3_rows),
            "rps_delta_quality_counts": dict(sorted(r3_quality.items())),
            "independent_postcheck_status": r3_postcheck["status"],
            "independent_postcheck_rows": r3_postcheck["rows_checked"],
            "sample_observed_value": sample,
        },
        "exact_requirement": {
            "contract_sections": ["REV2 §10.0 CORE_FACTOR_V1", "REV2 §10.0 RELATIVE_CHANGE"],
            "rps_formula": "RPS_N is a same-session cross-sectional midrank of retN over that date's evaluable universe; retN uses the frozen N-session window; n<2 is UNKNOWN.",
            "delta_offsets": {
                "rps5_delta1": {"current_field": "rps5[t]", "prior_field": "rps5[t-1]"},
                "rps5_delta3": {"current_field": "rps5[t]", "prior_field": "rps5[t-3]"},
                "rps20_delta3": {"current_field": "rps20[t]", "prior_field": "rps20[t-3]"},
            },
            "required_identity_per_prior_score": ["market_calendar_id", "prior_trade_date", "prior RPS contract/version", "prior accepted artifact digest", "prior universe snapshot id", "adjustment basis id", "source digest"],
            "code_guard": "src/v4/factors/relative.py requires prior artifact digest and prior universe snapshot id; missing either raises ValueError. It does not synthesize prior scores from raw history.",
            "warmup": "300 market days is a planning target only; each factor's first available date must be measured and reported independently. A delta is not available until both the current RPS and each required accepted prior-session RPS are available with matching calendar/universe/adjustment identities.",
        },
        "why_r3_values_cannot_be_copied": [
            "V4-03 R3 computed prior scores from a stage-owned historical staging artifact and produced independently recomputed candidate deltas.",
            "Its source receipt explicitly says STAGING_NOT_STAGE_ACCEPTANCE and the 47-field artifact says FULL_47_FIELD_CANDIDATE_NOT_STAGE_ACCEPTANCE.",
            "V4-05's accepted R4.1 factor publication independently records all three delta fields as UNKNOWN with BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY, null value and null output_digest for all 5,222 identities.",
            "The R3 prior artifact digest/universe binding was not included among V4-05 accepted artifact bindings, so copying R3 values would splice an unaccepted source into an accepted publication.",
        ],
        "repair_blocker": "No new independently accepted point-in-time prior-RPS publication chain is present. Building one requires accepted session calendars and dated start-universe snapshots at each prior session, prior RPS cross-sections, same adjustment/source identities, first-available/warm-up reconciliation, independent recomputation, and a new accepted V4-05 factor publication. The current audit has no authority to promote such a candidate.",
        "prohibited_changes_preserved": ["V4-07 thresholds unchanged", "UNKNOWN not coerced to FALSE", "V4-05 accepted artifacts not rewritten", "V4-03 staging values not consumed", "raw history not reconstructed inside V4-07"],
        "new_rps_candidate_created": False,
        "new_accepted_factor_publication_created": False,
        "real_base_seed_signal_capability": "DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN",
        "checks": checks,
        "checks_pass": all(checks.values()),
    }
    json_path = ROOT / "reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R1.json"
    write_json(json_path, evidence)
    doc_path = ROOT / "reports/audits/V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_AUDIT_ADDENDUM_20260930.md"
    doc = f"""# Prior-RPS Bootstrap Repair Audit Addendum — 2026-09-30

**Audit item:** `V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01`
**Status:** `OPEN`
**Assessment evidence:** `{json_path.relative_to(ROOT).as_posix()}`
**Assessment SHA-256:** `{sha(json_path)}`

## Finding

The accepted V4-05 Full Scope Factors publication for `{v405_head['target_trade_date']}` contains {len(accepted_rows):,} identities. Each of `rps5_delta1`, `rps5_delta3`, and `rps20_delta3` is `UNKNOWN / BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY` for all {len(accepted_rows):,} rows, with null values and null output digests. The accepted head binds the factor artifact `{accepted_factors['path']}` (SHA-256 `{sha(accepted_path)}`; logical digest `{accepted_factors['logical_digest']}`).

The V4-03 R3 candidate computed prior RPS scores from its stage-owned historical staging artifact (SHA-256 `{sha(r3_prior_path)}`; source digest `{r3_prior_receipt['source_digest']}`). Its independent postcheck passed on {r3_postcheck['rows_checked']:,} rows, and the full-scope candidate reported {r3_quality['rps5_delta3:OBSERVED']:,} observed / {r3_quality['rps5_delta3:UNKNOWN']:,} unknown `rps5_delta3` values. The sample value in the candidate is {sample['value'] if sample else 'unavailable'} for its recorded `{sample['start_session'] if sample else 'unknown'}` to `{sample['end_session'] if sample else 'unknown'}` window. But the prior artifact status is `{r3_prior_receipt['status']}`, and the full-scope output is `{r3_scope_receipt['status']}`. They are candidates, not accepted V4-05 inputs, so those values cannot be copied into the accepted factor lineage.

## Exact repair requirement

REV2 §10.0 defines RPS as a same-session cross-sectional midrank of `retN` over the date's evaluable universe. The delta fields require:

- `rps5_delta1 = rps5[t] - rps5[t-1]`
- `rps5_delta3 = rps5[t] - rps5[t-3]`
- `rps20_delta3 = rps20[t] - rps20[t-3]`

Each prior score must bind its accepted prior artifact digest and universe snapshot identity, plus the market calendar, prior trade date, adjustment basis, and source digest. `src/v4/factors/relative.py` rejects missing prior artifact/universe identities and does not synthesize a prior score from raw history. REV2 says the 300-market-day warm-up is a planning target; each field's actual first-available date must be measured independently.

## Open blocker and next action

There is no new independently accepted PIT prior-RPS chain. Repair remains OPEN until a dated, calendar-bound and universe-bound prior score chain is built, independently recomputed, reconciled for first-available/warm-up behavior, and published through a new accepted factor revision. This addendum does not change V4-07 thresholds, consume the V4-03 R3 staging values, rewrite V4-05, or convert UNKNOWN to FALSE. Real Base Seed capability remains `DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN`.
"""
    atomic_write(doc_path, doc.encode("utf-8"))
    print(json.dumps({"status": evidence["status"], "audit_status": "OPEN", "checks_pass": evidence["checks_pass"], "evidence": json_path.relative_to(ROOT).as_posix(), "addendum": doc_path.relative_to(ROOT).as_posix()}, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if evidence["checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
