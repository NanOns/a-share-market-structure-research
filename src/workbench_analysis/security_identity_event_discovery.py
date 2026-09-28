from __future__ import annotations

"""Generic historical and incremental discovery of security identity events.

Signals create review candidates only. Identity is merged only after a dated,
hash-bound accepted evidence record confirms the relationship.
"""

import hashlib
import re
from collections import defaultdict
from datetime import date
from itertools import combinations
from typing import Iterable, Mapping, Sequence

from workbench_analysis.v4_01_alias_completeness import REQUIRED_BOARDS

MODES = frozenset({"HISTORICAL_BACKSCAN", "DAILY_INCREMENTAL"})
SIGNALS = frozenset(
    {
        "OFFICIAL_CODE_CHANGE_EVENT",
        "DATED_ALIAS_FACT",
        "ROSTER_EXIT_ENTRY_ADJACENCY",
        "LIFECYCLE_BOUNDARY_ADJACENCY",
        "PERSISTENT_RETROSPECTIVE_BAR_ALIAS",
        "SOURCE_SYMBOL_REASSIGNMENT_OR_CODE_REUSE_CANDIDATE",
        "VERSIONED_IDENTITY_RELATION_EVIDENCE",
        "WEAK_NAME_CONTINUITY",
    }
)
_SYMBOL = re.compile(r"^(SH|SZ|BJ)\.([0-9]{6})$", re.IGNORECASE)
RELATION_POLICY_ID = "IDENTITY_RELATION_EVIDENCE_POLICY_V1"
RELATION_POLICY_VERSION = "1.0.0"
SAME_ENTITY_EVIDENCE_CLASSES = frozenset({
    "OFFICIAL_CODE_CHANGE_NOTICE", "VERSIONED_ACCEPTED_IDENTITY_ALIAS",
})
DISTINCT_ENTITY_EVIDENCE_CLASSES = frozenset({
    "OFFICIAL_DISTINCT_ISSUER_IDENTITY", "VERSIONED_ACCEPTED_LIFECYCLE_IDENTITY",
})


def _date(value: object | None) -> date | None:
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    if len(raw) == 8 and raw.isdigit():
        raw = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _key(value: object | None) -> str:
    return str(value or "").strip().upper()


def _exchange(key: str) -> str:
    match = _SYMBOL.fullmatch(key)
    return match.group(1).upper() if match else ""


def _board_for(key: str, record: Mapping[str, object] | None = None) -> str:
    record = record or {}
    board = str(record.get("board_scope") or record.get("board") or "").upper()
    exchange = str(record.get("exchange") or _exchange(key)).upper()
    if board in REQUIRED_BOARDS or board in {"BSE", "BEIJING"}:
        return "BSE" if board in {"BSE", "BEIJING"} else board
    match = _SYMBOL.fullmatch(key)
    if not match:
        return "UNKNOWN"
    code = match.group(2)
    if exchange == "SH":
        return "STAR" if code.startswith("688") else "SH_MAIN"
    if exchange == "SZ":
        return "CHINEXT" if code.startswith(("300", "301")) else "SZ_MAIN"
    return "BSE" if exchange == "BJ" else "UNKNOWN"


def _identity_id(record: Mapping[str, object] | None) -> str:
    if not record:
        return ""
    return str(record.get("security_id") or record.get("canonical_security_id") or "")


def _normalized_name(record: Mapping[str, object] | None) -> str:
    if not record:
        return ""
    value = str(record.get("security_name") or record.get("name") or record.get("company_name") or "")
    return "".join(ch for ch in value.upper() if ch.isalnum())


def _dated_alias_facts_do_not_overlap(facts: Sequence[Mapping[str, object]]) -> bool:
    by_key: dict[str, list[tuple[date, date | None]]] = defaultdict(list)
    for fact in facts:
        start = _date(fact.get("effective_from"))
        end = _date(fact.get("effective_to"))
        key = _key(fact.get("source_security_key"))
        if start is None or not key:
            return False
        by_key[key].append((start, end))
    for intervals in by_key.values():
        intervals.sort(key=lambda interval: interval[0])
        for (_, prior_end), (next_start, _) in zip(intervals, intervals[1:]):
            if prior_end is None or prior_end >= next_start:
                return False
    return True


