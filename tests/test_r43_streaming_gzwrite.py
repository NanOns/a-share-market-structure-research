from __future__ import annotations

import gzip
import json
from pathlib import Path

from workbench_analysis.r43_owner_replay import gzwrite


def test_gzwrite_streams_rows_deterministically_and_keeps_old_file_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "rows.jsonl.gz"
    rows = [{"n": 1}, {"n": 2}]

    def source():
        yield from rows

    first = gzwrite(tmp_path, target, source())
    first_bytes = target.read_bytes()
    assert json.loads(gzip.decompress(first_bytes).splitlines()[0]) == rows[0]
    assert [json.loads(line) for line in gzip.decompress(first_bytes).splitlines()] == rows
    assert first["sha256"]

    gzwrite(tmp_path, target, source())
    assert target.read_bytes() == first_bytes

    def broken_source():
        yield {"n": 3}
        raise RuntimeError("source interrupted")

    try:
        gzwrite(tmp_path, target, broken_source())
    except RuntimeError:
        pass
    else:
        raise AssertionError("generator error must propagate")
    assert target.read_bytes() == first_bytes
    assert not list(tmp_path.glob("rows.jsonl.gz.*.tmp"))
