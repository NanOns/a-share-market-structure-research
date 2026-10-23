from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from phase0_2a_runner import (
    SAMPLE_SELECTOR_CONTRACT,
    _period,
    _source_relative_windows,
    select_sample_securities,
)


def test_phase0_2a_sample_selection_is_current_universe_bounded_and_deterministic():
    current = {
        "SH.600001", "SH.688001", "SZ.000001", "SZ.300001", "BJ.920001", "SZ.000002"
    }
    actual = current | {"SH.999999"}

    first, first_receipt = select_sample_securities(current, actual)
    second, second_receipt = select_sample_securities(reversed(sorted(current)), reversed(sorted(actual)))

    assert first == second
    assert first_receipt == second_receipt
    assert first_receipt["selection_contract_id"] == SAMPLE_SELECTOR_CONTRACT["selection_contract_id"]
    assert first_receipt["eligible_count"] == len(current)
    assert first_receipt["selected_count"] == len(current)
    assert {item["security_id"] for item in first} == current
    assert {item["board"] for item in first} >= {"MAIN_SH", "STAR", "MAIN_SZ", "CHINEXT", "BEIJING"}
    assert all("stable_hash_sha256" in item for item in first_receipt["selected"])


def test_phase0_2a_selector_excludes_non_current_ids_and_caps_the_selection():
    current = {f"SZ.{value:06d}" for value in range(1, 90)}
    actual = current | {"SH.600001", "SZ.999999"}

    selected, receipt = select_sample_securities(current, actual)

    assert len(selected) == SAMPLE_SELECTOR_CONTRACT["sample_security_count"]
    assert {item["security_id"] for item in selected} <= current
    assert receipt["eligible_count"] == len(current)
    assert receipt["selected_count"] == SAMPLE_SELECTOR_CONTRACT["sample_security_count"]
    assert receipt["selection_digest_sha256"] == select_sample_securities(current, actual)[1]["selection_digest_sha256"]


def test_qfq_sample_windows_follow_available_source_date_range():
    first_window = _source_relative_windows([20000102, 20100102, 20240102, 20261021])
    moved_window = _source_relative_windows([20010102, 20110102, 20250102, 20271021])

    assert first_window["RECENT"][1] == 20261021
    assert moved_window["RECENT"][1] == 20271021
    assert _period(20251021, first_window) == "RECENT"
    assert _period(20261021, moved_window) == "RECENT"
    assert first_window["EARLY"][0] == 20000102
    assert moved_window["EARLY"][0] == 20010102
    assert first_window["MID"][1] + 1 == first_window["RECENT"][0]


def test_qfq_sample_windows_handle_sparse_and_leap_day_coverage():
    windows = _source_relative_windows([19800229, 19900228, 20240229])

    assert windows["RECENT"][1] == 20240229
    assert _period(19800229, windows) == "EARLY"
    assert _period(20240229, windows) == "RECENT"
