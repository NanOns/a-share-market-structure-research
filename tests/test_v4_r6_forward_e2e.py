"""Isolated R6 Forward path smoke: admission/denial, due plan, settlement, FEP read.

All files are created under pytest's G: temporary directory. This proves wiring
only and never grants production admission or real-sample maturity.
"""
import copy

import pytest

from test_cohort_admission_r4 import frozen, setup
from workbench_analysis.validation_cohort_read_contract_r3 import (
    maturity_schedule,
    publish_isolated_candidate,
    read_authorized_statistics,
)
from workbench_analysis.v4_15_persistence import Store
from workbench_analysis.v4_15_settlement import (
    SettlementRuntime,
    VectorPriceSource,
    digest,
)
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.fep_e1 import labels


def test_isolated_admission_to_due_settlement_and_fep_read(tmp_path):
    args = setup(tmp_path)
    enrolled = read_authorized_statistics(**args)
    assert enrolled["status"] == "READY" and enrolled["observed_count"] == 1

    head = __import__("json").loads((tmp_path / "head.json").read_bytes())
    head.pop("cohort_read_grants")
    (tmp_path / "denied_head.json").write_text(__import__("json").dumps(head), encoding="utf-8")
    import hashlib
    denied_head = {"path": "denied_head.json", "sha256": hashlib.sha256(
        (tmp_path / "denied_head.json").read_bytes()).hexdigest()}
    with pytest.raises(ValueError, match="COHORT_READ_GRANT_MISSING"):
        read_authorized_statistics(tmp_path, accepted_head=denied_head,
            owner_binding=args["owner_binding"], trade_date=args["trade_date"])

    sessions = ["2026-09-30", "2026-10-08", "2026-10-09", "2026-10-12",
                "2026-10-13", "2026-10-14"]
    args.update(candidate_directory="docs/evidence/r6_e2e", sessions=sessions)
    candidate = publish_isolated_candidate(**args)
    candidate_payload = __import__("json").loads((tmp_path / candidate["path"]).read_bytes())
    assert candidate_payload["production"] is False and candidate_payload["write_authorized"] is False
    horizon = maturity_schedule("2026-09-30", sessions, "2026-10-08")
    assert horizon[1]["status"] == "DUE_REQUIRES_SETTLEMENT_OWNER"
    assert horizon[3]["status"] == "PENDING"

    # The fixture authority is deliberately isolated and carries no production
    # capabilities. Settlement writes only into tmp_path/reports/.
    authority = CurrentStageAuthority.__new__(CurrentStageAuthority)
    authority.sessions = sessions
    authority.bindings = lambda: {"synthetic_only": True}
    store = Store(tmp_path, "reports/v4_15_runtime_r20/r6-e2e")
    runtime = SettlementRuntime(authority, store)
    event = copy.deepcopy(frozen())
    event.update(enrollment_id="e2e-event", entity_id="S1", comparison_reference=10)
    enrollment = store.append("enrollments", "e2e-event", event)
    universe = [
        dict(security_id=sid, close=10, hard_safety=True, research_eligible=True,
             prewatch_final_eligible=False, delta3=1, prior20_mean_amount=100,
             vol20=.1, RPS20=50, primary_industry="I")
        for sid in ("S1", "A", "B")
    ]
    snapshot = store.append("snapshots", "e2e-t0", dict(
        trade_date="2026-09-30", source_asof="2026-09-30",
        available_at="2026-09-30", universe=universe))
    freeze = runtime.freeze_t0(enrollment, snapshot)
    bar = dict(close=11, high=12, low=10, verified_identity=True,
               verified_adjustment=True, T0_basis_verified=True,
               evaluation_basis_date="2026-10-08",
               transform_coefficients={"alpha": 1, "beta": 0},
               source_asof="2026-10-08", available_at="2026-10-08")
    source = VectorPriceSource({sid: {"2026-10-08": dict(bar)}
                                for sid in ("S1", "A", "B")},
                               binding={"sha256": "a" * 64})
    outcome_binding = runtime.settle(freeze, source, "2026-10-08", horizons=(1,))[0]
    outcome = runtime.readback(freeze, "2026-10-08")["FIRST_OBSERVED"][1]
    assert outcome["outcome_status"] == "OBSERVED" and outcome["R_N"] == pytest.approx(.1)
    reread = labels.read_source(store, outcome_binding, outcome["outcome_revision_id"],
                                outcome["evaluation_revision"], outcome["evaluation_source_digest"])
    time_authority = dict(upstream_digest=labels.digest(reread),
        source_fact_available_at="2026-10-08T16:00:00+08:00",
        label_training_mature_at="2026-10-08T16:01:00+08:00",
        label_revision_available_at="2026-10-08T16:02:00+08:00")
    projected = labels.project(reread, {"family": "ABS_RETURN_N", "horizon": 1},
                                authority_head={"PROVED_HORIZONS": []},
                                time_authority=time_authority)
    assert projected["numeric_value"] == pytest.approx(.1)
    assert projected["evidence_class"] == "ENGINEERING_FIXTURE"
    assert projected["training_allowed"] is True
