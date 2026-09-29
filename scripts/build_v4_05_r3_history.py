"""Materialize replay-only T0-coordinate lookback bars from frozen official inputs."""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
import gzip
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq
from tdx.day_reader import DAY_RECORD_LENGTH, decode_record
from tdx.gbbq_reader import read_gbbq
from src.v4.go_forward_r3 import target_identity
from src.v4.replay_r3_guards import require_source_identity

OUT = ROOT / "reports/v4_05/staging/V4_05_R3_T0_COORDINATE_DAILY_HISTORY.jsonl.gz"
RECEIPT = ROOT / "reports/v4_05/V4_05_R3_DAILY_HISTORY_RECEIPT.json"
TARGET = 20260928
GBBQ_ID = "775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e"
PACKAGE_ID = "70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c"


def packed(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def visible_bars(bars: list) -> list:
    """Keep at most the accepted 251 actual bars through the target session."""
    return [bar for bar in bars if bar.trade_date <= TARGET][-251:]


def sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic(path: Path, value: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    os.replace(tmp, path)


def main() -> None:
    accepted = json.loads((ROOT / "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    if accepted["official_tdx_package_sha256"] != PACKAGE_ID:
        raise ValueError("accepted source identity changed")
    manifest = json.loads((ROOT / f"data/v4/source_snapshot_store/gbbq/sha256-{GBBQ_ID}/manifest.json").read_text(encoding="utf-8"))
    gbbq_path = ROOT / f"data/v4/source_snapshot_store/gbbq/sha256-{GBBQ_ID}/gbbq"
    require_source_identity(sha(gbbq_path), manifest["files"]["gbbq"]["sha256"])
    classification = json.loads((ROOT / "config/v4_02_gbbq_price_impact_classification_v1.json").read_text(encoding="utf-8"))
    dispositions = {int(k): v["formal_disposition"] for k, v in classification["dispositions"].items()}
    events = defaultdict(list)
    for event in read_gbbq(gbbq_path):
        if event.event_date <= TARGET:
            events[event.security_id].append(event)
    identity = json.loads((ROOT / "data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json").read_text(encoding="utf-8"))
    universe = {}
    with gzip.open(ROOT / "data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["trade_date"] == "2026-09-24":
                universe[row["source_security_key"]] = row
    active, unresolved = target_identity(set(universe), set(universe), identity["records"], "2026-09-28")
    if unresolved or len(active) != 5222:
        raise ValueError("target universe identity mismatch")
    target = {}
    with gzip.open(ROOT / accepted["candidate_path"], "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            target[row["source_security_key"]] = row
    extracted = ROOT / f"data/v4/source_snapshot_store/tdx_daily/sha256-{PACKAGE_ID}"
    if not extracted.is_dir():
        raise ValueError("official package extraction unavailable")
    counts = Counter()
    logical = sha256()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(OUT.suffix + ".tmp")
    with tmp.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=6) as compressed:
        for key in sorted(active):
            t0 = target[key]
            market, code = key.split(".")
            source = extracted / market.lower() / "lday" / f"{market.lower()}{code}.day"
            payload = source.read_bytes()
            if not payload or len(payload) % DAY_RECORD_LENGTH:
                raise ValueError(f"invalid official day file: {key}")
            bars = [decode_record(payload[offset:offset + DAY_RECORD_LENGTH]) for offset in range(0, len(payload), DAY_RECORD_LENGTH)]
            bars = visible_bars(bars)
            if len(bars) != t0["lookback_bar_count"]:
                raise ValueError(f"lookback count mismatch: {key}")
            relevant = [event for event in events.get(key, []) if bars[0].trade_date < event.event_date <= TARGET]
            blocking = {event.category for event in relevant if dispositions.get(event.category, "UNKNOWN_PRICE_IMPACT") in ("PRICE_AFFECTING_UNSUPPORTED", "UNKNOWN_PRICE_IMPACT")}
            ready = t0["adjusted_quality"] == "ADJUSTED_READY"
            if ready != (bars[-1].trade_date == TARGET and not blocking):
                raise ValueError(f"quality mismatch: {key}")
            factors = build_affine_factors([bar.trade_date for bar in bars], [xrxd_from_gbbq(event) for event in relevant if event.category == 1]) if ready else {}
            lookback = sha256()
            for bar in bars:
                raw_ohlc = [str(getattr(bar, field)) for field in ("open", "high", "low", "close")]
                factor = factors.get(bar.trade_date)
                qfq = [str(factor.qfq_price(Decimal(value))) for value in raw_ohlc] if factor else None
                if ready:
                    lookback.update(packed({"date": bar.trade_date, "qfq_ohlc": qfq, "A": str(factor.qfq_mul), "B": str(factor.qfq_add)}))
                row = {"security_id": t0["security_id"], "source_security_key": key, "board_scope": t0["board_scope"], "trade_date": bar.trade_date,
                       "raw_ohlc": raw_ohlc, "qfq_ohlc": qfq, "volume": bar.volume, "amount": bar.amount,
                       "adjusted_quality": "READY" if ready else "UNKNOWN", "blocking_reason": t0["adjustment_reason"],
                       "raw_package_identity": PACKAGE_ID, "gbbq_snapshot_identity": f"sha256-{GBBQ_ID}", "max_source_trade_date": bar.trade_date,
                       "coordinate_basis": "T0_CURRENT_COORDINATE", "historical_as_recorded_claim": False,
                       "formal_publication_at": t0["formal_publication_at"], "source_asof": TARGET,
                       "target_trade_date": TARGET, "evidence_origin": "V4_05_R3_REPLAY_ONLY"}
                line = packed(row)
                compressed.write(line)
                logical.update(line)
                counts["rows"] += 1
            if ready and lookback.hexdigest() != t0["lookback_logical_digest"]:
                raise ValueError(f"accepted lookback digest mismatch: {key}")
            counts[t0["adjusted_quality"]] += 1
            counts["entities"] += 1
    os.replace(tmp, OUT)
    receipt = {"contract_id": "V4_05_R3_T0_COORDINATE_DAILY_HISTORY_V1", "status": "PASS", "target_trade_date": TARGET,
               "artifact_path": OUT.relative_to(ROOT).as_posix(), "artifact_sha256": sha(OUT), "logical_digest": logical.hexdigest(),
               "counts": dict(counts), "lookback_limit_actual_bars": 251, "accepted_t0_candidate_sha256": accepted["candidate_sha256"],
               "raw_package_sha256": PACKAGE_ID, "gbbq_snapshot_id": f"sha256-{GBBQ_ID}", "all_ready_entity_lookback_digests_match": True,
               "historical_as_recorded_claim": False, "tdx_root_write_count": 0}
    atomic(RECEIPT, receipt)
    print(json.dumps({"rows": counts["rows"], "entities": counts["entities"], "sha256": receipt["artifact_sha256"]}))


if __name__ == "__main__":
    main()
