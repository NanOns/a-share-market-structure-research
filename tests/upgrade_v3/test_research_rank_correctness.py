import pandas as pd

from workbench_service.research_builder import _rank_eligible


def test_only_eligible_sectors_receive_stable_contiguous_ranks():
    rows = pd.DataFrame([
        {"sector_id": "Z", "current": False, "p1": 1.0},
        {"sector_id": "B", "current": True, "p1": 0.8},
        {"sector_id": "A", "current": True, "p1": 0.8},
        {"sector_id": "C", "current": None, "p1": 0.9},
    ])
    assert _rank_eligible(rows, "current", ["p1"]).tolist() == [pd.NA, 2, 1, pd.NA]
