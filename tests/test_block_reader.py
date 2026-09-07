from __future__ import annotations

from pathlib import Path

from tdx.block_reader import read_infoharbor_memberships


def test_infoharbor_sections(tmp_path: Path) -> None:
    path = tmp_path / "infoharbor_block.dat"
    path.write_bytes(
        "#GN_示例概念,2,880001,,,,\n0#000001,1#600000\n#FG_示例风格,1,880002,,,,\n2#920001\n".encode("gb18030")
    )
    rows, meta = read_infoharbor_memberships(path)
    assert [row["sector_type"] for row in rows] == ["concept", "concept", "style"]
    assert [row["security_id"] for row in rows] == ["SZ.000001", "SH.600000", "BJ.920001"]
    assert meta["headers_by_prefix"] == {"FG": 1, "GN": 1}
    assert [item["sector_name"] for item in meta["sector_headers"]] == ["示例概念", "示例风格"]
