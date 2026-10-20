from inspect import signature

from workbench_analysis import operational_daily_owner_v1 as owner


def test_exact_daily_ready_adapter_and_owner_io_contracts_are_compatible():
    prepare_parameters = set(signature(owner.prepare).parameters)
    replay_parameters = set(signature(owner.replay).parameters)

    assert {"replay_current", "adjustment_contract", "candidate_only_exact"} <= prepare_parameters
    assert {
        "lifecycle_binding",
        "exact_adjustment",
        "exact_daily_policy",
        "candidate_only_exact",
        "predecessor",
        "progress",
    } <= replay_parameters
