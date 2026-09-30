from pathlib import Path

from scripts.build_v4_08_membership_prerequisite import (
    read_industry_names_source,
    read_industry_source,
    read_infoharbor,
)
from src.sector.membership_baseline import map_source_sector_type


def test_infoharbor_source_parser_preserves_registered_and_unknown_types():
    raw = (
        "#GN_主题板块,1,GN001\n1#600001\n"
        "#FG_风格板块,1,FG001\n0#000001\n"
        "#ZZ_未注册分类,1,ZZ001\n2#920001\n"
        "#未标记标题,1,RAW001\n1#600002\n"
    ).encode("gb18030")
    rows, headers = read_infoharbor(Path("unused"), raw)
    assert len(headers) == 4
    assert [row["source_security_key"] for row in rows] == ["SH.600001", "SZ.000001", "BJ.920001", "SH.600002"]
    raw_types = [row["source_sector_type"] for row in rows]
    assert raw_types == ["concept", "style", "zz", "untyped_header"]
    assert map_source_sector_type(raw_types[0], {"concept": "THEME"}) == "THEME"
    assert map_source_sector_type(raw_types[1], {"style": "STYLE"}) == "STYLE"
    assert map_source_sector_type(raw_types[2], {"style": "STYLE"}) == "UNKNOWN"
    assert map_source_sector_type(raw_types[3], {"style": "STYLE"}) == "UNKNOWN"
    assert all(row["source_fact_kind"] == "SOURCE_OBSERVED" for row in rows)


def test_industry_parser_uses_frozen_bytes_and_keeps_raw_code_and_line():
    assignments = read_industry_source("1|600001|801010\nignored\n2|920001|801020\n".encode("gb18030"))
    names = read_industry_names_source("有色金属|x|x|x|x|80101\n铜|x|x|x|x|801011\n".encode("gb18030"))
    assert assignments == [
        {"security_id": "SH.600001", "industry_code": "801010", "line_number": 1},
        {"security_id": "BJ.920001", "industry_code": "801020", "line_number": 3},
    ]
    assert names == {"80101": "有色金属", "801011": "铜"}
