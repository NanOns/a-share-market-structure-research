"""Build R4 market identities and equal-weight 1/3/5 references from frozen inputs."""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from statistics import fmean
import gzip
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.replay_r4_identity import accepted_universe_snapshot_id, adjustment_basis_id, digest, target_market_snapshot_id

TARGET = "2026-09-28"
TARGET_INT = 20260928
SNAPSHOT_OUT = ROOT / "reports/v4_05/V4_05_R4_TARGET_MARKET_SNAPSHOT.json"
IDENTITY_OUT = ROOT / "reports/v4_05/V4_05_R4_MARKET_SNAPSHOT_IDENTITY.json"
REFERENCE_OUT = ROOT / "reports/v4_05/V4_05_R4_MARKET_REFERENCE.json"


def sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iso_day(value: int | str) -> str:
    text = str(value)
    return text if "-" in text else f"{text[:4]}-{text[4:6]}-{text[6:8]}"


def atomic_json(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> dict:
    r3_daily_receipt = json.loads((ROOT / "reports/v4_05/V4_05_R3_DAILY_HISTORY_RECEIPT.json").read_text(encoding="utf-8"))
    r3_daily_path = ROOT / r3_daily_receipt["artifact_path"]
    if sha(r3_daily_path) != r3_daily_receipt["artifact_sha256"]:
        raise ValueError("daily history receipt mismatch")
    accepted_v401_path = ROOT / "data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz"
    accepted_v401 = json.loads((ROOT / "data/v4/V4_01_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    if sha(accepted_v401_path) != accepted_v401["historical_universe"]["sha256"]:
        raise ValueError("accepted V4-01 universe source changed")
    go_forward_head_path = ROOT / "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json"
    go_forward_head = json.loads(go_forward_head_path.read_text(encoding="utf-8"))
    target_path = ROOT / go_forward_head["accepted_candidate"]["path"]
    if sha(target_path) != go_forward_head["accepted_candidate"]["sha256"]:
        raise ValueError("accepted V4-02 go-forward source changed")
    calendar_receipt = json.loads((ROOT / "reports/v4_05/V4_05_R3_CALENDAR_RECEIPT.json").read_text(encoding="utf-8"))
    calendar_ref = calendar_receipt["calendar_bindings"]["SSE"]
    calendar_path = ROOT / calendar_ref["path"]
    if sha(calendar_path) != calendar_ref["sha256"]:
        raise ValueError("calendar changed")
    calendar = json.loads(calendar_path.read_text(encoding="utf-8"))["session_dates"]
    target_index = calendar.index(TARGET)
    starts = {h: calendar[target_index - h] for h in (1, 3, 5)}
    relevant_dates = {TARGET, *starts.values()}

    start_rows: dict[str, list[dict]] = defaultdict(list)
    with gzip.open(accepted_v401_path, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            day = row["trade_date"]
            if day in starts.values() and row["board_scope"] in ("SH_MAIN", "SZ_MAIN", "STAR", "CHINEXT"):
                start_rows[day].append(row)
    if set(start_rows) != set(starts.values()):
        raise ValueError("one or more accepted V4-01 start sessions are absent")
    start_meta = {}
    for horizon, start in starts.items():
        rows = start_rows[start]
        ids = [row["security_id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate V4-01 start identity {start}")
        start_meta[str(horizon)] = {
            "start_session": start, "member_count": len(rows),
            "snapshot_id": accepted_universe_snapshot_id(rows),
            "snapshot_identity_algorithm_id": "V4_03_UNIVERSE_SNAPSHOT_IDENTITY_V1",
            "source_artifact": accepted_v401_path.relative_to(ROOT).as_posix(),
            "source_artifact_sha": sha(accepted_v401_path),
            "source_head_sha": sha(ROOT / "data/v4/V4_01_ACCEPTED_HEAD.json"),
        }

    target_members: dict[str, dict] = {}
    with gzip.open(target_path, "rt", encoding="utf-8") as source:
        for line in source:
            source_row = json.loads(line)
            sid = source_row["security_id"]
            if sid in target_members:
                raise ValueError(f"duplicate target identity {sid}")
            source_revision = digest([TARGET, source_row["raw_source_snapshot_id"], source_row["raw_source_digest"],
                                      source_row["adjustment_snapshot_id"], source_row["adjustment_snapshot_digest"]])
            target_members[sid] = {
                "target_trade_date": TARGET, "security_id": sid,
                "source_security_key": source_row["source_security_key"], "board_scope": source_row["board_scope"],
                "membership_basis": "V4_02_GO_FORWARD_PIT_ACCEPTED_CANDIDATE_ROW",
                "source_revision_id": source_revision,
                "eligibility_status": source_row["adjusted_quality"],
                "raw_source_snapshot_id": source_row["raw_source_snapshot_id"],
                "raw_source_digest": source_row["raw_source_digest"],
                "adjustment_snapshot_id": source_row["adjustment_snapshot_id"],
                "adjustment_snapshot_digest": source_row["adjustment_snapshot_digest"],
                "coordinate_basis": source_row["coordinate_basis"],
                "max_source_trade_date": source_row["max_source_trade_date"],
                "source_contract_id": source_row["contract_id"],
                "source_contract_sha256": source_row["contract_sha256"],
            }
    if len(target_members) != 5222:
        raise ValueError(f"target identities changed: {len(target_members)}")

    endpoints: dict[tuple[str, str], dict] = {}
    target_daily = {}
    with gzip.open(r3_daily_path, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            day = iso_day(row["trade_date"])
            if day in relevant_dates:
                endpoints[(day, row["security_id"])] = row
                if day == TARGET:
                    target_daily[row["security_id"]] = row
    if not set(target_daily).issubset(target_members):
        raise ValueError("daily target bars outside accepted target member set")

    # Confirm accepted candidate target endpoint identities against the R3 replay history.
    for sid, identity in target_members.items():
        bar = target_daily.get(sid)
        if identity["eligibility_status"] == "ADJUSTED_READY":
            if bar is None or bar["qfq_ohlc"] is None:
                raise ValueError(f"accepted adjusted endpoint missing from replay history: {sid}")
            if bar["raw_package_identity"] != identity["raw_source_snapshot_id"].removeprefix("sha256-") or bar["gbbq_snapshot_identity"] != identity["adjustment_snapshot_id"]:
                raise ValueError(f"endpoint source identity drift: {sid}")

    target_id = target_market_snapshot_id(TARGET, target_members.values())
    target_basis_rows = []
    for sid, bar in target_daily.items():
        if bar["adjusted_quality"] == "READY" and bar["qfq_ohlc"] is not None:
            target_basis_rows.append((sid, bar["coordinate_basis"], bar["gbbq_snapshot_identity"], bar["raw_package_identity"]))
    target_basis_id = adjustment_basis_id(target_basis_rows)
    snapshot = {"contract_id": "V4_05_TARGET_MARKET_SNAPSHOT_IDENTITY_V1", "target_trade_date": TARGET,
                "member_count": len(target_members), "market_snapshot_id": target_id,
                "membership_semantics": "exact rows from externally accepted V4-02 go-forward T0 target candidate",
                "source_candidate_path": target_path.relative_to(ROOT).as_posix(),
                "source_candidate_sha256": sha(target_path), "source_head_path": go_forward_head_path.relative_to(ROOT).as_posix(),
                "source_head_sha256": sha(go_forward_head_path),
                "identity_algorithm": "SHA256(canonical_json({contract_id,target_trade_date,sorted(security_id,source_security_key,membership_basis,source_revision_id,eligibility_status)}))",
                "coordinate_basis": "T0_CURRENT_COORDINATE", "historical_as_recorded_claim": False,
                "target_adjustment_basis_id": target_basis_id,
                "identities": sorted(target_members.values(), key=lambda row: row["security_id"])}
    atomic_json(SNAPSHOT_OUT, snapshot)

    market_calendar_id = "V4_05_MARKET_CALENDAR_V1:" + digest({name: binding["sha256"] for name, binding in calendar_receipt["calendar_bindings"].items()})
    input_digest = digest({"daily_history_sha256": sha(r3_daily_path), "accepted_v4_01_universe_sha256": sha(accepted_v401_path),
                           "accepted_v4_02_target_candidate_sha256": sha(target_path), "calendar_identity": calendar_receipt["calendar_bindings"]})
    horizons = {}
    for horizon, start in starts.items():
        members = sorted(row["security_id"] for row in start_rows[start])
        values, basis_members = {}, []
        for sid in members:
            first = endpoints.get((start, sid))
            last = endpoints.get((TARGET, sid))
            if not first or not last or not first.get("qfq_ohlc") or not last.get("qfq_ohlc"):
                continue
            if first["adjusted_quality"] != "READY" or last["adjusted_quality"] != "READY":
                continue
            basis = (last["coordinate_basis"], last["gbbq_snapshot_identity"], last["raw_package_identity"])
            basis_start = (first["coordinate_basis"], first["gbbq_snapshot_identity"], first["raw_package_identity"])
            if basis != basis_start:
                continue
            start_close, end_close = float(first["qfq_ohlc"][3]), float(last["qfq_ohlc"][3])
            if start_close <= 0:
                continue
            values[sid] = end_close / start_close - 1
            basis_members.append((sid, *basis))
        count, evaluable = len(members), len(values)
        missing = count - evaluable
        coverage = evaluable / count if count else None
        reason = "EMPTY_START_UNIVERSE" if count == 0 else "MISSING_COVERAGE_EXCEEDED" if missing / count > 0.2 else None
        reference = fmean(values.values()) if values and reason is None else None
        identity = {"market_calendar_id": market_calendar_id, "start_session": start, "end_session": TARGET,
                    "start_universe_snapshot_id": start_meta[str(horizon)]["snapshot_id"],
                    "evaluable_set_identity": digest(sorted(values)), "adjustment_basis_id": adjustment_basis_id(basis_members)}
        row = {"contract_id": "MARKET_RELATIVE_REFERENCE_V1", "contract_version": "1.0.0",
               "parameter_set_id": "V4_03_CORE_FACTOR_PARAMETER_SET_V1", "target_trade_date": TARGET,
               "horizon_sessions": horizon, **identity, "window_identity": digest(identity),
               "input_source_digest": input_digest,
               "input_endpoint_basis": "T0_CURRENT_COORDINATE + frozen GBBQ + Sep-28 raw source package",
               "reference_return": reference, "universe_count": count, "evaluable_count": evaluable,
               "missing_count": missing, "coverage": coverage,
               "quality_state": "UNKNOWN" if reason else "OBSERVED", "unknown_reason": reason,
               "max_source_trade_date": TARGET_INT, "formal_publication_at": "2026-09-29T06:53:52+00:00",
               "historical_as_recorded_claim": False}
        row["output_digest"] = digest(row)
        horizons[str(horizon)] = row

    reference_receipt = {"contract_id": "V4_05_R4_MARKET_REFERENCE_V1",
                         "status": "PASS" if all(row["quality_state"] == "OBSERVED" for row in horizons.values()) else "DEGRADED_PASS",
                         "target_trade_date": TARGET, "market_calendar_id": market_calendar_id,
                         "target_market_snapshot_id": target_id, "target_adjustment_basis_id": target_basis_id,
                         "horizons": horizons, "start_universe_provenance": start_meta,
                         "accepted_v4_01_universe_sha256": sha(accepted_v401_path),
                         "accepted_v4_02_target_candidate_sha256": sha(target_path),
                         "daily_history_sha256": sha(r3_daily_path), "calendar_sha256": calendar_ref["sha256"],
                         "max_source_trade_date": TARGET_INT}
    atomic_json(IDENTITY_OUT, {"contract_id": "V4_05_R4_MARKET_SNAPSHOT_IDENTITY_V1", "status": "PASS",
                               "target_trade_date": TARGET, "target_market_snapshot_id": target_id,
                               "target_market_snapshot_artifact": SNAPSHOT_OUT.relative_to(ROOT).as_posix(),
                               "target_market_snapshot_sha256": sha(SNAPSHOT_OUT),
                               "target_member_count": len(target_members), "target_adjustment_basis_id": target_basis_id,
                               "target_identity_algorithm_id": "V4_05_TARGET_MARKET_SNAPSHOT_IDENTITY_V1",
                               "start_universe_snapshots": start_meta,
                               "historical_as_recorded_claim": False})
    atomic_json(REFERENCE_OUT, reference_receipt)
    return reference_receipt


if __name__ == "__main__":
    result = main()
    print(json.dumps({h: {"return": row["reference_return"], "coverage": row["coverage"],
                          "snapshot_id": row["start_universe_snapshot_id"], "basis_id": row["adjustment_basis_id"]}
                      for h, row in result["horizons"].items()}, ensure_ascii=False, sort_keys=True))
