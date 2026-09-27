from __future__ import annotations

"""Recompute special-phase Price Limit outputs through the generic R6 runtime."""

import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis import special_price_phases as phase_runtime
from workbench_analysis.dated_security_alias import DatedSecurityAliasResolver
from workbench_analysis.special_price_phases import PhasePolicyRegistry, SpecialPhaseEvent, SpecialPhaseEventStore, SpecialPricePhase

BASE_PRICE = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R7_20260927.jsonl.gz"
DAILY = ROOT / "data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet"
CALENDAR = ROOT / "data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2/calendar_sse_20230704_20260924.json"
EVENTS = ROOT / "data/v4/bootstrap/special_price_phase_events_r4.jsonl"
ALIASES = ROOT / "data/v4/bootstrap/dated_security_alias_r7.jsonl"
POLICY = ROOT / "config/special_price_phase_policy_r6.json"
RULES = ROOT / "config/v4_02_price_limit_rules_r3.json"
R4_RANGE_AUDIT = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4.json"
OUT = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R6_20260927.jsonl.gz"
RECEIPT = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_BUILD_R6.json"

BUSINESS_FIELDS = (
    "security_id", "trade_date", "special_price_phase", "limit_status", "reason", "reference_price",
    "limit_up_price", "limit_down_price", "rule_id", "reference_basis", "risk_status", "is_st",
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(obj, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def atomic_replace(source: str, target: Path) -> None:
    with open(source, "r+b") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(source, target)


def _day(value: object) -> str:
    text = str(value or "").replace("/", "-")
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return date.fromisoformat(text[:10]).isoformat()


def compile_event_phase_index(store: SpecialPhaseEventStore, sessions: Iterable[str],
                              policies: PhasePolicyRegistry) -> dict[tuple[str, str], tuple[SpecialPricePhase, SpecialPhaseEvent]]:
    days = [_day(x) for x in sessions]
    indices = {day: i for i, day in enumerate(days)}
    candidates: set[tuple[str, str]] = set()
    for event in store.events:
        start = _day(event.phase_effective_from)
        if start not in indices:
            if event.phase in {SpecialPricePhase.DELISTING_FIRST_DAY, SpecialPricePhase.IPO_FIRST_5_TRADING_DAYS}:
                raise ValueError("SPECIAL_PHASE_START_NOT_IN_FORMAL_CALENDAR")
            continue
        start_idx = indices[start]
        if event.phase == SpecialPricePhase.DELISTING_FIRST_DAY:
            length = policies.delisting_sessions(start, event.board_scope)
            end_idx = min(len(days), start_idx + length)
        elif event.phase == SpecialPricePhase.IPO_FIRST_5_TRADING_DAYS:
            rule = policies.policy_for(event.phase, start, event.board_scope)
            length = int((rule or {}).get("trading_sessions_including_first_day", 0))
            end_idx = min(len(days), start_idx + length)
        elif event.phase_effective_to:
            end_day = _day(event.phase_effective_to)
            end_idx = next((i + 1 for i in range(start_idx, len(days)) if days[i] > end_day), len(days))
        else:
            end_idx = start_idx + 1
        for day in days[start_idx:end_idx]:
            candidates.add((event.security_id, day))
    planned = {}
    for security_id, day in candidates:
        phase, event = phase_runtime.resolve_event_phase(store, security_id, day, days, policies)
        if event is not None and phase != SpecialPricePhase.REGULAR:
            planned[(security_id, day)] = (phase, event)
    return planned


def load_unknown_facts(path: Path) -> dict[tuple[str, str], str]:
    audit = json.loads(path.read_text(encoding="utf-8"))
    facts: dict[tuple[str, str], str] = {}
    for row in audit.get("dispositions", []):
        if (row.get("disposition") == "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED"
                and row.get("r3_reason") is None and row.get("unknown_reason")):
            key = (str(row.get("security_id") or ""), _day(row.get("trade_date")))
            facts[key] = str(row["unknown_reason"])
    expected = int(audit.get("scope", {}).get("r3_fail_closed_dispositioned", 0))
    if len(facts) != expected or expected != 31:
        raise ValueError("R4_FAIL_CLOSED_FACTS_DO_NOT_MATCH_ACCEPTED_SCOPE")
    return facts


def load_close_lookup(parquet: Path, security_ids: set[str]) -> dict[tuple[str, str], str]:
    if not security_ids:
        return {}
    import duckdb
    connection = duckdb.connect()
    try:
        relation = connection.read_parquet(str(parquet))
        # Event identities are read from the accepted immutable event store;
        # SQL string values are still escaped before constructing the filter.
        literals = ",".join("'" + sid.replace("'", "''") + "'" for sid in sorted(security_ids))
        rows = relation.filter(f"canonical_security_id IN ({literals})") \
                       .project("canonical_security_id, trade_date, raw_close").fetchall()
    finally:
        connection.close()
    return {(str(sid), _day(day)): str(close) for sid, day, close in rows if close is not None}


def standard_rule_for(row: Mapping[str, object], policies: PhasePolicyRegistry,
                      rules: Iterable[Mapping[str, object]]) -> Mapping[str, object] | None:
    scope = str(row.get("board_scope") or "")
    key = policies.standard_rule_key(_day(row.get("trade_date")), scope)
    if key is None:
        return None
    exchange, board = key
    day, risk = _day(row.get("trade_date")), str(row.get("risk_status") or "")
    found = [rule for rule in rules if (str(rule.get("exchange")), str(rule.get("board")), str(rule.get("risk_status"))) == (exchange, board, risk)
             and str(rule.get("valid_from", "0001-01-01")) <= day
             and (rule.get("valid_to") is None or day <= str(rule["valid_to"]))]
    if len(found) > 1:
        raise ValueError("STANDARD_LIMIT_RULE_AMBIGUOUS")
    if not found:
        return None
    rule = found[0]
    return {"limit_ratio": rule.get("limit_ratio"), "tick": rule.get("tick"),
            "rounding_mode": rule.get("rounding_mode"), "minimum_price_movement_ticks": 1,
            "rule_id": rule.get("rule_id")}


def apply_row_runtime(row: Mapping[str, object], store: SpecialPhaseEventStore,
                      policies: PhasePolicyRegistry, sessions: Iterable[str], *,
                      phase_index: Mapping[tuple[str, str], tuple[SpecialPricePhase, SpecialPhaseEvent]] | None = None,
                      close_lookup: Mapping[tuple[str, str], str] | None = None,
                      unknown_facts: Mapping[tuple[str, str], str] | None = None,
                      alias_resolver: DatedSecurityAliasResolver | None = None,
                      standard_rules: Iterable[Mapping[str, object]] = ()) -> tuple[dict, SpecialPricePhase, bool]:
    result = dict(row)
    security_id, day = str(row.get("security_id") or ""), _day(row.get("trade_date"))
    board = str(row.get("board_scope") or "")
    if alias_resolver is not None:
        aliases = alias_resolver.records_for(security_id, day)
        if aliases:
            alias, fact_board = alias_resolver.resolve_alias(security_id, day), alias_resolver.resolve_board(security_id, day)
            if alias != row.get("source_security_key") or fact_board != board:
                raise ValueError("ACCEPTED_DATED_ALIAS_BINDING_MISMATCH")
    planned = (phase_index or {}).get((security_id, day))
    if planned is None:
        phase, event = phase_runtime.resolve_event_phase(store, security_id, day, sessions, policies, board)
    else:
        phase, event = planned
    unknown_reason = None
    if phase == SpecialPricePhase.REGULAR and event is None:
        unknown_reason = (unknown_facts or {}).get((security_id, day))
        if unknown_reason:
            phase = SpecialPricePhase.UNKNOWN_SPECIAL_PHASE
        elif row.get("reason") == "IPO_FIRST_5_TRADING_DAYS":
            phase = SpecialPricePhase.IPO_FIRST_5_TRADING_DAYS
    runtime_called = phase != SpecialPricePhase.REGULAR
    if runtime_called:
        regular_rule = standard_rule_for(row, policies, standard_rules) if phase == SpecialPricePhase.SPECIAL_REFERENCE_RESET else None
        close = (close_lookup or {}).get((security_id, day))
        result = phase_runtime.apply_phase_event(row, phase, event, policies, close=close,
                                                 regular_rule=regular_rule, unknown_reason=unknown_reason)
        policy = policies.policy_for(phase, day, board)
        result["phase_policy_id"] = (policy or {}).get("policy_id")
        if event is not None:
            result["event_id"] = event.event_id
            result["event_revision"] = event.revision
    else:
        result["special_price_phase"] = SpecialPricePhase.REGULAR.value
    result["contract_id"] = "PRICE_LIMIT_RULE_R6"
    return result, phase, runtime_called


def business_payload(row: Mapping[str, object]) -> dict:
    return {field: row.get(field) for field in BUSINESS_FIELDS}


def run_builder(*, base_price: Path = BASE_PRICE, daily: Path = DAILY, calendar_path: Path = CALENDAR,
                events_path: Path = EVENTS, aliases_path: Path = ALIASES, policy_path: Path = POLICY,
                rules_path: Path = RULES, unknown_audit_path: Path = R4_RANGE_AUDIT,
                output_path: Path = OUT, receipt_path: Path = RECEIPT) -> dict:
    required = (base_price, daily, calendar_path, events_path, aliases_path, policy_path, rules_path, unknown_audit_path)
    if not all(path.is_file() for path in required):
        raise FileNotFoundError("R6_GENERIC_PRICE_LIMIT_INPUT_MISSING")
    calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
    sessions = tuple(calendar["session_dates"])
    store = SpecialPhaseEventStore.from_jsonl(events_path)
    policies = PhasePolicyRegistry.from_json(policy_path)
    alias_resolver = DatedSecurityAliasResolver.from_jsonl(aliases_path)
    rules = json.loads(rules_path.read_text(encoding="utf-8"))["rules"]
    unknown_facts = load_unknown_facts(unknown_audit_path)
    phase_index = compile_event_phase_index(store, sessions, policies)
    close_lookup = load_close_lookup(daily, {event.security_id for event in store.events})
    phase_counts: Counter[str] = Counter()
    calls: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    business_digest, normalized_digest = hashlib.sha256(), hashlib.sha256()
    rows = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=output_path.name + ".", suffix=".tmp", dir=output_path.parent)
    os.close(fd)
    try:
        with gzip.open(base_price, "rt", encoding="utf-8") as source, gzip.open(temp, "wt", encoding="utf-8", newline="\n", compresslevel=6) as target:
            for line in source:
                base_row = json.loads(line)
                output_row, phase, called = apply_row_runtime(base_row, store, policies, sessions, phase_index=phase_index,
                    close_lookup=close_lookup, unknown_facts=unknown_facts, alias_resolver=alias_resolver, standard_rules=rules)
                phase_counts[phase.value] += 1
                if called:
                    calls[phase.value] += 1
                statuses[str(output_row.get("limit_status") or "UNKNOWN")] += 1
                normalized = json.dumps(output_row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                target.write(normalized)
                normalized_digest.update(normalized.encode("utf-8"))
                business = json.dumps(business_payload(output_row), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                business_digest.update(business.encode("utf-8"))
                rows += 1
                if rows % 500_000 == 0:
                    print(json.dumps({"r6_rows_written": rows, "phase_counts": dict(phase_counts)}, ensure_ascii=False), flush=True)
        atomic_replace(temp, output_path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    receipt = {
        "contract_id": "V4_02_PRICE_LIMIT_BUILD_R6", "version": "6.0.0", "status": "R6_CANDIDATE_READY",
        "stage_contract": "R3_PRICE_LIMIT_BASE + SPECIAL_PRICE_PHASE_EVENT_V1 + SPECIAL_PRICE_PHASE_POLICY_V2",
        "row_count": rows, "special_phase_counts": dict(phase_counts), "apply_phase_event_call_counts": dict(calls),
        "limit_status_counts": dict(statuses), "unknown_rows": statuses.get("UNKNOWN", 0),
        "business_fields": list(BUSINESS_FIELDS), "business_payload_sha256": business_digest.hexdigest(),
        "artifact": {"path": str(output_path.relative_to(ROOT)).replace("\\", "/"), "bytes": output_path.stat().st_size,
                     "sha256": sha(output_path), "normalized_rows_sha256": normalized_digest.hexdigest()},
        "inputs": {"r3_price_base_sha256": sha(base_price), "adjusted_daily_sha256": sha(daily),
                   "calendar_sha256": sha(calendar_path), "event_store_sha256": sha(events_path),
                   "dated_alias_facts_sha256": sha(aliases_path), "phase_policy_sha256": sha(policy_path),
                   "standard_price_rules_sha256": sha(rules_path), "r4_fail_closed_facts_sha256": sha(unknown_audit_path)},
        "tdx_root_write_count": 0, "scanner_factor_trading_runs": 0,
        "execution_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                           text=True, check=True).stdout.strip(),
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "next_stage": "INDEPENDENT_R6_BUSINESS_POSTCHECK_AND_R6_FINAL_RESEAL; V4-03_BLOCKED",
    }
    atomic_json(receipt_path, receipt)
    return receipt


def main() -> int:
    result = run_builder()
    print(json.dumps({"status": result["status"], "row_count": result["row_count"],
                      "special_phase_counts": result["special_phase_counts"],
                      "apply_phase_event_call_counts": result["apply_phase_event_call_counts"],
                      "business_payload_sha256": result["business_payload_sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
