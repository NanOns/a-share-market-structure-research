from workbench_service.app import _annotate_sector_hierarchy


def _item(sector_id, name, value):
    return {
        "sector_id": sector_id,
        "sector_name": name,
        "sector_type": "INDUSTRY",
        "cells": [{"trade_date": "2026-09-09", "sector_rs20": value}],
    }


def test_industry_root_and_leaf_ranks_are_separate():
    items = [
        _item("INDUSTRY:T0202", "农林牧渔", 0.10),
        _item("INDUSTRY:T020201", "种植业", 0.99),
        _item("INDUSTRY:T020202", "渔业", 0.98),
        _item("INDUSTRY:T0302", "商业连锁", 0.09),
    ]

    nodes = {
        ("INDUSTRY", "INDUSTRY:T0202"): {"hierarchy_level_code": "ROOT", "parent_sector_id": None, "parent_sector_name": None},
        ("INDUSTRY", "INDUSTRY:T020201"): {"hierarchy_level_code": "LEAF", "parent_sector_id": "INDUSTRY:T0202", "parent_sector_name": "农林牧渔"},
        ("INDUSTRY", "INDUSTRY:T020202"): {"hierarchy_level_code": "LEAF", "parent_sector_id": "INDUSTRY:T0202", "parent_sector_name": "农林牧渔"},
        ("INDUSTRY", "INDUSTRY:T0302"): {"hierarchy_level_code": "ROOT", "parent_sector_id": None, "parent_sector_name": None},
    }
    _annotate_sector_hierarchy(items, ["2026-09-09"], nodes)

    by_id = {item["sector_id"]: item for item in items}
    assert by_id["INDUSTRY:T0202"]["hierarchy_level"] == "一级大板块"
    assert by_id["INDUSTRY:T020201"]["hierarchy_level"] == "细分行业"
    assert by_id["INDUSTRY:T020201"]["parent_sector_name"] == "农林牧渔"
    assert by_id["INDUSTRY:T020201"]["cells"][0]["hierarchy_rank"] == 1.0
    assert by_id["INDUSTRY:T020201"]["cells"][0]["hierarchy_sector_rs20_pct"] == 1.0
    assert by_id["INDUSTRY:T020202"]["cells"][0]["hierarchy_rank"] == 2.0
    assert by_id["INDUSTRY:T020202"]["cells"][0]["hierarchy_sector_rs20_pct"] == 0.5
    assert by_id["INDUSTRY:T0202"]["cells"][0]["hierarchy_rank"] == 1.0
    assert by_id["INDUSTRY:T0302"]["cells"][0]["hierarchy_rank"] == 2.0


def test_non_industry_sectors_remain_flat():
    items = [{
        "sector_id": "THEME:880001",
        "sector_name": "示例概念",
        "sector_type": "THEME",
        "cells": [{"trade_date": "2026-09-09", "sector_rs20": 0.2}],
    }]

    _annotate_sector_hierarchy(items, ["2026-09-09"], {("THEME", "THEME:880001"): {"hierarchy_level_code": "FLAT", "parent_sector_id": None, "parent_sector_name": None}})

    assert items[0]["hierarchy_level"] == "平级板块"
    assert items[0]["parent_sector_id"] is None
