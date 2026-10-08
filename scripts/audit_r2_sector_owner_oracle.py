"""Independent, read-only numerical oracle for the staged 2026-09-30 sector owner."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-09-30"
EVIDENCE_DIR = ROOT / os.environ.get("R2_REPAIR_EVIDENCE_DIR", "docs/evidence/three_day_repair_r2_20261008")
AUTH = ROOT / os.environ.get("R2_SECTOR_AUTHORITY_PATH", "data/v4/r2_daily_candidates/three_day_repair_r2_20261008/v4_sector_operational_authority_v1.json")
OUT = EVIDENCE_DIR / ("R2_P0_4_SECTOR_INDEPENDENT_ORACLE.csv" if "R2_REPAIR_EVIDENCE_DIR" in os.environ else "R2_P0_2_SECTOR_INDEPENDENT_ORACLE.csv")


def read_jsonl_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def known(field, key):
    item = field.get(key, {})
    value = item.get("value")
    return value if item.get("quality_state") == "OBSERVED" and isinstance(value, (int, float)) and math.isfinite(value) else None


def main():
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    native_path = ROOT / auth["native"]["path"]
    factors_path = ROOT / auth["factors"]["path"]
    hist_path = ROOT / auth["sources"]["history"]["path"]
    membership_path = ROOT / auth["sources"]["membership"]["path"]
    for path, binding in ((native_path, auth["native"]), (factors_path, auth["factors"]),
                          (hist_path, auth["sources"]["history"]), (membership_path, auth["sources"]["membership"])):
        if file_digest(path) != binding["sha256"]:
            raise SystemExit(f"SOURCE_HASH_MISMATCH:{path}")

    native = {r["sector_id"]: r for r in read_jsonl_gz(native_path) if r.get("target_trade_date") == DATE}
    factors = {r["security_id"]: r for r in read_jsonl_gz(factors_path) if r.get("trade_date") == DATE}
    history = {r["security_id"]: r for r in read_jsonl_gz(hist_path)}
    memberships = [r for r in read_jsonl_gz(membership_path)
                   if r.get("membership_asof_date") == DATE and r.get("membership_quality") == "PIT_OBSERVED_ACCEPTED"
                   and r.get("identity_status") == "MAPPED" and r.get("sector_type") in {"INDUSTRY", "THEME"}]
    groups = {}
    for row in memberships:
        groups.setdefault((row["sector_type"], row["sector_id"]), set()).add(row["security_id"])
    if len(groups) != 378 or len(native) != 378:
        raise SystemExit(f"SCOPE_MISMATCH:membership={len(groups)} native={len(native)}")

    fields = ("sector_rs1", "sector_rs5", "sector_rs20", "breadth_ret1", "breadth_ret5", "breadth_ret20", "ma20_width")
    rows = []
    for (stype, sid), member_ids in sorted(groups.items()):
        actual = native[sid]
        if actual.get("sector_type") != stype or set(actual["member_ids"]) != member_ids:
            raise SystemExit(f"MEMBERSHIP_IDENTITY_MISMATCH:{sid}")
        member_facts = []
        for sec in member_ids:
            factor = factors.get(sec)
            h = history.get(sec)
            bars = [b for b in (h or {}).get("bars", []) if b.get("trade_date") == DATE]
            if factor is None or len(bars) != 1:
                member_facts.append({})
                continue
            fs = factor["fields"]
            qfq = bars[0].get("qfq_ohlc")
            close = float(qfq[3]) if qfq is not None and bars[0].get("adjustment_reason") is None else None
            member_facts.append({
                **{f"ret{n}": known(fs, f"ret{n}") for n in (1, 5, 20)},
                "ma20": known(fs, "ma20"), "close": close,
            })
        expected = {}
        for n in (1, 5, 20):
            vals = [m[f"ret{n}"] for m in member_facts if m.get(f"ret{n}") is not None]
            expected[f"sector_rs{n}"] = statistics.median(vals) if vals else None
            expected[f"breadth_ret{n}"] = sum(x > 0 for x in vals) / len(vals) if vals else None
        pairs = [(m["close"], m["ma20"]) for m in member_facts if m.get("close") is not None and m.get("ma20") is not None]
        expected["ma20_width"] = sum(close > ma20 for close, ma20 in pairs) / len(pairs) if pairs else None
        for field in fields:
            got = actual["fields"][field]
            value = got.get("value")
            exp = expected[field]
            if got.get("quality") == "ACCEPTED":
                if exp is None or not math.isclose(value, exp, rel_tol=0, abs_tol=1e-12):
                    raise SystemExit(f"NUMERIC_MISMATCH:{sid}:{field}:{value}:{exp}")
            elif exp is not None:
                raise SystemExit(f"UNEXPECTED_UNKNOWN:{sid}:{field}:{exp}")
            if field == "ma20_width":
                known_members = len(pairs)
            else:
                metric = field.rsplit("_", 1)[-1]
                known_members = sum(m.get(metric) is not None for m in member_facts)
            rows.append({"trade_date": DATE, "sector_type": stype, "sector_id": sid, "field": field,
                         "actual": value, "actual_quality": got.get("quality"), "independent_expected": exp,
                         "members": len(member_ids), "independent_known_members": known_members,
                         "membership_snapshot_id": actual["membership_snapshot_id"],
                         "source_history_sha256": auth["sources"]["history"]["sha256"],
                         "source_factors_sha256": auth["factors"]["sha256"],
                         "source_membership_sha256": auth["sources"]["membership"]["sha256"]})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if "R2_REPAIR_EVIDENCE_DIR" in os.environ:
        def binding(path):
            return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": file_digest(path)}
        summary = {"contract_id": "R2_P0_4_INDEPENDENT_SECTOR_ORACLE_V1", "result": "PASS",
                   "target": DATE, "sectors": len(native), "fields_per_sector": len(fields),
                   "comparisons": len(rows), "fields": list(fields),
                   "method": "Independent median, positive-return breadth, and same-date QFQ close versus accepted same-basis MA20 aggregation across accepted PIT membership groups; source hashes verified before calculation.",
                   "source_bindings": {"candidate_authority": binding(AUTH), "native": binding(native_path),
                                       "factors": binding(factors_path), "history": binding(hist_path),
                                       "membership": binding(membership_path)},
                   "detail": binding(OUT), "history_claim": auth["history_claim"]}
        (EVIDENCE_DIR / "R2_P0_4_SECTOR_INDEPENDENT_ORACLE.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": "PASS", "sectors": len(groups), "fields_per_sector": len(fields),
                      "comparisons": len(rows), "membership_groups": len(groups), "target": DATE,
                      "history_claim": auth["history_claim"], "output": str(OUT.relative_to(ROOT))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
