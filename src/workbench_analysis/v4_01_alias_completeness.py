from __future__ import annotations

"""Generic discovery and fail-closed resolution for historical code changes."""

from collections import defaultdict
from datetime import date
from hashlib import sha256
from itertools import combinations
from typing import Iterable, Mapping

from workbench_analysis.dated_security_alias import DatedAliasRecord

REQUIRED_BOARDS = ("SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR")
RESOLUTION_STATUSES = frozenset(
    {
        "CONFIRMED_SAME_ENTITY_CODE_CHANGE",
        "CONFIRMED_DISTINCT_ENTITY",
        "UNRESOLVED",
        "NOT_APPLICABLE",
    }
)
RAW_BAR_FIELDS = ("raw_open", "raw_high", "raw_low", "raw_close", "volume", "amount")


def _day(value: object | None) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    return date.fromisoformat(str(value).replace("-", "")) if len(str(value)) == 8 else date.fromisoformat(str(value))


def _record_key(row: Mapping[str, object]) -> str:
    return str(row.get("source_security_key") or row.get("symbol") or "").upper()


def _record_id(row: Mapping[str, object]) -> str:
    return str(row.get("canonical_security_id") or row.get("security_id") or "")


def _active_on(row: Mapping[str, object], day: date) -> bool:
    start = _day(row.get("effective_from", row.get("symbol_effective_from")))
    end = _day(row.get("effective_to", row.get("symbol_effective_to")))
    return start is not None and start <= day and (end is None or day <= end)


def discover_exact_bar_continuity_candidates(
    rows: Iterable[Mapping[str, object]], *, minimum_shared_sessions: int = 20
) -> list[dict[str, object]]:
    """Find persistent identical raw-bar series assigned to different source IDs.

    One-day price coincidences are deliberately not candidates. Candidate generation
    uses no security-code literals and does not itself merge identities.
    """
    if minimum_shared_sessions < 1:
        raise ValueError("ALIAS_CANDIDATE_MINIMUM_SESSIONS_MUST_BE_POSITIVE")

    signatures: dict[tuple[object, ...], dict[str, dict[str, object]]] = defaultdict(dict)
    for row in rows:
        source_key = _record_key(row)
        identity_id = _record_id(row)
        trade_date = _day(row.get("trade_date"))
        if not source_key or not identity_id or trade_date is None:
            continue
        raw_values = tuple(row.get(field) for field in RAW_BAR_FIELDS)
        if any(value is None for value in raw_values):
            continue
        signature = (trade_date, *raw_values)
        signatures[signature][source_key] = {
            "security_id": identity_id,
            "board": str(row.get("board_scope") or row.get("board") or ""),
        }

    shared_dates: dict[tuple[str, str], set[date]] = defaultdict(set)
    baseline_assignments: dict[tuple[str, str], tuple[str, str]] = {}
    for signature, assignments in signatures.items():
        keys = sorted(assignments)
        for left, right in combinations(keys, 2):
            left_id = str(assignments[left]["security_id"])
            right_id = str(assignments[right]["security_id"])
            if left_id == right_id:
                continue
            pair = (left, right)
            shared_dates[pair].add(signature[0])  # type: ignore[arg-type]
            baseline_assignments[pair] = (left_id, right_id)

    output: list[dict[str, object]] = []
    for pair, days in sorted(shared_dates.items()):
        if len(days) < minimum_shared_sessions:
            continue
        left_id, right_id = baseline_assignments[pair]
        ordered_days = sorted(days)
        output.append(
            {
                "source_keys": list(pair),
                "security_ids": [left_id, right_id],
                "shared_identical_raw_bar_sessions": len(days),
                "first_shared_date": ordered_days[0].isoformat(),
                "last_shared_date": ordered_days[-1].isoformat(),
                "candidate_reason": "PERSISTENT_IDENTICAL_RAW_OHLCV_AMOUNT_ACROSS_SPLIT_STABLE_IDS",
            }
        )
    return output


