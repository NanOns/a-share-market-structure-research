"""Freeze later local GBBQ read-only and classify revisions; never use for T0 QFQ."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tdx.gbbq_reader import read_gbbq  # noqa: E402

SOURCE = Path("D:/new_tdx/T0002/hq_cache")
PRE = ROOT / "data/v4/source_snapshot_store/gbbq/sha256-775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e"
OUT = ROOT / "reports/v4_02/V4_02_GO_FORWARD_GBBQ_LATER_REVISION_R2.json"
PRICE_AFFECTING = {1, 4, 6, 11, 12, 13, 14, 15}


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def revision_rows(path: Path) -> dict[tuple, list[tuple]]:
    groups = defaultdict(list)
    for row in read_gbbq(path):
        groups[(row.security_id, row.event_date, row.category)].append((row.c1, row.c2, row.c3, row.c4))
    return {key: sorted(values) for key, values in groups.items()}


def main() -> None:
    originals = {name: digest(SOURCE / name) for name in ("gbbq", "gbbq.map")}
    snapshot_id = "sha256-" + sha256(f"{originals['gbbq']}\0{originals['gbbq.map']}".encode()).hexdigest()
    store = ROOT / "data/v4/source_snapshot_store/gbbq_later_diagnostic" / snapshot_id
    store.mkdir(parents=True, exist_ok=True)
    for name, expected in originals.items():
        target = store / name
        if target.exists():
            if digest(target) != expected:
                raise ValueError("IMMUTABLE_LATER_GBBQ_COLLISION")
        else:
            with tempfile.NamedTemporaryFile(dir=store, delete=False) as stream:
                temp = Path(stream.name)
            shutil.copyfile(SOURCE / name, temp)
            if digest(temp) != expected or digest(SOURCE / name) != expected:
                temp.unlink(missing_ok=True)
                raise ValueError("LATER_GBBQ_CHANGED_DURING_CAPTURE")
            os.replace(temp, target)
    before = revision_rows(PRE / "gbbq")
    after = revision_rows(store / "gbbq")
    counts = Counter()
    price_affected = set()
    examples = []
    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        if old == new:
            counts["UNCHANGED"] += 1
            continue
        if key[1] > 20260928:
            classification = "FUTURE_EFFECTIVE_ADDITION" if new and not old else "UNKNOWN_FUTURE_REVISION_OR_DELETION"
        else:
            classification = "LATE_LE_T0_REVISION" if old and new else "LATE_LE_T0_ADDITION" if new else "DELETION"
        counts[classification] += 1
        if key[1] <= 20260928 and key[2] in PRICE_AFFECTING:
            price_affected.add(key[0])
        if len(examples) < 30:
            examples.append({"security_id": key[0], "effective_date": key[1], "category": key[2],
                             "classification": classification, "old": old, "later": new,
                             "price_affecting_or_unknown": key[2] in PRICE_AFFECTING})
    output = {"contract_id": "V4_02_GO_FORWARD_GBBQ_LATER_REVISION_R2",
              "status": "DIAGNOSTIC_ONLY", "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "source_read_only": str(SOURCE), "later_snapshot_id": snapshot_id,
              "later_snapshot_paths": {k: (store / k).relative_to(ROOT).as_posix() for k in originals},
              "later_file_hashes": originals, "pre_t0_snapshot_id": PRE.name,
              "comparison_cutoff": "2026-09-28", "classification_counts": dict(counts),
              "price_affected_security_count": len(price_affected),
              "price_affected_source_keys": sorted(price_affected),
              "examples": examples,
              "t0_adjustment_input_policy": "PRE_T0_SNAPSHOT_ONLY",
              "later_records_used_for_t0_qfq": False,
              "quality_disposition_for_price_affected_keys": "ADJUSTED_UNAVAILABLE_PIT_SOURCE_REVISION_AFTER_T0",
              "tdx_root_write_count": 0}
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(snapshot_id, dict(counts), len(price_affected))


if __name__ == "__main__":
    main()
