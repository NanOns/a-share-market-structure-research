from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from workbench_analysis.dated_security_alias import DatedSecurityAliasResolver
from workbench_analysis.special_price_phases import (
    PhasePolicyRegistry, SpecialPhaseEvent, SpecialPhaseEventStore, SpecialPricePhase,
    apply_phase_event, resolve_event_phase,
)
from capture_special_phase_sources import AllowlistedRedirectHandler, bounded_fetch, checked_url


def event(phase: SpecialPricePhase, sid: str, *, day="2031-04-07", **extra):
    row = {"event_id": f"{sid}-{phase.value}", "security_id": sid, "trade_date": day, "phase": phase.value,
           "phase_effective_from": day, "phase_effective_to": None, "exchange": "QX", "board": "GROWTH",
           "board_scope": "GROWTH", "event_type": "SYNTHETIC_EVENT", "source_ref": "https://fixture.example/evidence",
           "source_capture_path": "tests/fixture.pdf", "source_capture_sha256": "c" * 64,
           "observed_at": "2031-04-06T10:00:00+00:00", "system_available_at": "2031-04-06T10:00:00+00:00",
           "quality": "SYNTHETIC", "contract_id": "SPECIAL_PRICE_PHASE_EVENT_V1", "revision": 1}
    row.update(extra)
    return SpecialPhaseEvent.from_mapping(row)


def policies(duration: int | None = None):
    contract = json.loads((ROOT / "config/special_price_phase_policy_v1.json").read_text(encoding="utf-8"))
    if duration is not None:
        for row in contract["policies"]:
            if row["phase"] == "DELISTING_PERIOD":
                row["trading_sessions_including_first_day"] = duration
    return PhasePolicyRegistry(contract)


def test_synthetic_alias_changes_at_effective_boundary_and_keeps_identity():
    resolver = DatedSecurityAliasResolver([
        {"security_id": "NEVER-SEEN-A", "source_security_key": "QX.OLD", "effective_from": "2030-01-01",
         "effective_to": "2031-04-06", "exchange": "QX", "board": "GROWTH", "alias_role": "PRIMARY",
         "source_revision": "rev-old", "evidence_ref": "fixture://old", "evidence_hash": "1" * 64},
        {"security_id": "NEVER-SEEN-A", "source_security_key": "QX.NEW", "effective_from": "2031-04-07",
         "effective_to": None, "exchange": "QX", "board": "GROWTH", "alias_role": "PRIMARY",
         "source_revision": "rev-new", "evidence_ref": "fixture://new", "evidence_hash": "2" * 64},
    ])
    assert resolver.resolve_alias("NEVER-SEEN-A", "2031-04-06") == "QX.OLD"
    assert resolver.resolve_alias("NEVER-SEEN-A", "2031-04-07") == "QX.NEW"
    assert resolver.resolve_board("NEVER-SEEN-A", "2031-04-07") == "GROWTH"
    assert {row.security_id for row in resolver.records} == {"NEVER-SEEN-A"}


def test_any_synthetic_delisting_start_is_no_limit_without_code_branch():
    policies_ = policies()
    first = event(SpecialPricePhase.DELISTING_FIRST_DAY, "SEC-SYNTH-NOT-IN-HISTORY")
    phase, selected = resolve_event_phase(SpecialPhaseEventStore([first]), first.security_id, first.trade_date,
                                          ["2031-04-07", "2031-04-08"], policies_)
    result = apply_phase_event({"trade_date": first.trade_date, "board_scope": first.board_scope}, phase, selected, policies_)
    assert phase == SpecialPricePhase.DELISTING_FIRST_DAY
    assert result["limit_status"] == "NO_LIMIT"


def test_synthetic_ipo_phase_uses_contract_and_dispatches_no_limit():
    policy = policies()
    row = event(SpecialPricePhase.IPO_FIRST_5_TRADING_DAYS, "SEC-SYNTH-IPO")
    sessions = ["2031-04-07", "2031-04-08", "2031-04-09", "2031-04-10", "2031-04-11", "2031-04-14"]
    phase, selected = resolve_event_phase(SpecialPhaseEventStore([row]), row.security_id, sessions[2], sessions, policy)
    output = apply_phase_event({"trade_date": sessions[2], "board_scope": row.board_scope}, phase, selected, policy)
    assert phase == SpecialPricePhase.IPO_FIRST_5_TRADING_DAYS
    assert output["limit_status"] == "NO_LIMIT"


