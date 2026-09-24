"""Canonical FOCUS-03 daily input manifest, before any database write."""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Mapping, Sequence

from psycopg import sql

from .contracts import SOURCE_AUTHORITY_CONTRACT, canonical_bytes, digest
from .daily_plan import PlannedDay
from .materialize import StockFact
from .member_strength import SectorStrength
from .sector_basket import SectorBasket
from .source_reader import AcceptedSources
from .technical_facts import read_accepted_technical


CONTRACT_ID = "FOCUS_DAILY_INPUT_MANIFEST_V2"


@dataclass(frozen=True)
class AuthorityBindings:
    publication_source_identity: str
    publication_source_identity_kind: str
    publication_source_revision_id: int | None
    v3_snapshot_id: str | None
    v3_membership_snapshot_id: str | None
    v3_parameter_hash: str | None
    v3_3_snapshot_id: str | None
    v3_3_research_run_id: str | None
    relation_source_identity: str | None
    member_strength_snapshot_id: str | None
    member_strength_result_id: str | None
    member_strength_value_hash: str | None
    technical_snapshot_id: str | None = None
    technical_result_id: str | None = None
    technical_value_hash: str | None = None
    technical_fact_status: str = "UNAVAILABLE"
    technical_fact_reason: str | None = None


def read_authority_bindings(repository, *, sources: AcceptedSources,
                            strengths: Mapping[str, SectorStrength]) -> AuthorityBindings:
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select source_identity_sha256,source_revision_id from {}.publications "
            "where publication_id=%s and trade_date=%s and status='SUCCESS'").format(schema),
            (sources.publication_id, sources.trade_date))
        publication = cur.fetchone()
        if not publication:
            raise ValueError("publication source identity unavailable")
        v3 = None
        if sources.v3_run_id:
            cur.execute(sql.SQL(
                "select snapshot_id,membership_snapshot_id,parameter_hash "
                "from {}.research_runs where run_id=%s and publication_id=%s "
                "and trade_date=%s and status='COMPLETE'").format(schema),
                (sources.v3_run_id, sources.publication_id, sources.trade_date))
            v3 = cur.fetchone()
            if not v3:
                raise ValueError("V3 authority binding unavailable")
        bundle = None
        if sources.bundle_digest:
            cur.execute(sql.SQL(
                "select snapshot_id,research_run_id from {}.research_bundle_heads "
                "where trade_date=%s and publication_id=%s and bundle_digest=%s"
            ).format(schema),
                (sources.trade_date, sources.publication_id, sources.bundle_digest))
            bundle = cur.fetchone()
            if not bundle:
                raise ValueError("V3.3 authority binding unavailable")
        cur.execute(sql.SQL(
            "select source_scope,revision_no from {}.relation_publication_bindings "
            "where publication_id=%s").format(schema), (sources.publication_id,))
        relations = cur.fetchall()
    if len(relations) > 1:
        raise ValueError("ambiguous publication relation binding")
    strength_ids = {(item.source_snapshot_id, item.source_result_object_id,
                     item.source_value_hash) for item in strengths.values()}
    if len(strength_ids) > 1:
        raise ValueError("mixed member strength source identities")
    strength_id = next(iter(strength_ids)) if strength_ids else (None, None, None)
    relation_id = (f"{relations[0][0]}:{relations[0][1]}" if relations else None)
    with repository.connection.cursor() as cur:
        cur.execute("""select sha256 from workbench_meta.artifact_catalog
                       where relative_path=%s and availability='AVAILABLE'
                       order by discovered_at desc limit 1""",
                    ("data/normalized/adjusted_daily.parquet",))
        normalized_artifact = cur.fetchone()
    if normalized_artifact is None:
        raise ValueError("normalized artifact identity unavailable for technical binding")
    technical = None
    technical_reason = None
    try:
        technical = read_accepted_technical(
            repository, publication_id=sources.publication_id,
            trade_date=sources.trade_date,
            expected_normalized_sha256=str(normalized_artifact[0]))
    except ValueError as exc:
        # Preserve a degraded, auditable manifest while the independent
        # technical-result integrity issue is unresolved. No factor rows pass.
        technical_reason = str(exc)
    return AuthorityBindings(
        str(publication[0]) if publication[0] else sources.publication_id,
        "SOURCE_SHA256" if publication[0] else "PUBLICATION_ID_ONLY",
        int(publication[1]) if publication[1] is not None else None,
        str(v3[0]) if v3 else None,
        str(v3[1]) if v3 else None, str(v3[2]) if v3 else None,
        str(bundle[0]) if bundle else None, str(bundle[1]) if bundle else None,
        relation_id, *(str(value) if value is not None else None
                       for value in strength_id),
        technical.snapshot_id if technical else None,
        technical.result_object_id if technical else None,
        technical.value_hash if technical else None,
        "READY" if technical else "UNAVAILABLE", technical_reason)