def _candidate_id(keys: Sequence[str], ids: Sequence[str]) -> str:
    material = "|".join([*sorted(keys), "::", *sorted(ids)])
    return "IE-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24].upper()


def _has_aware_timestamp(value: object) -> bool:
    from datetime import datetime

    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _evidence_keys(evidence: Mapping[str, object]) -> tuple[str, ...]:
    raw = evidence.get("source_security_keys")
    if raw is None:
        raw = (evidence.get("old_source_security_key"), evidence.get("new_source_security_key"))
    if isinstance(raw, str):
        raw = (raw,)
    return tuple(sorted({_key(value) for value in raw if _key(value)}))


def _evidence_hash(evidence: Mapping[str, object]) -> str:
    return str(evidence.get("source_capture_sha256") or evidence.get("evidence_hash") or "").lower()


def _valid_relation_evidence(
    evidence: Mapping[str, object],
    *,
    relation: str,
    candidate_keys: Sequence[str],
    candidate_ids: Sequence[str],
    verified_digests: set[str],
    accepted_classes: frozenset[str],
) -> bool:
    evidence_relation = str(evidence.get("entity_relation") or evidence.get("relation") or "").upper()
    evidence_class = str(evidence.get("evidence_class") or "").upper()
    digest = _evidence_hash(evidence)
    effective_date = _date(evidence.get("effective_date"))
    required_common = (
        bool(evidence.get("source_ref")),
        bool(evidence.get("source_capture_path") or evidence.get("evidence_capture_path")),
        digest in verified_digests,
        effective_date is not None,
        _has_aware_timestamp(evidence.get("observed_at")),
        _has_aware_timestamp(evidence.get("system_available_at")),
    )
    if evidence_relation != relation or evidence_class not in accepted_classes or not all(required_common):
        return False
    if _evidence_keys(evidence) != tuple(sorted({_key(value) for value in candidate_keys if _key(value)})):
        return False

    security_ids = {str(value or "") for value in evidence.get("security_ids", []) if str(value or "")}
    if relation == "SAME_ENTITY":
        canonical_id = str(evidence.get("canonical_security_id") or evidence.get("security_id") or "")
        if evidence_class == "OFFICIAL_CODE_CHANGE_NOTICE":
            return len(candidate_keys) == 2 and bool(canonical_id)
        if (str(evidence.get("contract_id") or "") != "DATED_SECURITY_ALIAS_V1"
                or str(evidence.get("source_revision") or "").lower()
                not in {digest, "sha256:" + digest}):
            return False
        return len(candidate_keys) == 2 and bool(canonical_id)

    issuer_ids = {str(value or "") for value in evidence.get("issuer_ids", []) if str(value or "")}
    if len(security_ids) != 2 or len(issuer_ids) != 2:
        return False
    if len(candidate_keys) == 1:
        if len(set(candidate_ids)) < 2 or security_ids != set(candidate_ids):
            return False
    elif len(candidate_keys) == 2:
        if set(candidate_ids) and security_ids != set(candidate_ids):
            return False
    else:
        return False
    if evidence_class == "VERSIONED_ACCEPTED_LIFECYCLE_IDENTITY":
        acceptance_digest = str(evidence.get("acceptance_receipt_sha256") or "").lower()
        if not evidence.get("acceptance_receipt_path") or acceptance_digest not in verified_digests:
            return False
    return True