def test_duration_follows_contract_value_of_ten_sessions():
    policy = policies(10)
    first = event(SpecialPricePhase.DELISTING_FIRST_DAY, "SEC-SYNTH-DURATION")
    sessions = ["2031-04-07", "2031-04-08", "2031-04-09", "2031-04-10", "2031-04-11",
                "2031-04-14", "2031-04-15", "2031-04-16", "2031-04-17", "2031-04-18", "2031-04-21"]
    store = SpecialPhaseEventStore([first])
    phase_nine, _ = resolve_event_phase(store, first.security_id, sessions[9], sessions, policy)
    phase_ten, _ = resolve_event_phase(store, first.security_id, sessions[10], sessions, policy)
    assert phase_nine == SpecialPricePhase.DELISTING_PERIOD
    assert phase_ten == SpecialPricePhase.REGULAR


def test_synthetic_relisting_first_day_consumed_as_no_limit():
    policy = policies()
    row = event(SpecialPricePhase.RELISTING_FIRST_DAY, "SEC-SYNTH-RELIST")
    phase, selected = resolve_event_phase(SpecialPhaseEventStore([row]), row.security_id, row.trade_date, [row.trade_date], policy)
    result = apply_phase_event({"trade_date": row.trade_date, "board_scope": row.board_scope}, phase, selected, policy)
    assert result["limit_status"] == "NO_LIMIT"


def test_synthetic_special_reference_reset_supports_official_formula():
    policy = policies()
    row = event(SpecialPricePhase.SPECIAL_REFERENCE_RESET, "SEC-SYNTH-RESET",
                official_reference_formula={"op": "ADD", "left": {"op": "CONST", "value": "4.00"},
                                            "right": {"op": "CONST", "value": "1.00"}})
    result = apply_phase_event({"trade_date": row.trade_date, "board_scope": row.board_scope},
                               SpecialPricePhase.SPECIAL_REFERENCE_RESET, row, policy,
                               close="5.00",
                               regular_rule={"limit_ratio": "0.10", "tick": "0.01", "rounding_mode": "HALF_UP",
                                             "minimum_price_movement_ticks": 1, "rule_id": "synthetic-rule"})
    assert result["reference_price"] == "5.00"
    assert result["limit_up_price"] == "5.50"


def test_synthetic_unknown_special_phase_fails_closed():
    policy = policies()
    row = event(SpecialPricePhase.UNKNOWN_SPECIAL_PHASE, "SEC-SYNTH-UNKNOWN")
    result = apply_phase_event({"trade_date": row.trade_date, "board_scope": row.board_scope}, row.phase, row, policy)
    assert result["limit_status"] == "UNKNOWN"
    assert result["reason"] == "SPECIAL_PHASE_EVIDENCE_UNAVAILABLE"


def test_generic_runtime_and_builders_contain_no_security_specific_branches():
    files = list((ROOT / "src/workbench_analysis").rglob("*.py"))
    files += list((ROOT / "scripts").glob("build_v4_02*.py"))
    files.append(ROOT / "scripts/capture_special_phase_sources.py")
    forbidden = re.compile(r"(?:SZ|SH)\.\d{6}|SEC-EDEDE35FE66896ACCA0AC85EEB2F133B|SEC-B2F87F189D1D143B67730E3640E617CA")
    findings = [(str(path.relative_to(ROOT)), forbidden.findall(path.read_text(encoding="utf-8")))
                for path in files if forbidden.search(path.read_text(encoding="utf-8"))]
    assert not findings


def test_source_capture_rejects_non_allowlisted_redirect_and_over_limit(monkeypatch):
    allow = {"allowed.example"}
    with pytest.raises(ValueError, match="NOT_ALLOWED"):
        checked_url("https://outside.example/file.pdf", allow)
    handler = AllowlistedRedirectHandler(allow)
    with pytest.raises(ValueError, match="NOT_ALLOWED"):
        handler.redirect_request(None, None, 302, "Found", {}, "https://outside.example/file.pdf")

    class Headers:
        def get_content_type(self): return "application/pdf"

    class Response:
        headers = Headers()
        def __init__(self, data): self.data = data
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return "https://allowed.example/file.pdf"
        def read(self, size): return self.data[:size]

    class Opener:
        def open(self, request, timeout): return Response(b"%PDF-" + b"x" * 16)

    monkeypatch.setattr("capture_special_phase_sources.urllib.request.build_opener", lambda *handlers: Opener())
    with pytest.raises(ValueError, match="EXCEEDS_MAXIMUM"):
        bounded_fetch("https://allowed.example/file.pdf", allowed_hosts=allow, timeout=1, max_bytes=8, content_type="application/pdf")
