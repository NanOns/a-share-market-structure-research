"""Historical cross-section outputs with required PIT/source/window identity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from statistics import fmean
from typing import Mapping, Sequence

from .core import PARAMETER_SET_ID, contract_literal, rps_midrank


@dataclass(frozen=True)
class RelativeValue:
    value: float | None
    quality_state: str
    unknown_reason: str | None
    contract_id: str
    contract_version: str
    parameter_set_id: str
    window_identity: str
    input_digest: str
    output_digest: str
    universe_snapshot_id: str
    start_universe_snapshot_id: str | None
    start_session: str
    end_session: str
    adjustment_basis_id: str
    universe_count: int
    evaluable_count: int
    missing_count: int
    coverage: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def relative_factors(
    *,
    current_returns: Mapping[int, Mapping[str, float | None]],
    historical_rps: Mapping[int, Mapping[str, Mapping[str, float | None]]],
    asof_universe: Sequence[str],
    start_universes: Mapping[int, Sequence[str]],
    asof_trade_date: str,
    session_dates: Mapping[str, Mapping[int, str]],
    market_calendar_id: str,
    universe_snapshot_id: str,
    start_universe_snapshot_ids: Mapping[int, str],
    adjustment_basis_id: str,
    input_source_digest: str,
    prior_rps_artifact_digests: Mapping[int, Mapping[str, str]],
    prior_rps_universe_snapshot_ids: Mapping[int, Mapping[str, str]],
) -> tuple[dict[str, dict[str, RelativeValue]], dict[int, dict]]:
    """Compute RPS, deltas, and rel_market while binding PIT and source identity.

    `session_dates[asof_trade_date][-N]` must be the frozen t-N market session.
    Historical RPS values must come from the same versioned contract; each prior
    field is bound to its accepted artifact digest and is never synthesized from
    the current survivor universe.
    """
    members = sorted(set(asof_universe))
    if not all((market_calendar_id, universe_snapshot_id, adjustment_basis_id, input_source_digest)):
        raise ValueError("relative output identity inputs are mandatory")
    end = asof_trade_date
    references: dict[int, dict] = {}
    out = {s: {} for s in members}
    def bind(field: str, sid: str, value: float | None, reason: str | None,
             coverage: tuple[int, int, int, float | None], *, horizon: int,
             contract_id: str, start_sid: str | None = None, extra_digests: Sequence[str] = ()) -> RelativeValue:
        start = session_dates[end][horizon] if horizon in session_dates[end] else end
        identity = {"window_contract": "CROSS_SECTION_SESSION_WINDOW_V1",
                    "market_calendar_id": market_calendar_id, "start_session": start,
                    "end_session": end, "universe_snapshot_id": universe_snapshot_id,
                    "start_universe_snapshot_id": start_sid,
                    "adjustment_basis_id": adjustment_basis_id}
        window_id = _digest(identity)
        input_id = _digest([input_source_digest, *extra_digests, identity, field, sid])
        total, evaluable, missing, cov = coverage
        payload = {"value": value if reason is None else None,
                   "quality_state": "UNKNOWN" if reason else "OBSERVED", "unknown_reason": reason,
                   "contract_id": contract_id, "contract_version": "1.0.0",
                   "parameter_set_id": PARAMETER_SET_ID, "window_identity": window_id,
                   "input_digest": input_id, "universe_snapshot_id": universe_snapshot_id,
                   "start_universe_snapshot_id": start_sid, "start_session": start,
                   "end_session": end, "adjustment_basis_id": adjustment_basis_id,
                   "universe_count": total, "evaluable_count": evaluable,
                   "missing_count": missing, "coverage": cov}
        payload["output_digest"] = _digest(payload)
        return RelativeValue(**payload)

    for horizon in (1, 3, 5):
        if horizon not in start_universes or horizon not in start_universe_snapshot_ids or horizon not in session_dates[end]:
            raise ValueError(f"missing PIT start universe/window identity for horizon {horizon}")
        returns = current_returns[horizon]
        start_members = sorted(set(start_universes[horizon]))
        values = {s: returns.get(s) for s in start_members
                  if returns.get(s) is not None and math.isfinite(returns[s])}
        count = len(start_members)
        evaluable_count = len(values)
        missing = count - evaluable_count
        coverage = evaluable_count / count if count else None
        threshold = contract_literal("market_reference_max_missing_fraction")
        reason = "EMPTY_START_UNIVERSE" if count == 0 else "MISSING_COVERAGE_EXCEEDED" if missing / count > threshold else None
        reference = fmean(values.values()) if values and reason is None else None
        start_sid = start_universe_snapshot_ids[horizon]
        reference_window = {"window_contract": "CROSS_SECTION_SESSION_WINDOW_V1",
                            "market_calendar_id": market_calendar_id,
                            "start_session": session_dates[end][horizon], "end_session": end,
                            "start_universe_snapshot_id": start_sid,
                            "evaluable_set_identity": _digest(sorted(values)),
                            "adjustment_basis_id": adjustment_basis_id}
        reference_input_digest = _digest([input_source_digest, reference_window, sorted(values.items())])
        references[horizon] = {
            "contract_id": "MARKET_RELATIVE_REFERENCE_V1", "contract_version": "1.0.0",
            "parameter_set_id": PARAMETER_SET_ID, "reference_return": reference,
            "quality_state": "UNKNOWN" if reason else "OBSERVED", "unknown_reason": reason,
            "universe_snapshot_id": start_sid, "evaluable_set_identity": _digest(sorted(values)),
            "universe_count": count, "evaluable_count": evaluable_count,
            "missing_count": missing, "coverage": coverage,
            "window_identity": _digest(reference_window),
            "adjustment_basis_id": adjustment_basis_id, "input_source_digest": input_source_digest,
            "input_digest": reference_input_digest,
            "path_identity": "HISTORICAL_ENDPOINT_EQUAL_WEIGHT_REFERENCE"}
        references[horizon]["output_digest"] = _digest(references[horizon])
        for sid in members:
            ret = returns.get(sid)
            field_reason = "RETURN_UNKNOWN" if ret is None else reason
            out[sid][f"rel_market_{horizon}"] = bind(
                f"rel_market_{horizon}", sid,
                None if ret is None or reference is None else ret - reference,
                field_reason, (count, evaluable_count, missing, coverage),
                horizon=horizon, contract_id="MARKET_RELATIVE_REFERENCE_V1",
                start_sid=start_sid, extra_digests=(references[horizon]["input_digest"],))

    for horizon in (5, 20):
        if horizon not in current_returns:
            raise ValueError(f"missing return series for RPS horizon {horizon}")
        scores, coverage_meta = rps_midrank(current_returns[horizon], members)
        for sid in members:
            value = scores[sid]
            reason = None if value is not None else (
                "INSUFFICIENT_EVALUABLE_UNIVERSE" if coverage_meta["evaluable_count"] < 2 else "RETURN_UNKNOWN")
            out[sid][f"rps{horizon}"] = bind(
                f"rps{horizon}", sid, value, reason,
                (coverage_meta["universe_count"], coverage_meta["evaluable_count"],
                 coverage_meta["missing_count"], coverage_meta["coverage"]),
                horizon=horizon, contract_id="RPS_MIDRANK_V1",
                start_sid=universe_snapshot_id)

    for horizon, offset in ((5, 1), (5, 3), (20, 3)):
        field = f"rps{horizon}"
        prior = historical_rps.get(offset, {}).get(field, {})
        prior_digest = prior_rps_artifact_digests.get(offset, {}).get(field)
        prior_universe_id = prior_rps_universe_snapshot_ids.get(offset, {}).get(field)
        if prior_digest is None or prior_universe_id is None:
            raise ValueError(f"missing prior RPS artifact/universe identity for {field} t-{offset}")
        for sid in members:
            now_value = out[sid][field].value
            old_value = prior.get(sid)
            reason = None if now_value is not None and old_value is not None else "PRIOR_RPS_OR_CURRENT_SCORE_UNKNOWN"
            prior_session = session_dates[end].get(-offset)
            if prior_session is None:
                raise ValueError(f"missing prior score session t-{offset}")
            # Delta identity includes current cross-section and prior accepted RPS identity.
            identity = {"current_window": out[sid][field].window_identity,
                        "prior_trade_date": prior_session, "prior_contract": "RPS_MIDRANK_V1",
                        "prior_artifact_digest": prior_digest,
                        "prior_universe_snapshot_id": prior_universe_id,
                        "market_calendar_id": market_calendar_id,
                        "universe_snapshot_id": universe_snapshot_id,
                        "adjustment_basis_id": adjustment_basis_id}
            payload = {"value": now_value - old_value if reason is None else None,
                       "quality_state": "UNKNOWN" if reason else "OBSERVED", "unknown_reason": reason,
                       "contract_id": "RPS_DELTA_V1", "contract_version": "1.0.0",
                       "parameter_set_id": PARAMETER_SET_ID, "window_identity": _digest(identity),
                       "input_digest": _digest([input_source_digest, prior_digest, identity, sid]),
                       "universe_snapshot_id": universe_snapshot_id,
                       "start_universe_snapshot_id": prior_universe_id,
                       "start_session": prior_session, "end_session": end,
                       "adjustment_basis_id": adjustment_basis_id,
                       "universe_count": out[sid][field].universe_count,
                       "evaluable_count": out[sid][field].evaluable_count,
                       "missing_count": out[sid][field].missing_count,
                       "coverage": out[sid][field].coverage}
            payload["output_digest"] = _digest(payload)
            out[sid][f"rps{horizon}_delta{offset}"] = RelativeValue(**payload)
    return out, references
