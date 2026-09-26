from __future__ import annotations

"""Classify GBBQ categories and produce a bounded category-15 adjudication receipt."""

import gzip
import hashlib
import json
import os
import struct
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq  # noqa: E402
from tdx.gbbq_reader import read_gbbq  # noqa: E402

CONTRACT_PATH = ROOT / "config/v4_02_gbbq_price_impact_classification_v1.json"
UNIVERSE_PATH = ROOT / "data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz"
METADATA = ROOT / "data/input_staging/metadata/20260924/4835127dd77534be17d8aeba65d91ebf0ec5bbf6b5348bc1aff4612272acafdc/T0002/hq_cache"
DAY_ROOT = ROOT / "data/input_staging/extracted/20260924/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"
REPORT = ROOT / "reports/v4_02/V4_02_GBBQ_PRICE_IMPACT_CLASSIFICATION_V1.json"
DISPOSITIONS = ROOT / "data/v4/artifact_store/v4_02/V4_02_GBBQ_SECURITY_DISPOSITIONS_R6_2_20260926.jsonl.gz"
RECORD = struct.Struct("<IIIII f II")
CUTOFF = 20260924


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as output:
            json.dump(value, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def load_day(security_id: str) -> list[tuple[int, ...]]:
    market, code = security_id.split(".")
    path = DAY_ROOT / market.lower() / "lday" / f"{market.lower()}{code}.day"
    if not path.is_file() or path.stat().st_size % RECORD.size:
        return []
    payload = path.read_bytes()
    return [RECORD.unpack_from(payload, offset) for offset in range(0, len(payload), RECORD.size)]


def category15_review(records: list, by_security: dict[str, list]) -> dict:
    targets = [record for record in records if record.category == 15 and record.event_date <= CUTOFF]
    evidence = []
    parameter_shapes: Counter[str] = Counter()
    with_cat1 = set()
    for record in targets:
        all_values = (record.c1, record.c2, record.c3, record.c4)
        shape = ",".join("NZ" if value != 0 else "0" for value in all_values)
        parameter_shapes[shape] += 1
    for security_id in sorted({record.security_id for record in targets}):
        cat15 = [r for r in targets if r.security_id == security_id]
        all_events = by_security.get(security_id, [])
        if any(r.category == 1 and r.event_date <= CUTOFF for r in all_events):
            with_cat1.add(security_id)
        bars = [r for r in load_day(security_id) if r[0] <= CUTOFF and any(r[i] > 0 for i in (1, 2, 3, 4))]
        for event in cat15:
            before = max((bar for bar in bars if bar[0] < event.event_date), key=lambda bar: bar[0], default=None)
            after = min((bar for bar in bars if bar[0] >= event.event_date), key=lambda bar: bar[0], default=None)
            qfq = None
            if before is not None:
                xrxd = [xrxd_from_gbbq(item) for item in all_events if item.category == 1 and item.event_date <= CUTOFF]
                factor = build_affine_factors([bar[0] for bar in bars], xrxd).get(before[0])
                if factor is not None:
                    qfq = {"bar_date": before[0], "close": round((factor.qfq_mul * before[4] / 100 + factor.qfq_add) * 100) / 100}
            evidence.append({
                "security_id": security_id,
                "event_date": event.event_date,
                "source_record_index": event.source_record_index,
                "parameters": [event.c1, event.c2, event.c3, event.c4],
                "previous_actual_bar": {"date": before[0], "ohlc_raw": list(before[1:5])} if before else None,
                "first_actual_bar_on_or_after": {"date": after[0], "ohlc_raw": list(after[1:5])} if after else None,
                "category1_qfq_only_at_previous_bar": qfq,
                "category1_cooccurs_on_security": security_id in with_cat1,
            })
    return {
        "status": "UNKNOWN_PRICE_IMPACT_FAIL_CLOSED",
        "bounded_scope": "all observed category-15 records through source cutoff; no further sample expansion",
        "record_count": len(targets), "unique_security_count": len({record.security_id for record in targets}),
        "event_date_range": [min((r.event_date for r in targets), default=None), max((r.event_date for r in targets), default=None)],
        "securities_also_with_category_1": len(with_cat1),
        "parameter_zero_nonzero_shapes": dict(sorted(parameter_shapes.items())),
        "cooccurrence_and_tdx_qfq_behavior": evidence,
        "adjudication": "Local decoder and reference documentation do not define category 15. Adjacent TDX bars and category-1-only QFQ are descriptive and cannot establish category-15 price semantics. Fail closed only for securities with category 15.",
    }


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    gbbq_path, map_path = METADATA / "gbbq", METADATA / "gbbq.map"
    records = [record for record in read_gbbq(gbbq_path) if record.event_date <= CUTOFF]
    by_security: dict[str, list] = defaultdict(list)
    by_category: dict[int, list] = defaultdict(list)
    for record in records:
        by_security[record.security_id].append(record)
        by_category[record.category].append(record)
    category_counts = Counter(record.category for record in records)
    universe_ids: dict[str, dict] = {}
    with gzip.open(UNIVERSE_PATH, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            universe_ids.setdefault(row["source_security_key"], {"security_id": row["security_id"], "source_security_key": row["source_security_key"]})

    unsupported = {category: contract["dispositions"][str(category)] for category in range(1, 16)
                   if contract["dispositions"][str(category)]["formal_disposition"] in {"PRICE_AFFECTING_UNSUPPORTED", "UNKNOWN_PRICE_IMPACT"}}
    required_scopes = Counter()
    affected_security_count = Counter()
    dispositions_path = DISPOSITIONS
    dispositions_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=dispositions_path.name + ".", suffix=".tmp", dir=dispositions_path.parent)
    os.close(fd)
    try:
        with gzip.open(temp, "wt", encoding="utf-8", newline="") as output:
            for source_key, identity in sorted(universe_ids.items()):
                security_id = identity["security_id"]
                event_categories = sorted({event.category for event in by_security.get(source_key.replace(".", ".", 1), [])})
                if not event_categories:
                    event_categories = sorted({event.category for event in by_security.get(source_key, [])})
                nonprice = [category for category in event_categories if contract["dispositions"].get(str(category), {}).get("formal_disposition") == "NON_PRICE_AFFECTING"]
                affecting = [category for category in event_categories if category in unsupported]
                if any(contract["dispositions"].get(str(category), {}).get("formal_disposition") == "UNKNOWN_PRICE_IMPACT" for category in affecting):
                    quality = "UNAVAILABLE_UNKNOWN_PRICE_IMPACT"
                elif affecting:
                    quality = "UNAVAILABLE_PRICE_AFFECTING_UNSUPPORTED"
                else:
                    quality = "ELIGIBLE_CATEGORY_SCOPE_PENDING_REAL_ACCEPTANCE"
                for category in affecting:
                    affected_security_count[category] += 1
                required_scopes[quality] += 1
                row = {"security_id": security_id, "source_security_key": source_key,
                       "observed_categories_through_cutoff": event_categories,
                       "non_price_categories": nonprice, "blocking_categories": affecting,
                       "adjusted_quality_disposition": quality,
                       "adjustment_contract_id": contract["contract_id"]}
                output.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        os.replace(temp, dispositions_path)
    finally:
        Path(temp).unlink(missing_ok=True)

    semantic_source = ROOT / contract["source"]["semantic_reference"]
    decoder_source = ROOT / contract["source"]["local_decoder"]
    engine_source = ROOT / contract["source"]["category_1_engine"]
    report = {
        "contract_id": contract["contract_id"], "status": "CLASSIFICATION_COMPLETE_WITH_LOCAL_SEMANTIC_LIMITS",
        "formal_adjusted_acceptance": "OPEN_V4_00E_INDEPENDENT_REVIEW_AND_REAL_ACCEPTANCE_PENDING",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_cutoff": "2026-09-24", "record_count": len(records), "category_counts": {str(i): category_counts.get(i, 0) for i in range(1, 16)},
        "category_classification": [{"category": i, **contract["dispositions"][str(i)],
                                      "record_count": category_counts.get(i, 0),
                                      "unique_securities": len({r.security_id for r in by_category.get(i, [])}),
                                      "evidence_source": contract["source"]["semantic_reference"] if i in {2, 3, 5, 7, 8, 9, 10} else contract["source"]["local_decoder"]}
                                     for i in range(1, 16)],
        "category15_bounded_adjudication": category15_review(records, by_security),
        "per_security_scope_counts": dict(required_scopes),
        "per_category_affected_security_counts": {str(k): v for k, v in sorted(affected_security_count.items())},
        "security_dispositions": {"path": str(DISPOSITIONS.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(DISPOSITIONS), "row_count": len(universe_ids)},
        "evidence_hashes": {"gbbq_sha256": sha256_file(gbbq_path), "gbbq_map_sha256": sha256_file(map_path),
                            "semantic_reference_sha256": sha256_file(semantic_source), "decoder_sha256": sha256_file(decoder_source),
                            "engine_sha256": sha256_file(engine_source), "contract_sha256": sha256_file(CONTRACT_PATH),
                            "universe_sha256": sha256_file(UNIVERSE_PATH)},
        "limitations": ["Local category semantics are not independent primary-source acceptance.",
                        "Current metadata snapshot does not establish source visibility at historical cutoffs.",
                        "Categories 4, 6, 12, and 15 remain unknown or unsupported and are localized to affected securities.",
                        "No adjusted quality is promoted to READY by this classification receipt."],
        "next_stage": "REAL_ACTION_SUSPENSION_LISTING_AND_MULTI_CUTOFF_ACCEPTANCE",
    }
    atomic_json(REPORT, report)
    print(json.dumps({"status": report["status"], "category_counts": report["category_counts"],
                      "category15": {"records": report["category15_bounded_adjudication"]["record_count"],
                                     "securities": report["category15_bounded_adjudication"]["unique_security_count"],
                                     "cooccurs_category1": report["category15_bounded_adjudication"]["securities_also_with_category_1"]},
                      "per_security_scope_counts": report["per_security_scope_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
