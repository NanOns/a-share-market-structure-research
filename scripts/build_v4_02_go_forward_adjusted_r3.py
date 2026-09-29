"""Full required-board Sep-28 T0-coordinate candidate from frozen sources."""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq  # noqa: E402
from tdx.day_reader import DAY_RECORD_LENGTH, decode_record  # noqa: E402
from tdx.gbbq_reader import read_gbbq  # noqa: E402
from src.v4.go_forward_r3 import target_identity, publication_time

TARGET = 20260928
GBBQ_ID = "sha256-775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e"
OUT = ROOT / "reports/v4_02/staging/V4_02_GO_FORWARD_ADJUSTED_T0_CANDIDATE_R3.jsonl.gz"
RECEIPT = ROOT / "reports/v4_02/V4_02_GO_FORWARD_ADJUSTED_DAILY_RECEIPT_R3.json"
SAMPLES = ROOT / "reports/v4_02/V4_02_GO_FORWARD_ADJUSTMENT_SAMPLES_R3.json"


def packed(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def file_sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, encoding="utf-8", newline="\n", delete=False) as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        temp = Path(stream.name)
    os.replace(temp, path)


def main() -> None:
    capture = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R2.json").read_text(encoding="utf-8"))
    universe = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_UNIVERSE_CANDIDATE_R3.json").read_text(encoding="utf-8"))
    overlap = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_RAW_OVERLAP_R2.json").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_TDX_PACKAGE_RECEIPT_R2.json").read_text(encoding="utf-8"))
    if universe["status"] != "PASS_CANDIDATE" or overlap["status"] != "PASS" or package["status"] != "TARGET_DATE_CONTENT_PASS":
        raise ValueError("UPSTREAM_SOURCE_GATE_NOT_PASS")
    gbbq_root = ROOT / "data/v4/source_snapshot_store/gbbq" / GBBQ_ID
    gbbq_manifest = json.loads((gbbq_root / "manifest.json").read_text(encoding="utf-8"))
    if gbbq_manifest["system_available_at"] >= "2026-09-28T23:59:59Z":
        raise ValueError("GBBQ_NOT_VISIBLE_BEFORE_T0")
    for name, ref in gbbq_manifest["files"].items():
        if file_sha(gbbq_root / name) != ref["sha256"]:
            raise ValueError(f"GBBQ_HASH_MISMATCH:{name}")
    gbbq_sha = gbbq_manifest["files"]["gbbq"]["sha256"]
    events = defaultdict(list)
    for event in read_gbbq(gbbq_root / "gbbq"):
        if event.event_date <= TARGET:
            events[event.security_id].append(event)
    contract_path = ROOT / "config/v4_02_gbbq_price_impact_classification_v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    forward_contract_path = ROOT / "config/v4_02_go_forward_pit_adjustment_r2.json"
    forward_contract = json.loads(forward_contract_path.read_text(encoding="utf-8"))
    if forward_contract["contract_id"] != "V4_02_GO_FORWARD_T0_CURRENT_COORDINATE_R2":
        raise ValueError("FORWARD_CONTRACT_ID_MISMATCH")
    forward_contract_sha = file_sha(forward_contract_path)
    dispositions = {int(k): v["formal_disposition"] for k, v in contract["dispositions"].items()}
    identity = json.loads((ROOT / "data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json").read_text(encoding="utf-8"))
    accepted_keys = set()
    with gzip.open(ROOT / "data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            candidate = json.loads(line)
            if candidate["trade_date"] == "2026-09-24":
                accepted_keys.add(candidate["source_security_key"])
    target_keys = set(accepted_keys) | set(universe["new_source_keys"])
    active, unresolved = target_identity(accepted_keys, target_keys, identity["records"], "2026-09-28")
    if unresolved or set(active) != target_keys:
        raise ValueError("V4_02_GO_FORWARD_BLOCKED_UNIVERSE_IDENTITY")
    raw_published_at = "2026-09-28T07:58:05Z"
    raw_available_at = capture["attempts"][-1]["finished_at"]
    formal_publication_at = raw_available_at
    code_change_keys = {r["source_security_key"] for r in identity["records"] if r.get("alias_role") == "SUCCESSOR" and r.get("symbol_effective_from") and r["symbol_effective_from"] <= "2026-09-28"}
    extracted = ROOT / package["extraction_root"]
    counts = Counter()
    samples = {}
    logical = sha256()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=OUT.name + ".", suffix=".tmp", dir=OUT.parent)
    os.close(fd)
    try:
        with open(temp_name, "wb") as raw_output:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=0, compresslevel=6) as output:
                for key in sorted(active):
                    row = active[key]
                    market, code = key.split(".")
                    source = extracted / market.lower() / "lday" / f"{market.lower()}{code}.day"
                    if not source.is_file():
                        continue
                    payload = source.read_bytes()
                    if len(payload) < 32 or len(payload) % DAY_RECORD_LENGTH:
                        continue
                    all_bars = [decode_record(payload[offset:offset + DAY_RECORD_LENGTH])
                                for offset in range(0, len(payload), DAY_RECORD_LENGTH)]
                    bars = [bar for bar in all_bars if bar.trade_date <= TARGET][-251:]
                    if not bars:
                        continue
                    actual = bars[-1].trade_date == TARGET
                    visible = events.get(key, [])
                    relevant = [event for event in visible if bars[0].trade_date < event.event_date <= TARGET]
                    blocking = sorted({event.category for event in relevant if dispositions.get(event.category, "UNKNOWN_PRICE_IMPACT") in
                                       ("PRICE_AFFECTING_UNSUPPORTED", "UNKNOWN_PRICE_IMPACT")})
                    quality = "ADJUSTED_READY" if actual and not blocking else (
                        "ADJUSTED_UNAVAILABLE_NO_T0_RAW" if not actual else "ADJUSTED_UNAVAILABLE_UNSUPPORTED_OR_UNKNOWN_EVENT")
                    factor = None
                    lookback = sha256()
                    adjusted_latest = None
                    if quality == "ADJUSTED_READY":
                        xrxd = [xrxd_from_gbbq(e) for e in relevant if e.category == 1]
                        factors = build_affine_factors([b.trade_date for b in bars], xrxd)
                        for bar in bars:
                            item = factors[bar.trade_date]
                            values = [str(item.qfq_price(Decimal(str(getattr(bar, field)))))
                                      for field in ("open", "high", "low", "close")]
                            lookback.update(packed({"date": bar.trade_date, "qfq_ohlc": values,
                                                    "A": str(item.qfq_mul), "B": str(item.qfq_add)}))
                            if bar.trade_date == TARGET:
                                factor = item
                                adjusted_latest = values
                    event_set = [{"date": e.event_date, "category": e.category, "index": e.source_record_index,
                                  "c": [e.c1, e.c2, e.c3, e.c4]} for e in relevant]
                    latest = bars[-1]
                    board = ("SH_MAIN" if market == "SH" and code.startswith("60") else
                             "STAR" if market == "SH" else
                             "CHINEXT" if code.startswith("30") else "SZ_MAIN")
                    time_lineage = publication_time(TARGET, latest.trade_date, raw_published_at,
                                                   raw_available_at, gbbq_manifest["system_available_at"],
                                                   formal_publication_at)
                    output_row = {
                        "contract_id": forward_contract["contract_id"],
                        "contract_sha256": forward_contract_sha,
                        "security_id": row["security_id"], "source_security_key": key, "board_scope": board,
                        "target_trade_date": TARGET, "source_asof": TARGET,
                        **time_lineage,
                        "new_listing_provenance": universe["new_source_key_identity"].get(key),
                        "system_available_at": capture["attempts"][-1]["finished_at"],
                        "raw_source_snapshot_id": f"sha256-{capture['package_sha256']}",
                        "raw_source_digest": file_sha(source),
                        "adjustment_snapshot_id": GBBQ_ID, "adjustment_snapshot_digest": gbbq_sha,
                        "adjustment_system_available_at": gbbq_manifest["system_available_at"],
                        "max_source_trade_date": latest.trade_date,
                        "knowledge_lineage": "PIT_OBSERVED_AFTER_FORMAL_PUBLICATION", "coordinate_basis": "T0_CURRENT_COORDINATE",
                        "historical_as_recorded_claim": False,
                        "source_visibility_basis": "FROZEN_PRE_T0_GBBQ_SNAPSHOT",
                        "adjusted_quality": quality,
                        "adjustment_reason": None if quality == "ADJUSTED_READY" else
                        ("NO_T0_RAW_BAR" if not actual else "UNSUPPORTED_OR_UNKNOWN_PRICE_EVENT"),
                        "blocking_event_categories": blocking,
                        "visible_effective_event_set_digest": sha256(packed(event_set)).hexdigest(),
                        "visible_effective_event_count": len(event_set),
                        "qfq_mul": str(factor.qfq_mul) if factor else None,
                        "qfq_add": str(factor.qfq_add) if factor else None,
                        "raw_ohlc": [str(getattr(latest, field)) for field in ("open", "high", "low", "close")] if actual else None,
                        "qfq_ohlc": adjusted_latest,
                        "lookback_bar_count": len(bars),
                        "lookback_logical_digest": lookback.hexdigest() if quality == "ADJUSTED_READY" else None,
                    }
                    line = packed(output_row)
                    output.write(line)
                    logical.update(line)
                    counts[board] += 1
                    counts[quality] += 1
                    if actual:
                        counts["RAW_READY"] += 1
                    if quality == "ADJUSTED_READY" and "no_action" not in samples and not relevant:
                        samples["no_action"] = {"row": output_row, "visible_event_set": event_set}
                    if quality == "ADJUSTED_UNAVAILABLE_NO_T0_RAW" and "no_t0_bar" not in samples:
                        samples["no_t0_bar"] = {"row": output_row, "visible_event_set": event_set}
                    if quality == "ADJUSTED_UNAVAILABLE_UNSUPPORTED_OR_UNKNOWN_EVENT" and "unsupported" not in samples:
                        samples["unsupported"] = {"row": output_row, "visible_event_set": event_set}
                    for e in relevant:
                        if e.category != 1:
                            continue
                        kind = ("combined" if e.c1 and (e.c3 or e.c4) else "cash_dividend" if e.c1 else
                                "rights_issue" if e.c4 else "share_bonus_transfer" if e.c3 else "other_xrxd")
                        if kind not in samples:
                            samples[kind] = {"row": output_row, "visible_event_set": event_set,
                                             "sample_event": event_set[relevant.index(e)]}
                    if key in code_change_keys:
                        samples["code_change"] = {"row": output_row, "visible_event_set": event_set}
        os.replace(temp_name, OUT)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    receipt = {"contract_id": "V4_02_GO_FORWARD_ADJUSTED_DAILY_RECEIPT_R3",
               "status": "FULL_MARKET_T0_CANDIDATE_BUILT", "target_trade_date": TARGET,
               "package_sha256": capture["package_sha256"], "gbbq_snapshot_id": GBBQ_ID,
               "gbbq_sha256": gbbq_sha, "adjustment_contract_sha256": forward_contract_sha,
               "category_classification_contract_sha256": file_sha(contract_path),
               "row_counts": dict(counts), "candidate_path": OUT.relative_to(ROOT).as_posix(),
               "candidate_sha256": file_sha(OUT), "logical_digest": logical.hexdigest(),
               "first_possible_formal_publication_at": capture["attempts"][-1]["finished_at"],
               "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE",
               "tdx_root_write_count": 0}
    atomic_json(RECEIPT, receipt)
    atomic_json(SAMPLES, {"contract_id": "V4_02_GO_FORWARD_ADJUSTMENT_SAMPLES_R3",
                          "target_trade_date": TARGET, "sample_kinds": samples,
                          "unavailable_kinds": sorted(set(["cash_dividend", "share_bonus_transfer", "rights_issue", "combined", "no_action", "no_t0_bar", "code_change"]) - samples.keys())})
    print(receipt["status"], dict(counts), logical.hexdigest())


if __name__ == "__main__":
    main()
