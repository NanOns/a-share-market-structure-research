"""AUD-AMOUNT-A-06 candidate, explicit currency and calendar semantics; no authority grant."""
from decimal import Decimal, InvalidOperation
import hashlib
import json

CONTRACT = "AMOUNT_A_FORMAL_AUTHORITY_CANDIDATE_V1"
UNITS = {"CNY_YUAN": Decimal(1), "CNY_WAN": Decimal(10000), "CNY_YI": Decimal(100000000)}


def convert_amount(value, unit):
    if unit not in UNITS:
        raise ValueError("UNKNOWN_CURRENCY_UNIT")
    try:
        amount = Decimal(str(value)) * UNITS[unit]
    except InvalidOperation as exc:
        raise ValueError("INVALID_AMOUNT") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("INVALID_AMOUNT")
    return amount


def calculate_candidate(*, target, sessions, members_by_session, amount_rows, source_unit,
                        membership_timestamp, source_revision, threshold_contract=None):
    if sessions != sorted(set(sessions)) or target not in sessions:
        raise ValueError("INVALID_MARKET_CALENDAR")
    index = sessions.index(target)
    prior = sessions[max(0, index-20):index]
    window = prior + [target]
    reasons = []
    if len(prior) != 20:
        reasons.append("LISTING_OR_CALENDAR_WARMUP")
    member_sets = []
    for session in window:
        if session not in members_by_session:
            reasons.append("MEMBERSHIP_GAP")
        member_sets.append(set(members_by_session.get(session, [])))
    common = set.intersection(*member_sets) if member_sets else set()
    target_members = member_sets[-1] if member_sets else set()
    excluded, valid, resolved = {}, [], {}
    for member in sorted(target_members):
        if member not in common:
            excluded[member] = ["LISTING_WARMUP_OR_MEMBERSHIP_CHANGE"]
            continue
        faults = []
        for session in window:
            row = amount_rows.get((member, session))
            if row is None:
                faults.append(session + ":DATA_GAP_UNKNOWN")
                continue
            if row.get("state") not in {"ACTUAL_TRADED", "SUSPENDED_CONFIRMED"}:
                faults.append(session + ":STATUS_UNKNOWN")
                continue
            amount = convert_amount(row["amount"], source_unit)
            if row["state"] == "SUSPENDED_CONFIRMED" and amount != 0:
                raise ValueError("SUSPENSION_WITH_NONZERO_AMOUNT")
            if amount == 0 and row["state"] != "SUSPENDED_CONFIRMED":
                faults.append(session + ":ZERO_NOT_CONFIRMED")
                continue
            resolved[(member, session)] = amount
        if faults:
            excluded[member] = faults
        else:
            valid.append(member)
    if excluded:
        reasons.append("EXCLUDED_UNKNOWN_OR_INCOMPARABLE_MEMBERS")
    sums = {s: sum((resolved[(m, s)] for m in valid), Decimal(0)) for s in window}
    numerator = sums.get(target) if valid else None
    denominator = sum((sums[s] for s in prior), Decimal(0))/Decimal(20) if len(prior) == 20 and valid else None
    diagnostic_a = numerator/denominator if denominator is not None and denominator > 0 else None
    if denominator is None or denominator <= 0:
        reasons.append("UNKNOWN_OR_NONPOSITIVE_DENOMINATOR")
    # No invented 0.80/minimum-member policy. A future accepted contract is required.
    if threshold_contract is not None:
        raise ValueError("CANDIDATE_HAS_NO_ACCEPTED_THRESHOLD_CONTRACT")
    reasons.append("COVERAGE_THRESHOLD_NOT_EXTERNALLY_ACCEPTED")
    concentration = {}
    if numerator is not None and numerator > 0:
        concentration = {m: str(resolved[(m, target)] / numerator) for m in valid}
    return {"contract_id": CONTRACT, "target_trade_date": target, "prior20_sessions": prior,
            "window_sessions": window, "source_revision": source_revision,
            "source_unit": source_unit, "canonical_internal_unit": "CNY_YUAN",
            "currency_not_shares": True, "member_universe": sorted(target_members), "comparable_members": valid,
            "member_universe_digest": hashlib.sha256(json.dumps(sorted(target_members)).encode()).hexdigest(),
            "membership_timestamp": membership_timestamp, "excluded_member_reasons": excluded,
            "coverage_numerator": len(valid), "coverage_denominator": len(target_members),
            "window_coverage_denominator": max(map(len, member_sets), default=0),
            "coverage": str(Decimal(len(valid))/Decimal(len(target_members))) if target_members else None,
            "coverage_quality": "UNKNOWN_THRESHOLD_AUTHORITY", "coverage_threshold": None,
            "daily_common_member_sums_cny": {s: str(v) for s, v in sums.items()},
            "amount_numerator_cny": str(numerator) if numerator is not None else None,
            "amount_denominator_mean20_cny": str(denominator) if denominator is not None else None,
            "diagnostic_amount_a": str(diagnostic_a) if diagnostic_a is not None else None,
            "formal_amount_a": None, "unknown_reasons": sorted(set(reasons)),
            "concentration": {"weighting": "CURRENT_AMOUNT_SHARE_IN_COMPARABLE_UNIVERSE", "timestamp": target,
                              "numerator": "MEMBER_AMOUNT_CNY", "denominator": "SUM_COMPARABLE_MEMBER_AMOUNT_CNY", "weights": concentration},
            "formal_consumer_enabled": False, "v4_11_amount_a_branch_enabled": False,
            "accepted_owner_registered": False, "external_acceptance": None}
