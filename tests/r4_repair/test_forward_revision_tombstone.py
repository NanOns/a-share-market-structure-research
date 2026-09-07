from __future__ import annotations

import json
from pathlib import Path

from forward.live import next_revision_number
from scripts.tombstone_forward_revision import build


def test_invalid_revision_tombstone_preserves_evidence(tmp_path: Path):
    data = tmp_path / "data/forward/observations/20260904/revision_2"
    report = tmp_path / "reports/forward/20260904/revision_2"
    data.mkdir(parents=True)
    report.mkdir(parents=True)
    (data / "FORWARD_OBSERVATION.parquet").write_bytes(b"observation")
    receipt = report / "DAILY_FORWARD_CAPTURE_RECEIPT.json"
    receipt.write_bytes(b"changed")
    (report / "manifest.json").write_text(json.dumps({"files": {receipt.name: "0" * 64}}), encoding="utf8")
    before = {receipt: receipt.read_bytes(), data / "FORWARD_OBSERVATION.parquet": (data / "FORWARD_OBSERVATION.parquet").read_bytes()}

    tombstone = build(tmp_path, "20260904", 2)

    assert tombstone["status"] == "INVALID_PRESERVED"
    assert tombstone["next_unused_revision"] == 3
    assert tombstone["mismatches"][receipt.name]["actual"]
    assert next_revision_number(tmp_path, "20260904") == 3
    assert all(path.read_bytes() == contents for path, contents in before.items())
