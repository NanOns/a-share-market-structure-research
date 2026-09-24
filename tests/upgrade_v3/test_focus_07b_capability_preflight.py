import json
from datetime import date
from types import SimpleNamespace as NS

import pytest

from src.focus_tracker import release_gate, source_capabilities


V33 = "TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_03_FULL_LOO"


def test_release_preflight_rejects_advertised_path_without_provider(tmp_path, monkeypatch):
    day = date(2026, 9, 24)
    gate = tmp_path / "gate.json"
    gate.write_text(json.dumps({
        "contract_id": release_gate.CONTRACT_ID,
        "date_basis": "MASTER_TRADING_CALENDAR",
        "formal_activation_enabled": True,
        "minimum_forward_trade_date": "2026-09-23"}), encoding="utf-8")
    monkeypatch.setattr(release_gate, "require_release_ready", lambda _: None)
    manifest = NS(trade_date=day, payload={
        "evaluation_basis": "REAL_FORWARD", "calendar_scope": "MASTER_COMPLETE",
        "dependency_lock_kind": "VERSIONED_LOCK"})
    sources = NS(trade_date=day, publication_id="publication",
                 source_identity_digest="s" * 64,
                 rows=(NS(key=NS(source_family="V3_3_TODAY_CANDIDATE"),
                          source_contract_id=V33),))
    plan = NS(trade_date=day)
    monkeypatch.setitem(source_capabilities._MAPPING,
                        ("V3_3_TODAY_CANDIDATE", V33),
                        frozenset({"TREND_ACCELERATING"}))
    with pytest.raises(ValueError, match="CAPABILITY_CONTRACT_BROKEN:TREND_ACCELERATING"):
        release_gate.require_core_publication_ready(
            manifest=manifest, sources=sources, plan=plan,
            expected_trade_date=day, gate_path=gate)
