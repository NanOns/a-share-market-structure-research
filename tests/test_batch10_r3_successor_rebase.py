import pytest

from scripts.rebase_batch10_r3_successor import validate_exact_identity_sets, validate_rps_evidence


def test_r3_core_and_d0_must_bind_same_exact_5226_identity_set():
    core = [{"security_id": f"S{i:04}", "trade_date": "2026-10-20"} for i in range(5226)]
    d0 = [{"security_id": f"S{i:04}", "trade_date": "2026-10-20"} for i in range(5226)]
    digest = validate_exact_identity_sets(core, d0, trade_date="2026-10-20")
    assert len(digest) == 64

    d0[-1]["security_id"] = "OTHER"
    with pytest.raises(ValueError, match="BATCH10_R3_CORE_D0_IDENTITY_SET_MISMATCH"):
        validate_exact_identity_sets(core, d0, trade_date="2026-10-20")


def test_r3_object_and_d0_counts_reject_truncated_or_duplicate_sets():
    core = [{"security_id": f"S{i:04}", "trade_date": "2026-10-20"} for i in range(5226)]
    with pytest.raises(ValueError, match="BATCH10_R3_D0_NOT_EXACT_5226_UNIQUE_OBJECTS"):
        validate_exact_identity_sets(core, core[:-1], trade_date="2026-10-20")
    duplicate = list(core)
    duplicate[-1] = dict(duplicate[0])
    with pytest.raises(ValueError, match="BATCH10_R3_CORE_NOT_EXACT_5226_UNIQUE_OBJECTS"):
        validate_exact_identity_sets(duplicate, core, trade_date="2026-10-20")


def test_r3_rps5_delta3_evidence_requires_exact_counts_and_zero_mismatch():
    evidence = {"trade_date": "2026-10-20", "rps5_delta3": {
        "core_rows": 5226, "observed": 5202, "unknown": 24, "mismatches": 0,
        "independent_exact_matches": 5202, "independent_current_rps5_mismatches": 0}}
    assert validate_rps_evidence(evidence, trade_date="2026-10-20")["unknown"] == 24
    evidence["rps5_delta3"]["mismatches"] = 1
    with pytest.raises(ValueError, match="BATCH10_R3_INDEPENDENT_RPS_ORACLE_NOT_ZERO_MISMATCH"):
        validate_rps_evidence(evidence, trade_date="2026-10-20")
