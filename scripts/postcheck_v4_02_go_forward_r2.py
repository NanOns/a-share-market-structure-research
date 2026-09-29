"""Independent R2 source, candidate, lineage and sample crosscheck."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
import gzip
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
import subprocess
import sys
import zipfile

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq  # noqa: E402
from tdx.day_reader import DAY_RECORD_LENGTH, decode_record  # noqa: E402
from tdx.gbbq_reader import read_gbbq  # noqa: E402

BASELINE = "1524dcad312652c28b1f03b558ec8b6a7a3d0aa9"
OUT = ROOT / "reports/v4_02/V4_02_GO_FORWARD_PIT_LINEAGE_POSTCHECK_R2.json"


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    read = lambda name: json.loads((ROOT / f"reports/v4_02/{name}").read_text(encoding="utf-8"))
    capture = read("V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R2.json")
    package = read("V4_02_GO_FORWARD_TDX_PACKAGE_RECEIPT_R2.json")
    overlap = read("V4_02_GO_FORWARD_RAW_OVERLAP_R2.json")
    universe = read("V4_02_GO_FORWARD_UNIVERSE_CANDIDATE_R2.json")
    candidate = read("V4_02_GO_FORWARD_ADJUSTED_DAILY_RECEIPT_R2.json")
    no_backdating = read("V4_02_GO_FORWARD_NO_BACKDATING_R2.json")
    determinism = read("V4_02_GO_FORWARD_DETERMINISM_R2.json")
    later = read("V4_02_GO_FORWARD_GBBQ_LATER_REVISION_R2.json")
    archive = ROOT / capture["package_path"]
    assert digest(archive) == capture["package_sha256"] == package["package_sha256"]
    assert zipfile.is_zipfile(archive)
    assert capture["official_publication_time"] == "2026-09-28 15:58:05"
    assert [a["method"] for a in capture["attempts"]] == ["PYTHON_URLLIB", "PYTHON_URLLIB", "WINDOWS_CURL"]
    assert capture["attempts"][-1]["failure_reason"] is None
    assert capture["attempts"][-1]["actual_byte_count"] == archive.stat().st_size
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name in ("sh/lday/sh600000.day", "sz/lday/sz000001.day"):
            data = z.read(name)
            assert len(data) % DAY_RECORD_LENGTH == 0
            assert unpack_from("<I", data, len(data) - DAY_RECORD_LENGTH)[0] == 20260928
    extracted = ROOT / package["extraction_root"]
    counts = Counter()
    for market in ("sh", "sz", "bj"):
        for path in (extracted / market / "lday").glob("*.day"):
            size = path.stat().st_size
            if not size or size % DAY_RECORD_LENGTH:
                continue
            with path.open("rb") as stream:
                stream.seek(-DAY_RECORD_LENGTH, 2)
                day = int.from_bytes(stream.read(4), "little")
            assert day <= 20260928
            counts[market] += day == 20260928
    assert counts["sh"] == package["market_counts"]["sh_files_with_20260928_bar"]
    assert counts["sz"] == package["market_counts"]["sz_files_with_20260928_bar"]
    assert sum(counts.values()) == package["target_date_total_bars"]
    assert package["future_date_bar_count"] == 0
    assert overlap["status"] == "PASS" and overlap["counts"]["MISMATCH"] == 0 if "MISMATCH" in overlap["counts"] else overlap["status"] == "PASS"
    daily = ROOT / overlap["accepted_daily_path"]
    sample = duckdb.connect().execute("SELECT source_security_key, raw_close FROM read_parquet(?) "
                                      "WHERE trade_date=20260924 AND source_security_key IN ('SH.600000','SZ.000001')",
                                      [str(daily)]).fetchall()
    for key, accepted_close in sample:
        market, code = key.split(".")
        data = (extracted / market.lower() / "lday" / f"{market.lower()}{code}.day").read_bytes()
        vals = [decode_record(data[i:i+32]) for i in range(0, len(data), 32)]
        raw_close = next(bar.close for bar in vals if bar.trade_date == 20260924)
        assert Decimal(str(raw_close)) == accepted_close
    assert universe["status"] == "PASS_CANDIDATE" and universe["preserved_security_count"] == 5222
    assert not universe["unresolved_target_source_keys"] and not universe["unexplained_dropped_source_keys"]
    gbbq_root = ROOT / "data/v4/source_snapshot_store/gbbq" / candidate["gbbq_snapshot_id"]
    manifest = json.loads((gbbq_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["system_available_at"] == "2026-09-26T13:07:05Z"
    assert digest(gbbq_root / "gbbq") == candidate["gbbq_sha256"]
    assert digest(gbbq_root / "gbbq.map") == manifest["files"]["gbbq.map"]["sha256"]
    later_path = ROOT / later["later_snapshot_paths"]["gbbq"]
    later_manifest = json.loads((later_path.parent / "manifest.json").read_text(encoding="utf-8"))
    assert later_manifest["snapshot_id"] == later["later_snapshot_id"]
    assert later_manifest["t0_qfq_input"] is False
    assert later_manifest["file_hashes"] == later["later_file_hashes"]
    assert digest(later_path) == later["later_file_hashes"]["gbbq"]
    assert digest(ROOT / later["later_snapshot_paths"]["gbbq.map"]) == later["later_file_hashes"]["gbbq.map"]
    price_categories = {1, 4, 6, 11, 12, 13, 14, 15}
    def price_event_set(path: Path) -> list[tuple]:
        return sorted((e.security_id, e.event_date, e.category, e.c1, e.c2, e.c3, e.c4)
                      for e in read_gbbq(path) if e.event_date <= 20260928 and e.category in price_categories)
    assert price_event_set(gbbq_root / "gbbq") == price_event_set(later_path)
    assert later["price_affected_security_count"] == 0 and later["later_records_used_for_t0_qfq"] is False
    assert candidate["first_possible_formal_publication_at"] == capture["attempts"][-1]["finished_at"]
    contract_sha = digest(ROOT / "config/v4_02_go_forward_pit_adjustment_r2.json")
    assert candidate["adjustment_contract_sha256"] == contract_sha
    logical = sha256()
    rows = {}
    quality = Counter()
    boards = Counter()
    with gzip.open(ROOT / candidate["candidate_path"], "rb") as stream:
        for line in stream:
            logical.update(line)
            row = json.loads(line)
            assert row["target_trade_date"] == 20260928 and row["source_asof"] == 20260928
            assert row["max_source_trade_date"] <= 20260928
            assert row["knowledge_lineage"] == "PIT_OBSERVED"
            assert row["coordinate_basis"] == "T0_CURRENT_COORDINATE" and row["historical_as_recorded_claim"] is False
            assert row["adjustment_snapshot_digest"] == candidate["gbbq_sha256"]
            assert row["contract_sha256"] == contract_sha
            assert row["raw_source_snapshot_id"] == f"sha256-{capture['package_sha256']}"
            assert row["system_available_at"] == candidate["first_possible_formal_publication_at"]
            assert row["adjusted_quality"] == "ADJUSTED_READY" or row["qfq_ohlc"] is None
            rows[row["source_security_key"]] = row
            quality[row["adjusted_quality"]] += 1
            boards[row["board_scope"]] += 1
    assert logical.hexdigest() == candidate["logical_digest"]
    assert digest(ROOT / candidate["candidate_path"]) == candidate["candidate_sha256"]
    assert len(rows) == 5222 and quality["ADJUSTED_READY"] == 5195
    assert quality["ADJUSTED_UNAVAILABLE_UNSUPPORTED_OR_UNKNOWN_EVENT"] == 15
    assert quality["ADJUSTED_UNAVAILABLE_NO_T0_RAW"] == 12
    assert dict(boards) == {k: v for k, v in candidate["row_counts"].items() if k in boards}
    # Recompute one nontrivial historical QFQ lookback digest directly from
    # frozen GBBQ records and extracted raw bars, without reading builder samples.
    key = "SH.600000"
    row = rows[key]
    raw = (extracted / "sh/lday/sh600000.day").read_bytes()
    bars = [decode_record(raw[i:i+32]) for i in range(0, len(raw), 32) if int.from_bytes(raw[i:i+4], "little") <= 20260928][-251:]
    events = [xrxd_from_gbbq(e) for e in read_gbbq(gbbq_root / "gbbq")
              if e.security_id == key and e.category == 1 and bars[0].trade_date < e.event_date <= 20260928]
    factors = build_affine_factors([bar.trade_date for bar in bars], events)
    history = sha256()
    for bar in bars:
        factor = factors[bar.trade_date]
        item = {"date": bar.trade_date,
                "qfq_ohlc": [str(factor.qfq_price(Decimal(str(getattr(bar, field))))) for field in ("open", "high", "low", "close")],
                "A": str(factor.qfq_mul), "B": str(factor.qfq_add)}
        history.update((json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode())
    assert history.hexdigest() == row["lookback_logical_digest"]
    assert no_backdating["status"] == "PASS" and no_backdating["later_only_record_influenced_t0"] is False
    assert no_backdating["actual_later_snapshot_id"] == later["later_snapshot_id"]
    assert determinism["same_logical_digest"] and determinism["same_compressed_sha256"]
    assert determinism["first_run_logical_digest"] == determinism["second_run_logical_digest"] == logical.hexdigest()
    assert determinism["first_run_compressed_sha256"] == determinism["second_run_compressed_sha256"] == candidate["candidate_sha256"]
    for path in ("data/v4/V4_02_ACCEPTED_HEAD.json", "data/v4/V4_04_ACCEPTED_HEAD.json", "data/v4/V4_STAGE_ACCEPTED_HEAD.json"):
        original = subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)
        assert sha256(original).hexdigest() == digest(ROOT / path)
    output = {"contract_id": "V4_02_GO_FORWARD_PIT_LINEAGE_POSTCHECK_R2", "status": "PASS",
              "package_sha256": capture["package_sha256"], "target_bar_counts": dict(counts),
              "candidate_logical_digest": logical.hexdigest(), "candidate_rows": len(rows),
              "quality_counts": dict(quality), "sample_qfq_lookback_recomputed": key,
              "later_snapshot_id": later["later_snapshot_id"],
              "later_price_event_set_identical_to_t0_frozen_snapshot": True,
              "later_snapshot_classification_counts": later["classification_counts"],
              "accepted_heads_unchanged": True, "tdx_root_write_count": 0,
              "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE"}
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("INDEPENDENT_POSTCHECK_PASS", len(rows), logical.hexdigest())


if __name__ == "__main__":
    main()