def pair_summary_candidates(
    summaries: Iterable[Mapping[str, object]], *, minimum_shared_sessions: int = 20
) -> list[dict[str, object]]:
    """Validate and normalize pair summaries returned by a columnar exact-match scan."""
    output: list[dict[str, object]] = []
    for row in summaries:
        count = int(row.get("shared_identical_raw_bar_sessions") or row.get("identical_raw_bar_dates") or 0)
        left = str(row.get("old_source_security_key") or row.get("code_a") or "").upper()
        right = str(row.get("new_source_security_key") or row.get("code_b") or "").upper()
        left_id = str(row.get("old_security_id") or row.get("id_a") or "")
        right_id = str(row.get("new_security_id") or row.get("id_b") or "")
        if count < minimum_shared_sessions or not left or not right or not left_id or not right_id or left_id == right_id:
            continue
        keys = sorted((left, right))
        ids_by_key = {left: left_id, right: right_id}
        first_value = row.get("first_shared_date") or row.get("first_date")
        last_value = row.get("last_shared_date") or row.get("last_date")
        first_day = _day(first_value)
        last_day = _day(last_value)
        first = first_day.isoformat() if first_day else ""
        last = last_day.isoformat() if last_day else ""
        output.append(
            {
                "source_keys": keys,
                "security_ids": [ids_by_key[key] for key in keys],
                "shared_identical_raw_bar_sessions": count,
                "first_shared_date": first,
                "last_shared_date": last,
                "candidate_reason": "PERSISTENT_IDENTICAL_RAW_OHLCV_AMOUNT_ACROSS_SPLIT_STABLE_IDS",
            }
        )
    return sorted(output, key=lambda item: tuple(item["source_keys"]))


def candidate_id(source_keys: Iterable[str]) -> str:
    value = "|".join(sorted(str(key).upper() for key in source_keys))
    return "CC-" + sha256(value.encode("utf-8")).hexdigest()[:24].upper()


def classify_candidate(
    summary: Mapping[str, object],
    *,
    baseline_identity_by_key: Mapping[str, Mapping[str, object]],
    final_identity_by_key: Mapping[str, Mapping[str, object]],
    alias_facts: Iterable[Mapping[str, object]],
    verified_evidence_digests: set[str],
    evidence_refs: list[str],
    evidence_digests: list[str],
) -> dict[str, object]:
    """Resolve only when dated alias facts share a stable ID and verified evidence."""
    keys = [str(key).upper() for key in summary["source_keys"]]  # type: ignore[index]
    facts_by_key: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for fact in alias_facts:
        facts_by_key[_record_key(fact)].append(fact)

    fact_records = [fact for key in keys for fact in facts_by_key.get(key, [])]
    all_valid_evidence = bool(fact_records) and all(
        str(fact.get("evidence_hash") or "").lower() in verified_evidence_digests for fact in fact_records
    )
    fact_ids = {str(fact.get("security_id") or "") for fact in fact_records}
    roles = {str(fact.get("alias_role") or "").upper() for fact in fact_records}
    facts_cover_keys = { _record_key(fact) for fact in fact_records } == set(keys)
    same_entity = all_valid_evidence and facts_cover_keys and len(fact_ids) == 1 and {"PREDECESSOR", "CURRENT"}.issubset(roles)
    resolved_id = next(iter(fact_ids)) if same_entity else None
    final_ids = {str(final_identity_by_key.get(key, {}).get("security_id") or "") for key in keys}
    if same_entity and (final_ids != {resolved_id}):
        same_entity = False
        resolved_id = None

    chronological = sorted(
        fact_records,
        key=lambda fact: str(fact.get("effective_from") or fact.get("symbol_effective_from") or "9999-12-31"),
    )
    if same_entity:
        old_fact, new_fact = chronological[0], chronological[-1]
        old_key = _record_key(old_fact)
        new_key = _record_key(new_fact)
        status = "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
        reason_code = "OFFICIAL_DATED_ALIAS_FACT_AND_VERIFIED_EXCHANGE_EVIDENCE"
        effective_date_candidate = str(new_fact.get("effective_from") or new_fact.get("symbol_effective_from"))
        old_board = str(old_fact.get("board") or "")
        new_board = str(new_fact.get("board") or "")
        exchange = str(new_fact.get("exchange") or old_fact.get("exchange") or "")
    else:
        assignments = {
            key: baseline_identity_by_key.get(key, {}) for key in keys
        }
        ranked = sorted(
            keys,
            key=lambda key: str(assignments[key].get("symbol_effective_from") or assignments[key].get("list_date") or "9999-12-31"),
        )
        old_key, new_key = ranked[0], ranked[-1]
        old_board = str(assignments[old_key].get("board") or "")
        new_board = str(assignments[new_key].get("board") or "")
        exchange = str(assignments[new_key].get("exchange") or assignments[old_key].get("exchange") or "")
        effective_date_candidate = None
        status = "UNRESOLVED"
        reason_code = "CANDIDATE_LACKS_VERIFIED_DATED_IDENTITY_EVIDENCE"
        resolved_id = None

    baseline_by_key = {key: baseline_identity_by_key.get(key, {}) for key in keys}
    final_by_key = {key: final_identity_by_key.get(key, {}) for key in keys}
    evidence = list(dict.fromkeys([*evidence_refs, *(str(f.get("evidence_ref") or "") for f in fact_records if f.get("evidence_ref"))]))
    digests = list(dict.fromkeys([*evidence_digests, *(str(f.get("evidence_hash") or "") for f in fact_records if f.get("evidence_hash"))]))
    return {
        "candidate_id": candidate_id(keys),
        "old_source_security_key": old_key,
        "new_source_security_key": new_key,
        "old_security_id": str(baseline_by_key[old_key].get("security_id") or ""),
        "new_security_id": str(baseline_by_key[new_key].get("security_id") or ""),
        "candidate_reason": str(summary.get("candidate_reason") or ""),
        "effective_date_candidate": effective_date_candidate,
        "exchange": exchange,
        "old_board": old_board,
        "new_board": new_board,
        "baseline_old_board": str(baseline_by_key[old_key].get("board") or ""),
        "baseline_new_board": str(baseline_by_key[new_key].get("board") or ""),
        "dated_fact_board": sorted({str(fact.get("board") or "") for fact in fact_records if fact.get("board")}),
        "shared_identical_raw_bar_sessions": int(summary.get("shared_identical_raw_bar_sessions") or 0),
        "first_shared_date": summary.get("first_shared_date"),
        "last_shared_date": summary.get("last_shared_date"),
        "evidence_refs": evidence,
        "evidence_digests": digests,
        "resolution_status": status,
        "resolved_security_id": resolved_id,
        "reason_code": reason_code,
    }


