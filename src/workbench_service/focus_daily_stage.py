"""Run Focus only after the exact P12 publication is accepted in PostgreSQL."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


CONTRACT_ID = "FOCUS_P12_POST_SYNC_STAGE_V1"
GATE_CONTRACT_ID = "FOCUS_DAILY_PIPELINE_GATE_V1"


def _automatic_apply_gate(root: Path) -> tuple[bool, str]:
    try:
        gate = json.loads((root / "config/focus_daily_pipeline_gate_v1.json").read_text("utf-8"))
    except (OSError, ValueError):
        return False, "FOCUS_PIPELINE_GATE_UNAVAILABLE"
    if gate.get("contract_id") != GATE_CONTRACT_ID or not isinstance(
            gate.get("automatic_apply_enabled"), bool):
        return False, "FOCUS_PIPELINE_GATE_INVALID"
    return gate["automatic_apply_enabled"], str(gate.get("reason") or "GATE_CLOSED")


def _last_report(stdout: str) -> dict[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        try:
            value = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict) and value.get("contract_id") == "FOCUS_DAILY_RUNNER_V1":
            return value
    return None


def _identity_report(stdout: str) -> dict[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        try:
            value = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict) and value.get("contract_id") == "FOCUS_TECHNICAL_IDENTITY_REGISTRATION_V1":
            return value
    return None


def run_after_pg_sync(*, root: Path, trade_date: str, publication_id: str,
                      sync_report: dict[str, Any],
                      run_command: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Preflight then apply; report Focus failure without changing P12 status."""
    if (sync_report.get("status") != "FULL_PASS" or
            str(sync_report.get("trade_date")) != trade_date or
            str(sync_report.get("publication_id")) != publication_id):
        return {"contract_id": CONTRACT_ID, "status": "FAILED",
                "reason": "PG_SYNC_IDENTITY_NOT_ACCEPTED", "core_status": "NOT_RUN"}
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "src"), str(root / "scripts"), env.get("PYTHONPATH", "")])
    identity_command = [sys.executable, "-m", "scripts.register_focus_technical_identity",
                        "--trade-date", trade_date, "--publication-id", publication_id, "--apply"]
    try:
        identity_result = run_command(identity_command, cwd=root, env=env,
                                      capture_output=True, text=True, timeout=3600)
        identity = _identity_report(identity_result.stdout or "")
        if (identity_result.returncode != 0 or identity is None or
                identity.get("status") != "ACCEPTED" or
                identity.get("trade_date") != trade_date or
                identity.get("publication_id") != publication_id or
                not identity.get("source_object_id") or
                not identity.get("legacy_hash") or
                not identity.get("canonical_hash") or
                not identity.get("evidence_sha256") or
                not isinstance(identity.get("row_count"), int) or
                identity["row_count"] < 1):
            identity = {"status": "BLOCKED", "reason": "TECHNICAL_IDENTITY_REGISTRATION_FAILED"}
    except (OSError, subprocess.TimeoutExpired) as exc:
        identity = {"status": "BLOCKED", "reason": type(exc).__name__}
    apply_enabled, gate_reason = _automatic_apply_gate(root)
    command = [sys.executable, "-m", "scripts.run_focus_daily",
               "--trade-date", trade_date]
    reports: dict[str, dict[str, Any]] = {}
    for mode in ("--preflight", "--apply"):
        try:
            result = run_command(command + [mode], cwd=root, env=env,
                                 capture_output=True, text=True, timeout=3600)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"contract_id": CONTRACT_ID, "status": "FAILED",
                    "reason": type(exc).__name__, "core_status": "UNKNOWN",
                    "completed_step": "PREFLIGHT" if mode == "--apply" else "NONE",
                    "technical_identity": identity}
        report = _last_report(result.stdout or "")
        if report is None:
            return {"contract_id": CONTRACT_ID, "status": "FAILED",
                    "reason": "FOCUS_RUNNER_REPORT_INVALID", "core_status": "UNKNOWN",
                    "completed_step": "PREFLIGHT" if mode == "--apply" else "NONE",
                    "technical_identity": identity}
        reports[mode] = report
        if report.get("trade_date") != trade_date:
            return {"contract_id": CONTRACT_ID, "status": "FAILED",
                    "reason": "FOCUS_RUNNER_IDENTITY_MISMATCH", "core_status": "UNKNOWN",
                    "technical_identity": identity}
        if mode == "--preflight" and (
                result.returncode != 0 or report.get("core_status") != "PREFLIGHT_READY"):
            return {"contract_id": CONTRACT_ID, "status": "DEGRADED",
                    "reason": str(report.get("reason") or "FOCUS_PREFLIGHT_BLOCKED"),
                    "core_status": str(report.get("core_status") or "BLOCKED"),
                    "preflight": report, "technical_identity": identity}
        if mode == "--preflight" and report.get("publication_id") != publication_id:
            return {"contract_id": CONTRACT_ID, "status": "FAILED",
                    "reason": "FOCUS_RUNNER_IDENTITY_MISMATCH", "core_status": "UNKNOWN",
                    "technical_identity": identity}
        if mode == "--preflight" and not apply_enabled:
            return {"contract_id": CONTRACT_ID, "status": "DEGRADED",
                    "reason": gate_reason, "core_status": "PREFLIGHT_READY",
                    "trade_date": trade_date, "publication_id": publication_id,
                    "manifest_sha256": report.get("manifest_sha256"),
                    "automatic_apply_enabled": False,
                    "technical_identity": identity}
        if mode == "--apply" and result.returncode != 0:
            return {"contract_id": CONTRACT_ID, "status": "DEGRADED",
                    "reason": str(report.get("reason") or report.get("outcome_error") or "FOCUS_APPLY_FAILED"),
                    "core_status": str(report.get("core_status") or "UNKNOWN"),
                    "apply": report, "technical_identity": identity}
    applied = reports["--apply"]
    if applied.get("core_status") != "ACTIVATED":
        return {"contract_id": CONTRACT_ID, "status": "FAILED",
                "reason": "FOCUS_CORE_NOT_ACTIVATED", "core_status": applied.get("core_status"),
                "technical_identity": identity}
    outcome_status = applied.get("outcome_status")
    return {"contract_id": CONTRACT_ID,
            "status": "READY" if outcome_status in {"READY", "NO_DUE_OUTCOMES"}
            and identity.get("status") == "ACCEPTED" else "DEGRADED",
            "trade_date": trade_date, "publication_id": publication_id,
            "core_status": applied["core_status"],
            "outcome_status": outcome_status,
            "manifest_sha256": reports["--preflight"].get("manifest_sha256"),
            "technical_identity": identity}
