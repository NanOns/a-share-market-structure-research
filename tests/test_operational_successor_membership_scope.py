import json

import pytest

from workbench_analysis.operational_successor_v1 import validate_membership_reference_scope
from workbench_analysis.r43_owner_replay import ref


DAY = "2026-10-16"
SNAPSHOT = {"path": "data/membership.json", "sha256": "a" * 64, "bytes": 10}


def write_authority(root, authority):
    path = root / f"authority-{authority['T0']}.json"
    path.write_text(json.dumps(authority), encoding="utf-8")
    return ref(root, path)


def authority(day, snapshot=SNAPSHOT):
    return {
        "contract_id": "V4_NATIVE_MEMBERSHIP_REFERENCE_AUTHORITY_R1",
        "T0": day,
        "membership_snapshot": snapshot,
        "AS_RECORDED": False,
        "PIT_ELIGIBLE": False,
    }


def test_rejects_predecessor_membership_authority_for_successor_date(tmp_path):
    binding = write_authority(tmp_path, authority("2026-10-15"))
    candidate = {
        "accepted_trade_date": DAY,
        "membership_snapshot": SNAPSHOT,
        "native_membership_reference": binding,
    }

    with pytest.raises(ValueError, match="NATIVE_MEMBERSHIP_REFERENCE_SCOPE_MISMATCH"):
        validate_membership_reference_scope(tmp_path, candidate)


def test_accepts_exact_date_and_snapshot_binding(tmp_path):
    binding = write_authority(tmp_path, authority(DAY))
    candidate = {
        "accepted_trade_date": DAY,
        "membership_snapshot": SNAPSHOT,
        "native_membership_reference": binding,
    }

    result = validate_membership_reference_scope(tmp_path, candidate)
    assert result["T0"] == DAY


def test_exact_daily_successor_cannot_omit_membership_reference():
    with pytest.raises(ValueError, match="NATIVE_MEMBERSHIP_REFERENCE_REQUIRED"):
        validate_membership_reference_scope(
            ".",
            {"accepted_trade_date": DAY, "exact_daily_adjustment_contract": "V4_EXACT"},
        )


@pytest.mark.parametrize(("previous_day", "candidate_day"), [
    ("2026-10-15", "2026-10-16"),
    ("2026-10-16", "2026-10-19"),
    ("2026-10-19", "2026-10-20"),
    ("2026-10-20", "2026-10-21"),
    ("2026-10-21", "2026-10-22"),
])
def test_each_successor_requires_its_own_date_scoped_membership_authority(
        tmp_path, previous_day, candidate_day):
    exact = write_authority(tmp_path, authority(candidate_day))
    candidate = {
        "accepted_trade_date": candidate_day,
        "membership_snapshot": SNAPSHOT,
        "native_membership_reference": exact,
    }
    assert validate_membership_reference_scope(tmp_path, candidate)["T0"] == candidate_day

    stale = write_authority(tmp_path, authority(previous_day))
    carried_forward = {**candidate, "native_membership_reference": stale}
    with pytest.raises(ValueError, match="NATIVE_MEMBERSHIP_REFERENCE_SCOPE_MISMATCH"):
        validate_membership_reference_scope(tmp_path, carried_forward)