def validate_alias_interval_integrity(alias_facts: Iterable[Mapping[str, object]]) -> dict[str, int]:
    """Check inclusive interval conflicts per alias and per stable entity."""
    records = [DatedAliasRecord.from_mapping(row) for row in alias_facts]
    alias_conflicts = 0
    entity_conflicts = 0
    by_alias: dict[str, list[DatedAliasRecord]] = defaultdict(list)
    by_entity: dict[str, list[DatedAliasRecord]] = defaultdict(list)
    for record in records:
        by_alias[record.source_security_key].append(record)
        by_entity[record.security_id].append(record)

    def overlaps(left: DatedAliasRecord, right: DatedAliasRecord) -> bool:
        left_end = left.effective_to or date.max
        right_end = right.effective_to or date.max
        return left.effective_from <= right_end and right.effective_from <= left_end

    for rows in by_alias.values():
        for left, right in combinations(rows, 2):
            if left.security_id != right.security_id and overlaps(left, right):
                alias_conflicts += 1
    for rows in by_entity.values():
        for left, right in combinations(rows, 2):
            if left.source_security_key != right.source_security_key and overlaps(left, right):
                entity_conflicts += 1
    return {"alias_interval_conflicts": alias_conflicts, "entity_alias_interval_conflicts": entity_conflicts}


def validate_confirmed_alias_coverage(
    alias_facts: Iterable[Mapping[str, object]], trade_dates: Iterable[str]
) -> int:
    """Count session dates with zero or multiple alias/board resolutions."""
    facts = list(alias_facts)
    required_ids = {str(row.get("security_id") or "") for row in facts}
    errors = 0
    for security_id in required_ids:
        entity_facts = [row for row in facts if str(row.get("security_id") or "") == security_id]
        for trade_date in trade_dates:
            day = _day(trade_date)
            if day is None:
                errors += 1
                continue
            active = [row for row in entity_facts if _active_on(row, day)]
            if len(active) != 1:
                errors += 1
    return errors


def duplicate_identity_date_count(rows: Iterable[Mapping[str, object]]) -> int:
    seen: set[tuple[str, str]] = set()
    duplicates = 0
    for row in rows:
        identity_id = _record_id(row)
        trade_date = str(row.get("trade_date") or "")
        key = (identity_id, trade_date)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates


def required_scope_alias_gate_passes(report: Mapping[str, object]) -> bool:
    required = report.get("required_scope", {})
    if not isinstance(required, Mapping):
        return False
    statuses = report.get("candidate_status_counts", {})
    if not isinstance(statuses, Mapping):
        return False
    return (
        report.get("status") == "PASS"
        and all(board in required for board in REQUIRED_BOARDS)
        and int(statuses.get("UNRESOLVED", 0)) == 0
        and int(report.get("unresolved_required_scope_candidate_count", -1)) == 0
    )


def final_receipt_requires_alias_completeness_gate(alias_gate: Mapping[str, object] | None) -> bool:
    return isinstance(alias_gate, Mapping) and required_scope_alias_gate_passes(alias_gate)
