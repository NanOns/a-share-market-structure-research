"""Historical cross-section composition for V4-03; no forward benchmark."""

from __future__ import annotations

from typing import Mapping, Sequence

from .core import market_reference, rps_midrank


def relative_factors(
    *,
    current_returns: Mapping[int, Mapping[str, float | None]],
    historical_rps: Mapping[int, Mapping[str, Mapping[str, float | None]]],
    asof_universe: Sequence[str],
    start_universes: Mapping[int, Sequence[str]],
) -> tuple[dict[str, dict[str, float | None]], dict[int, dict]]:
    """Return per-security RPS, deltas, and rel_market from explicit PIT inputs.

    historical_rps[offset][field][security] is the previously published same
    contract score at t-offset. Callers must bind its artifact digest.
    """
    members = sorted(set(asof_universe))
    result = {s: {} for s in members}
    references = {}
    for horizon in (1, 3, 5):
        if horizon not in start_universes:
            raise ValueError(f"missing t-{horizon} historical universe")
        ref, metadata = market_reference(current_returns[horizon], start_universes[horizon])
        references[horizon] = {**metadata, "reference_return": ref,
                               "path_identity": "HISTORICAL_ENDPOINT_EQUAL_WEIGHT_REFERENCE"}
        for s in members:
            ret = current_returns[horizon].get(s)
            result[s][f"rel_market_{horizon}"] = None if ret is None or ref is None else ret - ref
    for horizon in (5, 20):
        scores, _ = rps_midrank(current_returns[horizon], members)
        for s in members:
            result[s][f"rps{horizon}"] = scores[s]
    for horizon, offset in ((5, 1), (5, 3), (20, 3)):
        field = f"rps{horizon}"
        prior = historical_rps.get(offset, {}).get(field, {})
        for s in members:
            now, old = result[s][field], prior.get(s)
            result[s][f"{field}_delta{offset}"] = None if now is None or old is None else now - old
    return result, references
