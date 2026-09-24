"""FOCUS-03 formal core publication gates."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .daily_plan import PlannedDay
from .input_manifest import DailyInputManifest, require_release_ready
from .replay import require_replay_clear
from .source_reader import AcceptedSources


CONTRACT_ID = "FOCUS_CORE_PUBLICATION_GATE_V1"
DEFAULT_GATE_PATH = Path("config/focus_core_release_gate_v1.json")


def require_core_publication_ready(*, manifest: DailyInputManifest,
                                   sources: AcceptedSources,
                                   plan: PlannedDay,
                                   expected_trade_date: date,
                                   repository=None,
                                   gate_path: Path = DEFAULT_GATE_PATH) -> None:
    """Reject historical, stale, partial-calendar or runtime-only publication.

    Degraded source-family capability can still publish if it is explicitly
    recorded by the source reader; historical reconstruction never activates
    the forward head.
    """
    require_release_ready(manifest)
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        minimum_date = date.fromisoformat(gate["minimum_forward_trade_date"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("Focus release gate contract unavailable") from exc
    if (gate.get("contract_id") != CONTRACT_ID or
            gate.get("date_basis") != "MASTER_TRADING_CALENDAR" or
            gate.get("formal_activation_enabled") is not True):
        raise ValueError("Focus release gate contract identity mismatch")
    if expected_trade_date < minimum_date:
        raise ValueError("trade date predates formal Focus cutover")
    payload = manifest.payload
    if manifest.trade_date != expected_trade_date:
        raise ValueError("Focus source date is not the expected trade date")
    if sources.trade_date != expected_trade_date or plan.trade_date != expected_trade_date:
        raise ValueError("Focus source/plan date mismatch")
    if payload.get("evaluation_basis") != "REAL_FORWARD":
        raise ValueError("historical reconstruction cannot activate a Focus head")
    if payload.get("calendar_scope") != "MASTER_COMPLETE":
        raise ValueError("Focus activation requires a complete master calendar")
    if payload.get("dependency_lock_kind") != "VERSIONED_LOCK":
        raise ValueError("Focus activation requires the versioned dependency lock")
    if not sources.publication_id or not sources.source_identity_digest:
        raise ValueError("accepted publication authority identity unavailable")
    if repository is not None:
        require_replay_clear(repository, before_trade_date=expected_trade_date)