@dataclass(frozen=True)
class DailyInputManifest:
    trade_date: date
    payload: dict[str, object]
    sha256: str
    release_gate_reasons: tuple[str, ...]


def build_manifest(*, sources: AcceptedSources, plan: PlannedDay,
                   bindings: AuthorityBindings, calendar: Sequence[date],
                   calendar_artifact_sha256: str,
                   normalized_sha256: str,
                   stock_facts: Sequence[StockFact],
                   baskets: Mapping[str, SectorBasket],
                   strengths: Mapping[str, SectorStrength],
                   state_contract_id: str, parameter_set_id: str,
                   implementation_digest: str, dependency_lock_hash: str,
                   evaluation_basis: str, calendar_scope: str,
                   dependency_lock_kind: str) -> DailyInputManifest:
    if plan.trade_date != sources.trade_date or not calendar or calendar[-1] != sources.trade_date:
        raise ValueError("manifest date/calendar mismatch")
    if list(calendar) != sorted(set(calendar)):
        raise ValueError("manifest calendar not strictly increasing")
    if evaluation_basis not in {"REAL_FORWARD", "HISTORICAL_RECONSTRUCTED"}:
        raise ValueError("invalid evaluation basis")
    if calendar_scope not in {"MASTER_COMPLETE", "RANGE_SLICE"}:
        raise ValueError("unknown calendar scope")
    if dependency_lock_kind not in {"VERSIONED_LOCK", "RUNTIME_FINGERPRINT"}:
        raise ValueError("unknown dependency lock kind")
    required_hashes = (calendar_artifact_sha256, normalized_sha256,
                       implementation_digest, dependency_lock_hash)
    if any(len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value)
           for value in required_hashes):
        raise ValueError("manifest source/implementation hash invalid")
    if not all((sources.publication_id, sources.source_identity_digest,
                bindings.publication_source_identity, state_contract_id,
                parameter_set_id)):
        raise ValueError("manifest authority identity incomplete")
    if sources.v3_run_id and not all((bindings.v3_snapshot_id,
                                      bindings.v3_membership_snapshot_id,
                                      bindings.v3_parameter_hash)):
        raise ValueError("V3 snapshot/parameter binding absent")
    if sources.bundle_digest and not all((bindings.v3_3_snapshot_id,
                                          bindings.v3_3_research_run_id)):
        raise ValueError("V3.3 bundle binding absent")
    sector_episodes = {item.episode_id: item for item in
                       (plan.episode_tracking or plan.decisions)
                       if item.key.entity_type == "SECTOR" and item.episode_id}
    if set(baskets) != set(sector_episodes) or set(strengths) != set(sector_episodes):
        raise ValueError("sector fact set differs from tracking plan")
    if any(baskets[episode].sector_id != decision.key.entity_id or
           strengths[episode].sector_id != decision.key.entity_id
           for episode, decision in sector_episodes.items()):
        raise ValueError("sector fact identity mismatch")
    expected_paths = {(request.security_id, request.start_trade_date)
                      for request in plan.stock_path_requests}
    actual_paths = {(fact.security_id, fact.start_trade_date) for fact in stock_facts}
    if expected_paths != actual_paths or len(actual_paths) != len(stock_facts):
        raise ValueError("stock fact set differs from tracking plan")
    by_family: dict[str, list[str]] = {family: [] for family in sources.capabilities}
    for row in sources.rows:
        by_family[row.key.source_family].append(row.source_item_digest)
    source_family_rows = {family: {"capability": sources.capabilities[family],
                                   "count": len(items),
                                   "digest": digest(items)}
                          for family, items in sorted(by_family.items())}
    release_gate_reasons = tuple(sorted(
        (["CALENDAR_RANGE_ONLY"] if calendar_scope != "MASTER_COMPLETE" else []) +
        (["DEPENDENCY_LOCK_RUNTIME_ONLY"]
         if dependency_lock_kind != "VERSIONED_LOCK" else []) +
        (["HISTORICAL_RECONSTRUCTED_INPUT"]
         if evaluation_basis != "REAL_FORWARD" else [])))
    payload: dict[str, object] = {
        "contract_id": CONTRACT_ID,
        "trade_date": sources.trade_date,
        "evaluation_basis": evaluation_basis,
        "source_authority_contract_id": SOURCE_AUTHORITY_CONTRACT,
        "publication_id": sources.publication_id,
        "source_identity_digest": sources.source_identity_digest,
        "v3_run_id": sources.v3_run_id,
        "v3_3_bundle_digest": sources.bundle_digest,
        "authority_bindings": bindings.__dict__,
        "publication_source_identity_quality": bindings.publication_source_identity_kind,
        "source_family_rows": source_family_rows,
        "tracking_plan_digest": plan.plan_digest,
        "calendar_start": calendar[0],
        "calendar_end": calendar[-1],
        "calendar_session_count": len(calendar),
        "calendar_digest": digest(list(calendar)),
        "calendar_artifact_sha256": calendar_artifact_sha256,
        "calendar_scope": calendar_scope,
        "normalized_artifact_sha256": normalized_sha256,
        "stock_facts": [(fact.security_id, fact.start_trade_date,
                         fact.quality_status, fact.input_digest)
                        for fact in sorted(stock_facts,
                                           key=lambda item: (item.security_id,
                                                             item.start_trade_date))],
        "entry_baskets": [(episode, baskets[episode].basket_digest)
                          for episode in sorted(baskets)],
        "member_strength": [(episode, strengths[episode].fact_digest)
                            for episode in sorted(strengths)],
        "state_contract_id": state_contract_id,
        "parameter_set_id": parameter_set_id,
        "implementation_digest": implementation_digest,
        "dependency_lock_hash": dependency_lock_hash,
        "dependency_lock_kind": dependency_lock_kind,
        "release_gate_reasons": release_gate_reasons,
    }
    return DailyInputManifest(sources.trade_date, payload, digest(payload),
                              release_gate_reasons)


def write_manifest(*, output_path: Path, manifest: DailyInputManifest) -> None:
    """Write once, outside TDX; same bytes are idempotent."""
    encoded = canonical_bytes(manifest.payload)
    if hashlib.sha256(encoded).hexdigest() != manifest.sha256:
        raise ValueError("manifest digest mismatch")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        if hashlib.sha256(output_path.read_bytes()).hexdigest() != manifest.sha256:
            raise ValueError("immutable manifest conflict")
        return
    fd, temporary = tempfile.mkstemp(prefix="." + output_path.name + ".", suffix=".tmp",
                                      dir=output_path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def require_release_ready(manifest: DailyInputManifest) -> None:
    if manifest.release_gate_reasons:
        raise ValueError("Focus input manifest release gates: " +
                         ",".join(manifest.release_gate_reasons))
