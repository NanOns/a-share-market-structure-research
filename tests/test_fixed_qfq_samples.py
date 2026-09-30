from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from phase0_2a_runner import SAMPLE_SELECTOR_CONTRACT, select_sample_securities


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
