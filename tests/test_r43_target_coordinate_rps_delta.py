from workbench_analysis.r43_owner_replay import rank_exact_endpoint_rps


def test_endpoint_rps_uses_only_exact_dated_members():
    # The endpoint scores are computed in the current target's QFQ coordinate.
    # A security outside the historical endpoint roster must not change the
    # endpoint denominator or the two eligible members' ranks.
    target_coordinate_returns = {
        'A': 0.20,
        'B': 0.10,
        'C': 0.95,
    }
    endpoint_members = {'A', 'B'}

    scores = rank_exact_endpoint_rps(target_coordinate_returns, endpoint_members)

    assert scores == {'A': 100.0, 'B': 0.0}
