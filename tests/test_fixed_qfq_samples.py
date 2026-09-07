from phase0_2a_runner import FIXED_SAMPLES


def test_all_five_phase0_2_fixed_samples_are_frozen() -> None:
    assert {(item["security_id"], item["date"]) for item in FIXED_SAMPLES} == {
        ("SH.600519", 20250625),
        ("SZ.000651", 20150702),
        ("SZ.000651", 20000803),
        ("SH.600519", 20060425),
        ("SZ.000001", 20260611),
    }

