from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phase1_runner import factor_frame_digest, select_qa_samples


def _metadata(security_id, cutoff=20260924, *, normal=True, history=121, recent=16, aligned=20):
    return {
        "security_id": security_id,
        "anchor": cutoff,
        "normal": normal,
        "input_bar_count": history,
        "recent_valid_bar_count": recent,
        "aligned_rows": aligned,
    }


def test_phase1_selector_is_deterministic_current_universe_and_board_stratified():
    current = {
        "SH.600001", "SZ.000001", "SH.688001", "SZ.300001", "BJ.920001",
        "SH.600002", "SZ.000002", "SH.600003", "SZ.000003",
    }
    metadata = [_metadata(item) for item in current]
    metadata.extend([
        _metadata("SH.600004", normal=False),
        _metadata("SZ.000004", history=120),
        _metadata("SZ.000005", recent=14),
        _metadata("SH.600005", cutoff=20260923),
    ])

    first = select_qa_samples(metadata, current, 20260924)
    second = select_qa_samples(list(reversed(metadata)), current, 20260924)

    assert first == second
    assert first["selected_count"] == 5
    assert first["eligible_count"] == len(current)
    assert len({item["security_id"] for item in first["selected"]}) == 5
    assert {item["board"] for item in first["selected"]} == {
        "MAIN_SH", "MAIN_SZ", "STAR", "CHINEXT", "BEIJING"
    }
    assert all(item["selection_reason"] == "CURRENT_UNIVERSE_ACTUAL_CUTOFF_BAR_HISTORY_QUALITY"
               for item in first["selected"])
    assert first["selection_digest_sha256"] == second["selection_digest_sha256"]


def test_phase1_sample_selection_does_not_change_factor_frame_digest():
    import pandas as pd

    frame = pd.DataFrame({"security_id": ["SH.600001"], "date": [20260924], "RET5": [0.02]})
    before = factor_frame_digest(frame)
    selection = select_qa_samples([_metadata("SH.600001")], {"SH.600001"}, 20260924)
    after = factor_frame_digest(frame)

    assert selection["selected_count"] == 1
    assert before == after