def _alias_facts_are_strong_same_entity_evidence(
    facts: Sequence[Mapping[str, object]], verified_digests: set[str]
) -> bool:
    required_roles = {"PREDECESSOR", "CURRENT"}
    roles = {str(fact.get("alias_role") or "").upper() for fact in facts}
    for fact in facts:
        digest = str(fact.get("evidence_hash") or fact.get("source_capture_sha256") or "").lower()
        if (
            str(fact.get("contract_id") or "") != "DATED_SECURITY_ALIAS_V1"
            or digest not in verified_digests
            or not (fact.get("evidence_ref") or fact.get("source_ref"))
            or not (fact.get("evidence_capture_path") or fact.get("source_capture_path"))
            or str(fact.get("source_revision") or "").lower() not in {digest, "sha256:" + digest}
            or _date(fact.get("effective_from")) is None
            or not _has_aware_timestamp(fact.get("observed_at"))
            or not _has_aware_timestamp(fact.get("system_available_at"))
        ):
            return False
    return required_roles <= roles


class _CandidateUnion:
    def __init__(self, identities: Mapping[str, Mapping[str, object]]):
        self.identities = identities
        self.rows: dict[tuple[tuple[str, ...], tuple[str, ...]], dict[str, object]] = {}

    def add(
        self,
        keys: Iterable[str],
        signal: str,
        *,
        effective_date: object | None = None,
        details: Mapping[str, object] | None = None,
        identity_ids: Iterable[str] | None = None,
    ) -> None:
        ordered_keys = tuple(sorted({_key(key) for key in keys if _key(key)}))
        if not ordered_keys:
            return
        if identity_ids is None:
            ids = tuple(_identity_id(self.identities.get(key)) for key in ordered_keys)
        else:
            ids = tuple(str(value or "") for value in identity_ids)
        id_key = tuple(sorted(value for value in ids if value))
        if len(ordered_keys) > 1 and len(id_key) < 2:
            id_key = tuple(sorted(ids))
        key = (ordered_keys, id_key)
        row = self.rows.setdefault(
            key,
            {
                "candidate_id": _candidate_id(ordered_keys, id_key),
                "source_keys": list(ordered_keys),
                "baseline_security_ids": list(ids),
                "candidate_signals": [],
                "effective_date_candidates": [],
                "signal_details": [],
            },
        )
        if signal not in row["candidate_signals"]:
            row["candidate_signals"].append(signal)
        day = _date(effective_date)
        if day is not None and day.isoformat() not in row["effective_date_candidates"]:
            row["effective_date_candidates"].append(day.isoformat())
        if details:
            compact = {str(k): v for k, v in details.items() if v is not None}
            if compact and compact not in row["signal_details"]:
                row["signal_details"].append(compact)

    def values(self) -> list[dict[str, object]]:
        result = list(self.rows.values())
        for row in result:
            row["candidate_signals"] = sorted(row["candidate_signals"])
            row["effective_date_candidates"] = sorted(row["effective_date_candidates"])
            row["signal_details"] = sorted(row["signal_details"], key=lambda x: str(x))
        return sorted(result, key=lambda row: str(row["candidate_id"]))


