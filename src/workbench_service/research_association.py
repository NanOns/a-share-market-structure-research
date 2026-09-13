"""V3 P07-02 associations and independent research shortlists."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


CONTRACT_ID = "RESEARCH_ASSOCIATION_PREVIEW_1"
SHORTLIST_CONTRACT_ID = "RESEARCH_SHORTLIST_PREVIEW_1"


class ResearchAssociationError(ValueError):
    pass


def _finite(value: Any) -> bool:
    try:
        return value is not None and bool(pd.notna(value)) and bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _truth(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip().upper()
        if value in {"TRUE", "1", "YES"}:
            return True
        if value in {"FALSE", "0", "NO"}:
            return False
        return None
    return bool(value)


def _loo_current(group: pd.DataFrame, security_id: str) -> tuple[bool, dict[str, Any]]:
    other = group[group["security_id"].ne(security_id)]
    ret = pd.to_numeric(other["ret1"], errors="coerce")
    valid = ret.notna() & np.isfinite(ret)
    count = int(valid.sum())
    breadth = float((ret[valid] > 0).mean()) if count else None
    median = float(ret[valid].median()) if count else None
    passed = count >= 5 and breadth is not None and breadth >= .55 and median is not None and median > 0
    return passed, {"other_valid_count": count, "other_b1": breadth, "other_m1": median, "contract": "CURRENT_LOO_B1_M1_V1"}


def _loo_early(group: pd.DataFrame, security_id: str, state: dict[str, Any]) -> tuple[bool | None, dict[str, Any]]:
    other = group[group["security_id"].ne(security_id)]
    ret = pd.to_numeric(other["ret1"], errors="coerce")
    valid = ret.notna() & np.isfinite(ret)
    count = int(valid.sum())
    signals = other["setup"].map(_truth).eq(True) | other["recovery"].map(_truth).eq(True)
    improve = state.get("b_delta3") if _finite(state.get("b_delta3")) else state.get("ma20_delta3") if _finite(state.get("ma20_delta3")) else None
    if count < 5 or improve is None:
        return None, {"other_valid_count": count, "other_early_count": int(signals.sum()), "improvement": improve, "contract": "EARLY_LOO_WIDTH_CHANGE_V1"}
    passed = count >= 5 and int(signals.sum()) >= 2 and float(improve) >= .05
    return passed, {"other_valid_count": count, "other_early_count": int(signals.sum()), "improvement": float(improve), "contract": "EARLY_LOO_WIDTH_CHANGE_V1"}


def select_associations_and_shortlists(
    members: pd.DataFrame,
    roles: pd.DataFrame,
    sector_states: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select 1 primary/2 alternatives and independent CURRENT/EARLY lists."""
    member_required = {"sector_id", "security_id", "ret1", "setup", "recovery"}
    role_required = {"sector_id", "security_id", "role", "role_rank"}
    missing = sorted(member_required.difference(members.columns))
    if missing:
        raise ResearchAssociationError("ASSOCIATION_MEMBER_COLUMNS_MISSING:" + ",".join(missing))
    missing = sorted(role_required.difference(roles.columns))
    if missing:
        raise ResearchAssociationError("ASSOCIATION_ROLE_COLUMNS_MISSING:" + ",".join(missing))
    if "sector_id" not in sector_states.columns:
        raise ResearchAssociationError("ASSOCIATION_STATE_SECTOR_ID_REQUIRED")
    state_lookup = {str(row["sector_id"]): row for row in sector_states.to_dict("records")}
    member_groups = {str(key): group.copy() for key, group in members.groupby("sector_id", sort=False)}
    role_rows = roles[roles["role"].isin(["CURRENT_RESEARCH", "EARLY_WATCH"])].copy()
    role_rows["sector_id"] = role_rows["sector_id"].astype(str)
    role_rows["security_id"] = role_rows["security_id"].astype(str)
    associations: list[dict[str, Any]] = []
    candidates_by_track: dict[str, list[dict[str, Any]]] = {"CURRENT": [], "EARLY": []}
    for (track, security_id), group in role_rows.groupby([role_rows["role"].map({"CURRENT_RESEARCH": "CURRENT", "EARLY_WATCH": "EARLY"}), "security_id"], sort=True):
        candidates = []
        for _, role in group.iterrows():
            sector_id = str(role["sector_id"])
            state = state_lookup.get(sector_id, {})
            track_ok = _truth(state.get("current")) if track == "CURRENT" else _truth(state.get("potential_eligible"))
            if track == "CURRENT":
                loo, evidence = _loo_current(member_groups.get(sector_id, members.iloc[0:0]), security_id)
            else:
                loo, evidence = _loo_early(member_groups.get(sector_id, members.iloc[0:0]), security_id, state)
            candidate = {"track": track, "security_id": security_id, "sector_id": sector_id, "track_ok": track_ok, "role_rank": int(role["role_rank"]), "sector_rank": state.get("current_rank") if track == "CURRENT" else state.get("potential_rank"), "loo_support": loo, "loo_evidence": evidence, "role_reason_codes": role.get("role_reason_codes", [])}
            candidates.append(candidate)
        candidates.sort(key=lambda value: (value["track_ok"] is not True, value["loo_support"] is not True, value["role_rank"], value["sector_rank"] if _finite(value["sector_rank"]) else 10**9, value["sector_id"]))
        for relation_rank, candidate in enumerate(candidates[:3], start=1):
            relation = "PRIMARY" if relation_rank == 1 else "ALTERNATIVE"
            reason = ["TRACK_ROLE_ELIGIBLE"]
            if candidate["loo_support"] is True:
                reason.append("LOO_COMMON_SUPPORT")
            elif candidate["loo_support"] is False:
                reason.append("LOO_SINGLE_OR_WEAK_SUPPORT")
            else:
                reason.append("LOO_SUPPORT_UNKNOWN")
            associations.append({**candidate, "association_role": relation, "association_rank": relation_rank, "reason_codes": reason, "contract_id": CONTRACT_ID})
            candidate = {**candidate, "association_role": relation, "association_rank": relation_rank, "reason_codes": reason}
            candidates_by_track[track].append(candidate)
    association_frame = pd.DataFrame(associations)
    # The current list is selected first only to resolve the explicit
    # dual-qualified rule; the two display lists still have independent caps.
    def shortlist(track: str, excluded: set[str] | None = None) -> list[dict[str, Any]]:
        excluded = excluded or set()
        values = [row for row in candidates_by_track[track] if row["association_role"] == "PRIMARY" and row["security_id"] not in excluded]
        values.sort(key=lambda value: (value["sector_rank"] if _finite(value["sector_rank"]) else 10**9, value["role_rank"], value["sector_id"], value["security_id"]))
        used_sector: dict[str, int] = {}
        used_security: set[str] = set()
        result = []
        for value in values:
            if value["security_id"] in used_security or used_sector.get(value["sector_id"], 0) >= 3:
                continue
            used_sector[value["sector_id"]] = used_sector.get(value["sector_id"], 0) + 1
            used_security.add(value["security_id"])
            setup = False
            recovery = False
            source_rows = role_rows[(role_rows.security_id == value["security_id"]) & (role_rows.sector_id == value["sector_id"])]
            if len(source_rows):
                setup = bool(source_rows.iloc[0]["role"] == "EARLY_WATCH")
            member_group = member_groups.get(value["sector_id"], members.iloc[0:0])
            member_hit = member_group[member_group["security_id"].astype(str).eq(value["security_id"])]
            if len(member_hit):
                recovery = _truth(member_hit.iloc[0].get("recovery")) is True
            waiting = "板块当前强势确认" if track == "EARLY" and recovery else "BREAKOUT或RECOVERY"
            result.append({"list_type": "CURRENT_FOCUS" if track == "CURRENT" else "EARLY_FOCUS", "security_id": value["security_id"], "primary_sector_id": value["sector_id"], "alternative_sector_ids": [row["sector_id"] for row in candidates_by_track[track] if row["security_id"] == value["security_id"] and row["sector_id"] != value["sector_id"]][:2], "selection_reason": value["reason_codes"][:3], "waiting_for": waiting, "invalid_if": ["STRUCTURE_BREAK", "EXTENDED", "SECTOR_TRACK_LOST"], "previous_state": None, "change_reason": "NEW_SELECTION", "contract_id": SHORTLIST_CONTRACT_ID})
            if len(result) >= 20:
                break
        for rank, value in enumerate(result, start=1):
            value["rank"] = rank
        return result
    current_list = shortlist("CURRENT")
    current_ids = {row["security_id"] for row in current_list}
    early_list = shortlist("EARLY", current_ids)
    return association_frame, pd.DataFrame(current_list + early_list)


__all__ = ["CONTRACT_ID", "SHORTLIST_CONTRACT_ID", "ResearchAssociationError", "select_associations_and_shortlists"]
