"""One repeatable-read PG identity for immutable current V4 authority facts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def current_accepted_authority_snapshot(root: str | Path) -> dict:
    """Read the accepted stage/Data/Owner tuple under one PG RR/RO snapshot."""
    from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
    from . import v4_native
    from .v4_forward_pg_r1 import ForwardFactStore

    with v4_native.connection("v4", read_only=True) as pg:
        with v4_native.bind_read_snapshot(pg):
            authority = CurrentStageAuthority(Path(root).resolve())
            identity = ForwardFactStore._database_identity(pg)
            bindings = authority.bindings()
            payload = {
                "contract_id": "V4_ACCEPTED_AUTHORITY_SNAPSHOT_R1",
                "database_identity": identity,
                "bindings": bindings,
                "stage": authority.stage,
                "current_head": authority.head_ref,
                "data_head": authority.data_ref,
                "calendar": authority.calendar_ref,
                "identity": authority.identity_ref,
                "membership": authority.membership_ref,
                "owner_heads": authority.owners,
            }
            trade_date = authority.data["accepted_trade_date"]
            namespace = authority.head.get("accepted_head_namespace")
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {"contract_id": payload["contract_id"], "sha256": hashlib.sha256(raw).hexdigest(),
            "database_identity": identity, "trade_date": trade_date,
            "namespace": namespace, "bindings": bindings}
