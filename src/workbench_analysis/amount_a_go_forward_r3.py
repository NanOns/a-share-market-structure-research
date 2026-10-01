"""Sector Amount A candidate arithmetic and accepted-observation warmup.

Stock amount_ratio20, amr20_mean_prior and raw AMOUNT are separate namespaces.
This module grants no consumer permission and writes no Accepted Head.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import gzip
import json
from pathlib import Path
from .forward_pit_ledger_r2 import atomic, bound, canonical, digest, instant, reference

CONTRACT = "AMOUNT_A_FORMAL_AUTHORITY_GO_FORWARD_V1"
NAMESPACE = "SECTOR.amount_a_value"
UNITS = {"CNY_YUAN": Decimal(1), "CNY_WAN": Decimal(10000), "CNY_YI": Decimal(100000000)}


def currency(value, unit):
    if unit not in UNITS:
        raise ValueError("EXPLICIT_CURRENCY_UNIT_REQUIRED")
    try:
        result = Decimal(str(value))*UNITS[unit]
    except InvalidOperation as exc:
        raise ValueError("INVALID_AMOUNT") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("INVALID_AMOUNT")
    return result


def calculate_sector_amount(*, sector_id, target, sessions, observations, mode):
    """Pure arithmetic; caller must use the verified ledger reader for real scope."""
    if mode not in {"VERIFIED_ACCEPTED_OBSERVATION_LEDGER", "SYNTHETIC_ENGINEERING_ONLY"}:
        raise ValueError("DECLARED_SOURCE_SCOPE_REQUIRED")
    if sessions != sorted(set(sessions)) or target not in sessions:
        raise ValueError("EXACT_ORDERED_MARKET_CALENDAR_REQUIRED")
    index = sessions.index(target)
    window = sessions[max(0,index-20):index+1]
    reasons = []
    if len(window)!=21:
        reasons.append("INSUFFICIENT_CALENDAR_HISTORY")
    missing = [day for day in window if day not in observations]
    if missing:
        reasons.append("ACCEPTED_PIT_MEMBERSHIP_OBSERVATION_GAP")
    groups = [set(observations.get(day,{}).get("members",[])) for day in window]
    for day in window:
        if day in observations and observations[day].get("membership_basis")!="PIT_OBSERVED_ACCEPTED":
            reasons.append("PIT_MEMBERSHIP_NOT_PROVED")
    common = set.intersection(*groups) if groups else set()
    target_members = groups[-1] if groups else set()
    amounts, faults = {}, {}
    if not common:
        reasons.append("NO_COMPARABLE_MEMBERS")
    for member in sorted(common):
        for day in window:
            row = observations[day].get("amounts",{}).get(member)
            key = member+"@"+day
            if not row or row.get("state") not in {"ACTUAL_TRADED", "SUSPENDED_CONFIRMED"}:
                faults[key] = "RAW_AMOUNT_OR_DATED_STATUS_UNKNOWN"
                continue
            try:
                value = currency(row.get("amount"),row.get("unit"))
            except ValueError:
                faults[key] = "RAW_AMOUNT_UNIT_OR_VALUE_UNKNOWN"
                continue
            if row["state"]=="SUSPENDED_CONFIRMED" and value!=0:
                faults[key]="SUSPENSION_AMOUNT_CONFLICT"
            elif row["state"]=="ACTUAL_TRADED" and value==0:
                faults[key]="ZERO_AMOUNT_NOT_CONFIRMED"
            else:
                amounts[(member,day)] = value
    if faults:
        reasons.append("COMMON_MEMBER_SOURCE_GAP_UNKNOWN")
    comparable = sorted(m for m in common if all((m,day) in amounts for day in window))
    coverage = Decimal(len(comparable))/len(target_members) if target_members else None
    largest = max(map(len,groups),default=0)
    window_coverage = Decimal(len(comparable))/largest if largest else None
    numerator = denominator = amount_a = None
    sums = {}
    # Missing threshold is not an arithmetic blocker. Actual missing membership
    # or required common-member source is an arithmetic blocker.
    if not reasons:
        sums = {day:sum((amounts[(m,day)] for m in comparable),Decimal(0)) for day in window}
        numerator=sums[target]
        denominator=sum((sums[day] for day in window[:-1]),Decimal(0))/20
        if denominator<=0:
            reasons.append("NONPOSITIVE_PRIOR20_DENOMINATOR")
        else:
            amount_a=numerator/denominator
    return {"contract_id":CONTRACT,"namespace":NAMESPACE,"sector_id":sector_id,"target_trade_date":target,
            "amount_a_value":str(amount_a) if amount_a is not None else None,
            "arithmetic_status":"KNOWN" if amount_a is not None else "UNKNOWN",
            "source_scope":mode,"knowledge_lineage":"SYNTHETIC_ENGINEERING_ONLY" if mode.startswith("SYNTHETIC") else "PIT_OBSERVED_MEMBER_SOURCE_BOUND_AMOUNT",
            "prior20_sessions":window[:-1],"h21_sessions":window,"missing_accepted_membership_sessions":missing,
            "comparable_member_count":len(comparable),"target_member_count":len(target_members),
            "window_target_member_max":largest,"coverage":str(coverage) if coverage is not None else None,
            "window_coverage":str(window_coverage) if window_coverage is not None else None,
            "comparable_members":comparable,"current_only_members":sorted(target_members-common),
            "source_unknown_reasons":faults,"quality_reasons":sorted(set(reasons)),
            "amount_numerator_cny":str(numerator) if numerator is not None else None,
            "amount_denominator_prior20_mean_cny":str(denominator) if denominator is not None else None,
            "daily_common_member_sums_cny":{day:str(value) for day,value in sums.items()},
            "canonical_internal_unit":"CNY_YUAN","global_coverage_threshold":None,
            "consumer_permission":{"formal":False,"accepted_gate_contract":None,"reason":"CANDIDATE_PRODUCER_NOT_EXTERNALLY_ACCEPTED; CONSUMER_SPECIFIC_GATE_REQUIRED"},
            "stock_confirmation_dependency":False,"stock_amr20_dependency":False,"accepted":False}


def _read(root,ref):
    return json.loads(bound(root,ref))


def accepted_observation_payload(root, *, data_head_binding, membership_head_binding):
    """Append only one actually accepted dated membership+amount observation."""
    root=Path(root).resolve()
    data=_read(root,data_head_binding)
    membership=_read(root,membership_head_binding)
    if data.get("contract_id")!="V4_DATA_ACCEPTED_HEAD_V2" or data.get("external_acceptance")!="EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN":
        raise ValueError("EXTERNALLY_ACCEPTED_DATA_SOURCE_REQUIRED")
    acceptance=_read(root,data["external_acceptance_record"])
    if acceptance.get("external_acceptance")!="EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN":
        raise ValueError("DATA_EXTERNAL_ACCEPTANCE_RECORD_REQUIRED")
    from .dm01_accepted_chain_v1 import require_audit
    require_audit(root,acceptance["external_authority"])
    if acceptance["accepted_through"]!=data["accepted_trade_date"]:
        raise ValueError("DATA_ACCEPTANCE_CUTOFF_MISMATCH")
    if any(data["component_permissions"][c]["status"]!="FULL_PASS" for c in ("RAW_DAILY","IDENTITY_UNIVERSE","TRADING_STATUS")):
        raise ValueError("REQUIRED_SOURCE_CAPABILITY_NOT_FULL")
    if membership.get("external_acceptance")!="EXTERNALLY_ACCEPTED" or membership.get("membership_acceptance_scope")!="FORWARD_PIT_MEMBERSHIP_ONLY":
        raise ValueError("ACCEPTED_DATED_PIT_MEMBERSHIP_REQUIRED")
    bound(root,membership["external_acceptance_evidence"])
    facts=[json.loads(line) for line in gzip.decompress(bound(root,membership["facts"])).decode("utf8").splitlines()]
    target=data["accepted_trade_date"]
    calendar=_read(root,data["calendar"])
    if target not in calendar["session_dates"]:
        raise ValueError("ACCEPTED_CALENDAR_TARGET_GAP")
    identity=_read(root,data["component_artifacts"]["IDENTITY_UNIVERSE"])
    raw=_read(root,data["component_artifacts"]["RAW_DAILY"])
    statuses=_read(root,data["component_artifacts"]["TRADING_STATUS"])
    if any(x["trade_date"]!=target for x in (identity,raw,statuses)):
        raise ValueError("SOURCE_TARGET_DATE_MISMATCH")
    roster={r["security_id"]:r for r in identity["rows"]}
    quotes={r["security_id"]:r for r in raw["rows"]}
    states={r["security_id"]:r for r in statuses["rows"]}
    sectors={}
    seen=set()
    for row in facts:
        if row.get("membership_asof_date")!=target or row.get("membership_quality")!="PIT_OBSERVED_ACCEPTED" or row.get("pit_observed") is not True:
            raise ValueError("CURRENT_SNAPSHOT_CANNOT_BACKFILL_HISTORICAL_PIT")
        key=(row["sector_id"],row["security_id"])
        if key in seen:raise ValueError("DUPLICATE_MEMBERSHIP_OBSERVATION")
        seen.add(key)
        if row["security_id"] not in roster:raise ValueError("MEMBERSHIP_IDENTITY_GAP")
        sectors.setdefault(row["sector_id"],[]).append(row["security_id"])
    amounts={}
    for sid in sorted(roster):
        if sid not in states or states[sid]["trade_date"]!=target:
            raise ValueError("DATED_STATUS_IDENTITY_GAP")
        if sid in quotes:
            q=quotes[sid]
            if q["trade_date"]!=target or q["source_security_key"]!=roster[sid]["source_security_key"]:
                raise ValueError("RAW_IDENTITY_TARGET_MISMATCH")
            amounts[sid]={"amount":str(q["amount"]),"unit":"CNY_YUAN", "native_unit":q["amount_unit"],
                          "state":"ACTUAL_TRADED" if states[sid]["status"]=="ACTUAL_TRADED" else "UNKNOWN"}
        elif states[sid]["status"]=="SUSPENDED":
            amounts[sid]={"amount":"0","unit":"CNY_YUAN","state":"SUSPENDED_CONFIRMED","zero_basis":"EXACT_ACCEPTED_DATED_SUSPENSION"}
        else:
            amounts[sid]={"amount":None,"unit":"CNY_YUAN","state":"UNKNOWN"}
    item={"contract_id":CONTRACT,"target_trade_date":target,"source_scope":"ACCEPTED_CURRENT_OBSERVATION_ONLY",
          "membership_basis":"PIT_OBSERVED_ACCEPTED","data_head_binding":data_head_binding,
          "membership_head_binding":membership_head_binding,"membership_source_binding":membership["facts"],
          "calendar_binding":data["calendar"],"source_bindings":{c:data["component_artifacts"][c] for c in ("RAW_DAILY","IDENTITY_UNIVERSE","TRADING_STATUS")},
          "membership_observed_at":sorted(set(r["observed_at"] for r in facts)),
          "amount_accepted_available_at":data["promoted_at_utc"],"sectors":{s:sorted(m) for s,m in sectors.items()},"amounts":amounts,
          "ordinary_amount_unit_authority":"TDX_A_SHARE_FLOAT32_CNY_CROSS_FIELD_AUDIT; NAMESPACE_NOT_AMOUNT_A",
          "formal_consumer_enabled":False,"external_acceptance_of_this_producer":None}
    item["publication_id"]="A04_OBSERVATION:"+digest(canonical(item))
    return item


def append_accepted_observation(root, *, data_head_binding, membership_head_binding,
                                ledger="data/v4/a04_go_forward_r3"):
    root=Path(root).resolve()
    destination=(root/ledger).resolve()
    if not destination.is_relative_to(root):raise ValueError("LEDGER_DESTINATION_OUTSIDE_PROJECT")
    item=accepted_observation_payload(root,data_head_binding=data_head_binding,membership_head_binding=membership_head_binding)
    destination=root/ledger/"observations"/(item["publication_id"].split(":")[1]+".json")
    atomic(destination,canonical(item),immutable=True)
    return reference(root,destination)


def read_verified_observations(root,bindings):
    items=[]
    for ref in bindings:
        item=_read(root,ref);base=dict(item);pid=base.pop("publication_id")
        if pid!="A04_OBSERVATION:"+digest(canonical(base)) or item["contract_id"]!=CONTRACT:
            raise ValueError("OBSERVATION_PUBLICATION_IDENTITY_MISMATCH")
        # Reconstruct from exact accepted sources, compare every source amount/member.
        rebuilt=accepted_observation_payload(root,data_head_binding=item["data_head_binding"],membership_head_binding=item["membership_head_binding"])
        if rebuilt!=item:
            raise ValueError("OBSERVATION_SOURCE_REPLAY_MISMATCH")
        items.append(item)
    if len({x["target_trade_date"] for x in items})!=len(items):
        raise ValueError("ONE_SELECTED_REVISION_PER_TARGET_REQUIRED")
    return items


def compute_ledger_candidate(root,bindings,*,target):
    items=read_verified_observations(root,bindings)
    current=next((x for x in items if x["target_trade_date"]==target),None)
    if current is None:raise ValueError("TARGET_ACCEPTED_OBSERVATION_REQUIRED")
    sessions=_read(root,current["calendar_binding"])["session_dates"]
    all_sectors=sorted(current["sectors"])
    rows=[]
    for sector in all_sectors:
        observations={x["target_trade_date"]:{"members":x["sectors"][sector],"amounts":x["amounts"],"membership_basis":x["membership_basis"]}
                      for x in items if sector in x["sectors"]}
        rows.append(calculate_sector_amount(sector_id=sector,target=target,sessions=sessions,observations=observations,mode="VERIFIED_ACCEPTED_OBSERVATION_LEDGER"))
    item={"contract_id":CONTRACT,"rows":rows,"observation_bindings":bindings,"target_trade_date":target,
          "historical_limitation":"PRE_BASELINE_HISTORICAL_AMOUNT_A_NOT_FORMALLY_RECONSTRUCTABLE",
          "formal_consumer_enabled":False,"stock_confirmation_dependency":False,"accepted":False}
    item["publication_id"]="A04_AMOUNT_A_CANDIDATE:"+digest(canonical(item))
    return item