def discover_identity_events(
    *,
    mode: str,
    session_dates: Iterable[object],
    roster_snapshots: Iterable[Mapping[str, object]] = (),
    lifecycle_records: Iterable[Mapping[str, object]] = (),
    identities: Mapping[str, Mapping[str, object]],
    required_scope_source_keys: Iterable[str] | None = None,
    alias_facts: Iterable[Mapping[str, object]] = (),
    official_events: Iterable[Mapping[str, object]] = (),
    identity_relation_evidence: Iterable[Mapping[str, object]] = (),
    verified_evidence_digests: set[str] | None = None,
    retrospective_bar_candidates: Iterable[Mapping[str, object]] = (),
    source_identity_assignments: Mapping[str, Iterable[Mapping[str, object]]] | None = None,
    target_date: object | None = None,
) -> dict[str, object]:
    """Build a deterministic union of historical or one-session identity events.

    A roster boundary is paired only within one exchange. Listing dates,
    source revisions, names, lifecycle boundaries, and bar continuity create
    candidates only; relation status requires policy-accepted identity evidence.
    """
    mode = str(mode).upper()
    if mode not in MODES:
        raise ValueError("IDENTITY_EVENT_MODE_UNSUPPORTED")
    if mode == "DAILY_INCREMENTAL" and _date(target_date) is None:
        raise ValueError("IDENTITY_EVENT_TARGET_DATE_REQUIRED")
    identity_map = {_key(key): value for key, value in identities.items()}
    if required_scope_source_keys is None:
        required_keys = {
            key for key, row in identity_map.items()
            if str(row.get("security_type") or "").upper() in {"A_STOCK", "1"}
        }
        if not required_keys:
            required_keys = set(identity_map)
    else:
        required_keys = {_key(key) for key in required_scope_source_keys}
    aliases = list(alias_facts)
    official = list(official_events)
    relation_evidence = list(identity_relation_evidence)
    verified = {str(value).lower() for value in (verified_evidence_digests or set())}
    sessions = sorted({day for value in session_dates if (day := _date(value)) is not None})
    allowed_dates = set(sessions)
    if mode == "DAILY_INCREMENTAL":
        target = _date(target_date)
        if target not in allowed_dates:
            raise ValueError("IDENTITY_EVENT_TARGET_NOT_OFFICIAL_SESSION")
        sessions = [day for day in sessions if day <= target]
    else:
        target = None

    union = _CandidateUnion(identity_map)
    signal_counts: dict[str, int] = {signal: 0 for signal in sorted(SIGNALS)}

    for event in official:
        event_day = _date(event.get("effective_date"))
        if mode == "DAILY_INCREMENTAL" and event_day != target:
            continue
        old = _key(event.get("old_source_security_key") or event.get("old_symbol"))
        new = _key(event.get("new_source_security_key") or event.get("new_symbol"))
        digest = str(event.get("source_capture_sha256") or event.get("evidence_hash") or "").lower()
        if old and new:
            union.add((old, new), "OFFICIAL_CODE_CHANGE_EVENT", effective_date=event.get("effective_date"),
                      details={"source_ref": event.get("source_ref"), "source_capture_sha256": digest,
                               "system_available_at": event.get("system_available_at")})
            signal_counts["OFFICIAL_CODE_CHANGE_EVENT"] += 1

    for evidence in relation_evidence:
        keys = _evidence_keys(evidence)
        effective_date = evidence.get("effective_date")
        if mode == "DAILY_INCREMENTAL" and _date(effective_date) != target:
            continue
        if keys:
            union.add(
                keys,
                "VERSIONED_IDENTITY_RELATION_EVIDENCE",
                effective_date=effective_date,
                identity_ids=evidence.get("security_ids"),
                details={"evidence_class": evidence.get("evidence_class"),
                         "entity_relation": evidence.get("entity_relation") or evidence.get("relation"),
                         "source_ref": evidence.get("source_ref"),
                         "source_capture_sha256": _evidence_hash(evidence)},
            )
            signal_counts["VERSIONED_IDENTITY_RELATION_EVIDENCE"] += 1

    alias_groups: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for fact in aliases:
        alias_groups[str(fact.get("security_id") or "")].append(fact)
    for security_id, facts in alias_groups.items():
        ordered = sorted(facts, key=lambda row: str(row.get("effective_from") or ""))
        for left, right in combinations(ordered, 2):
            old, new = _key(left.get("source_security_key")), _key(right.get("source_security_key"))
            if mode == "DAILY_INCREMENTAL" and _date(right.get("effective_from")) != target:
                continue
            if old and new and old != new:
                union.add((old, new), "DATED_ALIAS_FACT", effective_date=right.get("effective_from"),
                          details={"security_id": security_id, "source_ref": right.get("evidence_ref"),
                                   "source_capture_sha256": right.get("evidence_hash")})
                signal_counts["DATED_ALIAS_FACT"] += 1

    # Consecutive official-session rosters expose non-overlapping transitions
    # without requiring same-day bars for the old and new symbols.
    session_position = {day: index for index, day in enumerate(sessions)}
    prior_day: date | None = None
    prior_codes: set[str] | None = None
    for snapshot in roster_snapshots:
        day = _date(snapshot.get("trade_date") or snapshot.get("date"))
        codes = snapshot.get("source_codes") or snapshot.get("codes") or ()
        if day is None or day not in allowed_dates:
            continue
        if mode == "DAILY_INCREMENTAL" and day > target:
            continue
        current_codes = {_key(code) for code in codes if _key(code)}
        adjacent = (
            prior_day is not None
            and prior_codes is not None
            and session_position.get(day) == session_position.get(prior_day, -2) + 1
        )
        if adjacent and not (mode == "DAILY_INCREMENTAL" and day != target):
            exited = prior_codes - current_codes
            entered = current_codes - prior_codes
            for old in sorted(exited):
                if old not in required_keys:
                    continue
                old_board = _board_for(old, identity_map.get(old))
                if old_board not in REQUIRED_BOARDS:
                    continue
                for new in sorted(entered):
                    if new not in required_keys:
                        continue
                    new_board = _board_for(new, identity_map.get(new))
                    if new_board not in REQUIRED_BOARDS or _exchange(old) != _exchange(new):
                        continue
                    left, right = identity_map.get(old), identity_map.get(new)
                    same_name = bool(_normalized_name(left) and _normalized_name(left) == _normalized_name(right))
                    union.add((old, new), "ROSTER_EXIT_ENTRY_ADJACENCY", effective_date=day,
                              details={"previous_session": prior_day.isoformat(), "first_session": day.isoformat(),
                                       "old_board": old_board, "new_board": new_board})
                    signal_counts["ROSTER_EXIT_ENTRY_ADJACENCY"] += 1
                    if same_name:
                        union.add((old, new), "WEAK_NAME_CONTINUITY", effective_date=day,
                                  details={"name_match_is_candidate_only": True})
                        signal_counts["WEAK_NAME_CONTINUITY"] += 1
        prior_day, prior_codes = day, current_codes

    # Independently sourced lifecycle facts expose boundaries even if a roster
    # snapshot was corrected or unavailable.
    lifecycle = list(lifecycle_records)
    session_position = {day: index for index, day in enumerate(sessions)}
    starts: dict[date, list[Mapping[str, object]]] = defaultdict(list)
    ends: dict[date, list[Mapping[str, object]]] = defaultdict(list)
    for record in lifecycle:
        start = _date(record.get("effective_from") or record.get("symbol_effective_from") or record.get("list_date"))
        end = _date(record.get("effective_to") or record.get("symbol_effective_to") or record.get("delist_date"))
        if start:
            starts[start].append(record)
        if end:
            ends[end].append(record)
    for end_day, old_rows in ends.items():
        prior_pos = session_position.get(end_day)
        if prior_pos is None or prior_pos + 1 >= len(sessions):
            continue
        next_day = sessions[prior_pos + 1]
        if mode == "DAILY_INCREMENTAL" and next_day != target:
            continue
        for old_row in old_rows:
            old = _key(old_row.get("source_security_key") or old_row.get("symbol"))
            for new_row in starts.get(next_day, []):
                new = _key(new_row.get("source_security_key") or new_row.get("symbol"))
                if (not old or not new or old == new or old not in required_keys or new not in required_keys
                        or _exchange(old) != _exchange(new)):
                    continue
                if _board_for(old, old_row) not in REQUIRED_BOARDS or _board_for(new, new_row) not in REQUIRED_BOARDS:
                    continue
                left_anchor = _date(old_row.get("list_date"))
                right_anchor = _date(new_row.get("list_date"))
                same_name = bool(_normalized_name(old_row) and _normalized_name(old_row) == _normalized_name(new_row))
                union.add((old, new), "LIFECYCLE_BOUNDARY_ADJACENCY", effective_date=next_day,
                          details={"previous_session": end_day.isoformat(), "first_session": next_day.isoformat(),
                                   "old_source_revision": old_row.get("source_revision_id") or old_row.get("source_revision"),
                                   "new_source_revision": new_row.get("source_revision_id") or new_row.get("source_revision")})
                signal_counts["LIFECYCLE_BOUNDARY_ADJACENCY"] += 1
                if same_name:
                    union.add((old, new), "WEAK_NAME_CONTINUITY", effective_date=next_day,
                              details={"name_match_is_candidate_only": True})
                    signal_counts["WEAK_NAME_CONTINUITY"] += 1

    for candidate in retrospective_bar_candidates:
        if mode == "DAILY_INCREMENTAL":
            candidate_day = _date(candidate.get("effective_date") or candidate.get("target_date"))
            if candidate_day != target:
                continue
        keys = candidate.get("source_keys") or (
            candidate.get("old_source_security_key"), candidate.get("new_source_security_key")
        )
        if keys:
            union.add(keys, "PERSISTENT_RETROSPECTIVE_BAR_ALIAS",
                      details={"shared_identical_raw_bar_sessions": candidate.get("shared_identical_raw_bar_sessions"),
                               "first_shared_date": candidate.get("first_shared_date"),
                               "last_shared_date": candidate.get("last_shared_date")},
                      identity_ids=candidate.get("security_ids"))
            signal_counts["PERSISTENT_RETROSPECTIVE_BAR_ALIAS"] += 1

    for raw_key, records in (source_identity_assignments or {}).items():
        key = _key(raw_key)
        ordered = sorted(records, key=lambda row: str(row.get("effective_from") or row.get("list_date") or ""))
        for left, right in combinations(ordered, 2):
            old_id, new_id = _identity_id(left), _identity_id(right)
            if not old_id or not new_id or old_id == new_id:
                continue
            old_end = _date(left.get("effective_to") or left.get("symbol_effective_to") or left.get("delist_date"))
            new_start = _date(right.get("effective_from") or right.get("symbol_effective_from") or right.get("list_date"))
            if old_end is not None and new_start is not None and old_end < new_start:
                if mode == "DAILY_INCREMENTAL" and new_start != target:
                    continue
                union.add((key,), "SOURCE_SYMBOL_REASSIGNMENT_OR_CODE_REUSE_CANDIDATE",
                          effective_date=new_start, identity_ids=(old_id, new_id),
                          details={"old_security_id": old_id, "new_security_id": new_id,
                                   "old_effective_to": old_end.isoformat(), "new_effective_from": new_start.isoformat()})
                signal_counts["SOURCE_SYMBOL_REASSIGNMENT_OR_CODE_REUSE_CANDIDATE"] += 1

    events = union.values()
    alias_by_key: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for fact in aliases:
        alias_by_key[_key(fact.get("source_security_key"))].append(fact)
    official_by_pair: dict[tuple[str, ...], list[Mapping[str, object]]] = defaultdict(list)
    for evidence in [*official, *relation_evidence]:
        pair = _evidence_keys(evidence)
        if pair:
            official_by_pair[pair].append(evidence)

    status_counts: dict[str, int] = defaultdict(int)
    for event in events:
        keys = list(event["source_keys"])
        ids = list(event["baseline_security_ids"])
        facts = [fact for key in keys for fact in alias_by_key.get(key, [])]
        aliases_cover = len(keys) > 1 and {_key(fact.get("source_security_key")) for fact in facts} == set(keys)
        evidence_hashes = {str(fact.get("evidence_hash") or "").lower() for fact in facts}
        same_entity_fact = (
            aliases_cover and bool(facts)
            and len({str(fact.get("security_id") or "") for fact in facts}) == 1
            and {str(fact.get("alias_role") or "").upper() for fact in facts} >= {"PREDECESSOR", "CURRENT"}
            and _dated_alias_facts_do_not_overlap(facts)
            and _alias_facts_are_strong_same_entity_evidence(facts, verified)
        )
        pair = tuple(sorted(keys))
        candidate_evidence = list(official_by_pair.get(pair, []))
        if same_entity_fact:
            current = next((fact for fact in facts
                            if str(fact.get("alias_role") or "").upper() == "CURRENT"), {})
            candidate_evidence.append({
                "entity_relation": "SAME_ENTITY",
                "evidence_class": "VERSIONED_ACCEPTED_IDENTITY_ALIAS",
                "source_security_keys": keys,
                "canonical_security_id": next(iter({str(fact.get("security_id") or "") for fact in facts})),
                "contract_id": current.get("contract_id"),
                "source_revision": current.get("source_revision"),
                "effective_date": current.get("effective_from"),
                "source_ref": current.get("evidence_ref") or current.get("source_ref"),
                "source_capture_path": current.get("evidence_capture_path") or current.get("source_capture_path"),
                "source_capture_sha256": current.get("evidence_hash") or current.get("source_capture_sha256"),
                "observed_at": current.get("observed_at"),
                "system_available_at": current.get("system_available_at"),
            })
        valid: list[Mapping[str, object]] = []
        for proof in candidate_evidence:
            relation = str(proof.get("entity_relation") or proof.get("relation") or "").upper()
            accepted = SAME_ENTITY_EVIDENCE_CLASSES if relation == "SAME_ENTITY" else DISTINCT_ENTITY_EVIDENCE_CLASSES
            if _valid_relation_evidence(
                proof, relation=relation, candidate_keys=keys, candidate_ids=ids,
                verified_digests=verified, accepted_classes=accepted,
            ):
                valid.append(proof)
        outcomes = {
            (str(proof.get("entity_relation") or proof.get("relation") or "").upper(),
             str(proof.get("canonical_security_id") or proof.get("security_id") or ""),
             tuple(sorted(str(value) for value in proof.get("security_ids", []) if str(value))))
            for proof in valid
        }
        if len(outcomes) == 1:
            relation, canonical_id, _ = next(iter(outcomes))
            proof = valid[0]
            if relation == "SAME_ENTITY" and canonical_id:
                event["resolution_status"] = "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
                event["resolved_security_id"] = canonical_id
                event["resolution_reason"] = "POLICY_ACCEPTED_HASH_VERIFIED_SAME_ENTITY_EVIDENCE"
            elif relation == "DISTINCT_ENTITY":
                event["resolution_status"] = "CONFIRMED_DISTINCT_ENTITY"
                event["resolved_security_id"] = None
                event["resolution_reason"] = "POLICY_ACCEPTED_HASH_VERIFIED_DISTINCT_ISSUER_EVIDENCE"
            else:
                event["resolution_status"] = "UNRESOLVED"
                event["resolved_security_id"] = None
                event["resolution_reason"] = "POLICY_ACCEPTED_EVIDENCE_LACKS_REQUIRED_IDENTITY_FIELDS"
            event["resolution_evidence"] = [proof]
        else:
            event["resolution_status"] = "UNRESOLVED"
            event["resolved_security_id"] = None
            event["resolution_reason"] = (
                "CONFLICTING_POLICY_ACCEPTED_RELATION_EVIDENCE" if len(outcomes) > 1
                else "CANDIDATE_LACKS_POLICY_ACCEPTED_DATED_IDENTITY_EVIDENCE"
            )
            event["resolution_evidence"] = []
        event["affected_boards"] = sorted({_board_for(key, identity_map.get(key)) for key in keys})
        event["required_scope_affected"] = any(board in REQUIRED_BOARDS for board in event["affected_boards"])
        status_counts[str(event["resolution_status"])] += 1

    unresolved_required = sum(
        event["resolution_status"] == "UNRESOLVED" and event["required_scope_affected"] for event in events
    )
    return {
        "contract_id": "SECURITY_IDENTITY_EVENT_DISCOVERY_V1",
        "version": "1.0.0",
        "identity_relation_policy": {
            "contract_id": RELATION_POLICY_ID,
            "version": RELATION_POLICY_VERSION,
        },
        "mode": mode,
        "target_date": _date(target_date).isoformat() if _date(target_date) else None,
        "status": "PASS" if unresolved_required == 0 else "BLOCKED",
        "session_count": len(sessions),
        "signal_counts": signal_counts,
        "candidate_count": len(events),
        "candidate_status_counts": dict(sorted(status_counts.items())),
        "unresolved_required_scope_candidate_count": unresolved_required,
        "required_scope": list(REQUIRED_BOARDS),
        "events": events,
        "fail_closed": {
            "weak_signal_can_merge_identity": False,
            "unresolved_candidate_identity": "UNKNOWN_FOR_AFFECTED_CAPABILITY",
            "required_scope_unresolved_limit": 0,
        },
    }
