from inspect import signature

from workbench_analysis import operational_daily_owner_v1 as owner
from workbench_analysis import r43_market_replay as market
from workbench_analysis import r43_focus_replay as focus
from workbench_analysis import r43_structure_replay as structure
from workbench_analysis import tdx_sector_retro_r43 as sector


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

    profile_parameters = set(signature(structure.materialize_profiles_structure).parameters)
    assert {"prior_snapshot", "prior_security_ids", "progress_counter"} <= profile_parameters

    sector_parameters = set(signature(sector.run).parameters)
    assert {"predecessor_history", "progress_counter"} <= sector_parameters

    market_parameters = set(signature(market.materialize_market).parameters)
    assert {"predecessor_profiles", "predecessor_markets"} <= market_parameters

    focus_parameters = set(signature(focus.materialize_focus).parameters)
    assert {"predecessor_state", "progress_counter"} <= focus_parameters
