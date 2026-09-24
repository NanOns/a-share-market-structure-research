"""FOCUS_OUTCOME_SETTLEMENT_TXN_V1 immutable outcome revisions and heads."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Mapping, Sequence

from psycopg import sql
from psycopg.types.json import Jsonb

from .contracts import FocusKey, SOURCE_AUTHORITY_CONTRACT, digest
from .outcomes import (CONTRACT_ID as OUTCOME_CONTRACT, TERMINAL,
                       classify_outcome, followup_complete)
from .outcome_math import (OutcomePathMetrics, sector_outcome_path,
                           stock_outcome_path)
from .materialize import VerifiedNormalizedSlice
from .price_path import due_date
from .sector_basket import SectorBasket


CONTRACT_ID = "FOCUS_OUTCOME_SETTLEMENT_TXN_V1"
REQUIRED_ANCHORS = frozenset({"FIRST_FOCUS", "CURRENT_UPGRADE", "EXIT_EFFECTIVE",
                              "INVALIDATION", "FIRST_SUPPORTED"})
HORIZONS = (1, 3, 5, 10, 20)
_SHA = re.compile(r"^[0-9a-f]{64}$")
_METRIC_QUANTUM = Decimal("0.000000000001")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        if not (value == value and abs(value) != float("inf")):
            raise ValueError("non-finite JSON evidence number")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ValueError("unsupported JSON evidence value: " + type(value).__name__)


@dataclass(frozen=True)
class DueAnchor:
    anchor_id: str
    episode_id: str
    source_family: str
    selection_contract_family: str
    entity_type: str
    entity_id: str
    anchor_type: str
    anchor_date: date
    horizon: int
    target_date: date
    price_basis: str
    reference_price: Decimal | None
    anchor_fact_digest: str
    evaluation_basis: str
    current_revision: int | None
    current_status: str | None
    current_evidence: Mapping[str, Any] | None
    source_revised: bool = False


@dataclass(frozen=True)
class OutcomeRecord:
    anchor_id: str
    horizon: int
    target_trade_date: date
    status: str
    evaluation_basis: str
    forward_return: Decimal | None
    mfe: Decimal | None
    mae: Decimal | None
    mdd: Decimal | None
    input_digest: str
    reason_codes: tuple[str, ...]
    evidence: Mapping[str, Any]

    def validate(self) -> None:
        if self.horizon not in HORIZONS or self.status not in {
            "PENDING", "OBSERVED", "DATA_GAP", "SUSPENDED", "DELISTED", "SOURCE_REVISED"
        }:
            raise ValueError("invalid outcome horizon or status")
        if self.evaluation_basis not in {"REAL_FORWARD", "HISTORICAL_RECONSTRUCTED"}:
            raise ValueError("invalid outcome evaluation basis")
        if not _SHA.fullmatch(self.input_digest):
            raise ValueError("invalid outcome input digest")
        if not self.reason_codes or any(not str(code) for code in self.reason_codes):
            raise ValueError("outcome reason codes required")
        if not isinstance(self.evidence, Mapping):
            raise ValueError("outcome evidence required")
        metrics = (self.forward_return, self.mfe, self.mae, self.mdd)
        if self.status != "OBSERVED" and any(value is not None for value in metrics):
            raise ValueError("non-observed outcome metrics must be NULL")
        if self.status == "OBSERVED":
            if self.forward_return is None or self.mdd is None:
                raise ValueError("observed outcome requires return and MDD")
            if self.evidence.get("target_data_state") != "BAR" or not self.evidence.get("path_complete"):
                raise ValueError("observed outcome requires complete actual BAR path")
            if not self.evidence.get("target_input_accepted") or not self.evidence.get("target_input_sealed"):
                raise ValueError("observed outcome requires accepted sealed target input")
        if self.status in TERMINAL and (
                not self.evidence.get("target_input_accepted") or
                not self.evidence.get("target_input_sealed")):
            raise ValueError("terminal outcome requires accepted sealed target input")
        if self.status == "DATA_GAP" and not _SHA.fullmatch(
                str(self.evidence.get("gap_audit_digest", ""))):
            raise ValueError("terminal DATA_GAP requires an audit digest")
        if self.status == "SUSPENDED" and not _SHA.fullmatch(
                str(self.evidence.get("suspension_audit_digest", ""))):
            raise ValueError("SUSPENDED requires an audit digest")
        if self.status == "DELISTED" and not _SHA.fullmatch(
                str(self.evidence.get("delisting_audit_digest", ""))):
            raise ValueError("DELISTED requires an audit digest")
        if self.status == "SOURCE_REVISED":
            old_digest = str(self.evidence.get("old_target_source_digest", ""))
            new_digest = str(self.evidence.get("new_target_source_digest", ""))
            if not _SHA.fullmatch(old_digest) or not _SHA.fullmatch(new_digest) or old_digest == new_digest:
                raise ValueError("SOURCE_REVISED requires distinct old/new source digests")
        for value in metrics:
            if value is not None and (not isinstance(value, Decimal) or not value.is_finite()):
                raise ValueError("outcome metrics must be finite Decimal or NULL")
            if value is not None and value != value.quantize(_METRIC_QUANTUM,
                                                              rounding=ROUND_HALF_UP):
                raise ValueError("outcome metric exceeds persisted 12-digit scale")


@dataclass(frozen=True)
class TargetInputSeal:
    trade_date: date
    accepted: bool
    sealed: bool
    source_identity_digest: str
    seal_digest: str

    def validate(self) -> None:
        if not _SHA.fullmatch(self.source_identity_digest) or not _SHA.fullmatch(self.seal_digest):
            raise ValueError("target input seal requires source and seal digests")
        if self.sealed and not self.accepted:
            raise ValueError("unaccepted target input cannot be sealed")


def read_target_input_seals(repository, *, target_dates: set[date],
                            normalized_artifact_sha256: str,
                            evaluation_basis: str) -> dict[date, TargetInputSeal]:
    """Derive target seals from accepted publication heads and artifact catalog."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    if not _SHA.fullmatch(normalized_artifact_sha256):
        raise ValueError("normalized artifact SHA-256 required")
    if evaluation_basis not in {"REAL_FORWARD", "HISTORICAL_RECONSTRUCTED"}:
        raise ValueError("invalid target seal evaluation basis")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute("select artifact_id,sha256,availability,discovered_at "
                    "from workbench_meta.artifact_catalog where relative_path=%s "
                    "and sha256=%s and availability='AVAILABLE' "
                    "order by discovered_at desc limit 1",
                    ("data/normalized/adjusted_daily.parquet", normalized_artifact_sha256))
        artifact = cur.fetchone()
    artifact_sealed = artifact is not None and artifact[3] is not None
    result = {}
    for target_date in sorted(target_dates):
        with repository.connection.cursor() as cur:
            cur.execute(sql.SQL("select h.publication_id,p.status,p.source_identity_sha256 "
                                "from {}.publication_heads h join {}.publications p using(publication_id) "
                                "where h.trade_date=%s").format(schema, schema), (target_date,))
            publications = cur.fetchall()
        if len(publications) > 1:
            raise ValueError("ambiguous target publication head")
        if not publications:
            continue
        publication_id, status, source_sha = publications[0]
        if status != "SUCCESS":
            continue
        source_exact = bool(source_sha and _SHA.fullmatch(str(source_sha).strip()))
        identity_kind = "SOURCE_SHA256" if source_exact else "PUBLICATION_ID_ONLY"
        if evaluation_basis == "REAL_FORWARD" and not source_exact:
            source_exact = False
        source_identity_digest = (str(source_sha).strip() if source_exact else
                                  digest({"identity_kind": identity_kind,
                                          "publication_id": str(publication_id)}))
        accepted = True
        sealed = artifact_sealed and (source_exact or
                 evaluation_basis == "HISTORICAL_RECONSTRUCTED")
        seal_digest = digest({"contract_id": "FOCUS_TARGET_INPUT_SEAL_V1",
                              "target_date": target_date,
                              "publication_id": str(publication_id),
                              "publication_status": str(status),
                              "source_identity_kind": identity_kind,
                              "source_identity_digest": source_identity_digest,
                              "normalized_artifact_sha256": normalized_artifact_sha256,
                              "artifact_id": str(artifact[0]) if artifact else None,
                              "artifact_discovered_at": artifact[3] if artifact else None,
                              "sealed": sealed})
        result[target_date] = TargetInputSeal(target_date, accepted, sealed,
                                               source_identity_digest, seal_digest)
    return result


def record_target_data_audit(repository, *, entity_type: str, entity_id: str,
                             target_trade_date: date, audit_kind: str,
                             target_source_identity_digest: str,
                             normalized_artifact_sha256: str, audited_by: str,
                             evidence: Mapping[str, Any]) -> str:
    """Append reviewed suspension, delisting, or final gap evidence."""
    kinds = {"CONFIRMED_SUSPENSION", "CONFIRMED_DELISTING", "FINAL_DATA_GAP"}
    if entity_type not in {"STOCK", "SECTOR"} or audit_kind not in kinds or not entity_id:
        raise ValueError("invalid audited target-state identity")
    if not _SHA.fullmatch(target_source_identity_digest) or not _SHA.fullmatch(normalized_artifact_sha256):
        raise ValueError("audited target-state source/artifact digest required")
    if not audited_by.strip() or not isinstance(evidence, Mapping) or not evidence:
        raise ValueError("audited_by and nonempty evidence required")
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("select h.publication_id,p.status,p.source_identity_sha256 "
                            "from {}.publication_heads h join {}.publications p using(publication_id) "
                            "where h.trade_date=%s").format(schema, schema), (target_trade_date,))
        publications = cur.fetchall()
        cur.execute("select 1 from workbench_meta.artifact_catalog where relative_path=%s "
                    "and sha256=%s and availability='AVAILABLE' limit 1",
                    ("data/normalized/adjusted_daily.parquet", normalized_artifact_sha256))
        artifact_exists = cur.fetchone() is not None
    if len(publications) != 1 or publications[0][1] != "SUCCESS" or not artifact_exists:
        raise ValueError("target audit requires accepted publication and available artifact")
    publication_id, _, raw_source_sha = publications[0]
    exact_sha = bool(raw_source_sha and _SHA.fullmatch(str(raw_source_sha).strip()))
    expected_source_identity = (str(raw_source_sha).strip() if exact_sha else
                                digest({"identity_kind": "PUBLICATION_ID_ONLY",
                                        "publication_id": str(publication_id)}))
    if target_source_identity_digest != expected_source_identity:
        raise ValueError("target audit source identity is not the accepted target head")
    safe_evidence = _json_safe(evidence)
    evidence_digest = digest({"contract_id": "FOCUS_TARGET_DATA_AUDIT_V1",
                              "entity_type": entity_type, "entity_id": entity_id,
                              "target_trade_date": target_trade_date,
                              "audit_kind": audit_kind,
                              "target_source_identity_digest": target_source_identity_digest,
                              "normalized_artifact_sha256": normalized_artifact_sha256,
                              "audited_by": audited_by.strip(),
                              "evidence": safe_evidence})
    audit_id = "focus-target-audit-" + evidence_digest[:32]
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("insert into {}.focus_target_data_audits "
                            "(audit_id,entity_type,entity_id,target_trade_date,audit_kind,"
                            "target_source_identity_digest,normalized_artifact_sha256,"
                            "evidence_digest,audited_by,evidence) "
                            "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) "
                            "on conflict (entity_type,entity_id,target_trade_date,audit_kind,"
                            "target_source_identity_digest,normalized_artifact_sha256) do nothing")
                    .format(schema),
                    (audit_id, entity_type, entity_id, target_trade_date, audit_kind,
                     target_source_identity_digest, normalized_artifact_sha256,
                     evidence_digest, audited_by.strip(), Jsonb(safe_evidence)))
        cur.execute(sql.SQL("select audit_id,evidence_digest,audited_by,evidence "
                            "from {}.focus_target_data_audits where entity_type=%s "
                            "and entity_id=%s and target_trade_date=%s and audit_kind=%s "
                            "and target_source_identity_digest=%s and normalized_artifact_sha256=%s")
                    .format(schema),
                    (entity_type, entity_id, target_trade_date, audit_kind,
                     target_source_identity_digest, normalized_artifact_sha256))
        stored = cur.fetchone()
    if stored != (audit_id, evidence_digest, audited_by.strip(), safe_evidence):
        raise ValueError("immutable target audit evidence conflict")
    return audit_id


def read_target_data_audits(repository, *, due_anchors: Sequence[DueAnchor],
                            target_seals: Mapping[date, TargetInputSeal],
                            normalized_artifact_sha256: str) -> dict[tuple[str, str, date], dict[str, Any]]:
    """Load only audits bound to the exact target source and artifact identity."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    result: dict[tuple[str, str, date], dict[str, Any]] = {}
    for due in due_anchors:
        seal = target_seals.get(due.target_date)
        if seal is None or not seal.accepted or not seal.sealed:
            continue
        with repository.connection.cursor() as cur:
            cur.execute(sql.SQL("select audit_id,audit_kind,evidence_digest,audited_by,evidence "
                                "from {}.focus_target_data_audits where entity_type=%s "
                                "and entity_id=%s and target_trade_date=%s "
                                "and target_source_identity_digest=%s and normalized_artifact_sha256=%s")
                        .format(schema),
                        (due.entity_type, due.entity_id, due.target_date,
                         seal.source_identity_digest, normalized_artifact_sha256))
            rows = cur.fetchall()
        key = (due.entity_type, due.entity_id, due.target_date)
        audit = result.setdefault(key, {})
        for audit_id, kind, evidence_digest, audited_by, evidence in rows:
            field = {"CONFIRMED_SUSPENSION": "suspension_audit_digest",
                     "CONFIRMED_DELISTING": "delisting_audit_digest",
                     "FINAL_DATA_GAP": "gap_audit_digest"}.get(str(kind))
            if field is None or not _SHA.fullmatch(str(evidence_digest).strip()):
                raise ValueError("invalid target audit row")
            expected_digest = digest({"contract_id": "FOCUS_TARGET_DATA_AUDIT_V1",
                                     "entity_type": due.entity_type,
                                     "entity_id": due.entity_id,
                                     "target_trade_date": due.target_date,
                                     "audit_kind": str(kind),
                                     "target_source_identity_digest": seal.source_identity_digest,
                                     "normalized_artifact_sha256": normalized_artifact_sha256,
                                     "audited_by": str(audited_by),
                                     "evidence": evidence})
            if (str(evidence_digest).strip() != expected_digest or
                    str(audit_id) != "focus-target-audit-" + expected_digest[:32]):
                raise ValueError("target audit evidence digest mismatch")
            if field in audit:
                raise ValueError("ambiguous target audit row")
            audit[field] = str(evidence_digest).strip()
            audit[field + "_by"] = str(audited_by)
            audit[field + "_evidence"] = evidence
    return result


def materialize_due_outcomes(repository, *, calendar: Sequence[date],
                             as_of_trade_date: date,
                             normalized: VerifiedNormalizedSlice,
                             target_seals: Mapping[date, TargetInputSeal],
                             baskets_by_episode: Mapping[str, SectorBasket],
                             target_audits: Mapping[tuple[str, str, date], Mapping[str, Any]] | None = None,
                             force_revisions: set[tuple[str, int]] | None = None) -> tuple[OutcomeRecord, ...]:
    """Build all due records from a SHA-verified local normalized slice.

    Suspension, delisting, and irrecoverable-gap decisions require separate
    audited evidence keyed by entity type/id and the fixed target date.
    """
    if normalized.artifact_sha256 == "" or not _SHA.fullmatch(normalized.artifact_sha256):
        raise ValueError("verified normalized artifact identity required")
    if as_of_trade_date not in normalized.calendar:
        raise ValueError("normalized slice does not contain settlement session")
    audits = target_audits or {}
    due = due_anchor_plan(repository, calendar=calendar, as_of_date=as_of_trade_date,
                          force_revisions=force_revisions)
    records = []
    for anchor in due:
        seal = target_seals.get(anchor.target_date)
        if seal is None:
            accepted = sealed = False
            source_digest = seal_digest = None
        else:
            seal.validate()
            if seal.trade_date != anchor.target_date:
                raise ValueError("target seal date does not match fixed outcome target")
            accepted, sealed = seal.accepted, seal.sealed
            source_digest, seal_digest = seal.source_identity_digest, seal.seal_digest
        key = (anchor.entity_type, anchor.entity_id, anchor.target_date)
        audit = dict(audits.get(key, {}))
        if anchor.entity_type == "STOCK":
            path: OutcomePathMetrics = stock_outcome_path(
                normalized=normalized, security_id=anchor.entity_id,
                calendar=calendar, anchor_date=anchor.anchor_date,
                horizon=anchor.horizon)
        elif anchor.entity_type == "SECTOR":
            basket = baskets_by_episode.get(anchor.episode_id)
            if basket is None:
                raise ValueError("accepted entry basket missing for sector outcome")
            path = sector_outcome_path(normalized=normalized, basket=basket,
                                       calendar=calendar,
                                       anchor_date=anchor.anchor_date,
                                       horizon=anchor.horizon)
        else:
            raise ValueError("unknown outcome entity type")
        if path.target_trade_date != anchor.target_date:
            raise ValueError("price path target differs from due anchor plan")
        path_values = None
        if path.path_complete:
            path_values = {"forward_return": path.forward_return,
                           "mfe": path.mfe, "mae": path.mae, "mdd": path.mdd}
        evidence = {"target_trade_date": anchor.target_date.isoformat(),
                    "normalized_artifact_sha256": normalized.artifact_sha256,
                    "target_source_identity_digest": source_digest,
                    "target_seal_digest": seal_digest,
                    "path_input_digest": path.input_digest,
                    "path_quality_status": path.quality_status,
                    "coverage": path.coverage,
                    "basket_digest": (baskets_by_episode[anchor.episode_id].basket_digest
                                      if anchor.entity_type == "SECTOR" else None),
                    **audit}
        if (((anchor.anchor_id, anchor.horizon) in (force_revisions or set()) or
             anchor.source_revised) and
                anchor.current_evidence):
            old_digest = anchor.current_evidence.get("target_source_identity_digest")
            new_digest = source_digest
            if old_digest and new_digest and old_digest != new_digest:
                evidence["old_target_source_digest"] = old_digest
                evidence["new_target_source_digest"] = new_digest
            old_artifact = anchor.current_evidence.get("normalized_artifact_sha256")
            if (old_artifact and old_artifact != normalized.artifact_sha256):
                evidence["old_normalized_artifact_sha256"] = old_artifact
                evidence["new_normalized_artifact_sha256"] = normalized.artifact_sha256
            if ((old_digest and new_digest and old_digest != new_digest) or
                    (old_artifact and old_artifact != normalized.artifact_sha256)):
                evidence["revision_reason"] = "ACCEPTED_TARGET_INPUT_REVISED"
        records.append(build_outcome_record(
            due=anchor, calendar=calendar, as_of_date=as_of_trade_date,
            target_input_accepted=accepted, target_input_sealed=sealed,
            anchor_actual_bar=path.anchor_actual_bar,
            target_data_state=path.target_data_state,
            path_complete=path.path_complete,
            input_digest=path.input_digest, path_metrics=path_values,
            evidence=evidence,
            audited_suspension=bool(audit.get("suspension_audit_digest")),
            audited_delisting=bool(audit.get("delisting_audit_digest")),
            gap_audit_digest=audit.get("gap_audit_digest"),
            source_revised=False))
    return tuple(records)


def build_outcome_record(*, due: DueAnchor, calendar: Sequence[date],
                         as_of_date: date, target_input_accepted: bool,
                         target_input_sealed: bool, anchor_actual_bar: bool,
                         target_data_state: str | None, path_complete: bool,
                         input_digest: str, path_metrics: Mapping[str, Decimal] | None,
                         evidence: Mapping[str, Any], audited_suspension: bool = False,
                         audited_delisting: bool = False,
                         gap_audit_digest: str | None = None,
                         source_revised: bool = False) -> OutcomeRecord:
    if not _SHA.fullmatch(input_digest):
        raise ValueError("base settlement input digest required")
    decision = classify_outcome(
        calendar=calendar, anchor_date=due.anchor_date, horizon=due.horizon,
        as_of_date=as_of_date, target_input_accepted=target_input_accepted,
        target_input_sealed=target_input_sealed,
        anchor_actual_bar=anchor_actual_bar, target_data_state=target_data_state,
        audited_suspension=audited_suspension,
        audited_delisting=audited_delisting, gap_audit_digest=gap_audit_digest,
        path_complete=path_complete, source_revised=source_revised)
    payload = dict(evidence)
    payload.update({"contract_id": OUTCOME_CONTRACT,
                    "settlement_contract_id": CONTRACT_ID,
                    "target_trade_date": (decision.target_trade_date or due.target_date).isoformat(),
                    "target_data_state": target_data_state,
                    "target_input_accepted": target_input_accepted,
                    "target_input_sealed": target_input_sealed,
                    "anchor_actual_bar": anchor_actual_bar,
                    "path_complete": path_complete,
                    "gap_audit_digest": gap_audit_digest})
    payload = _json_safe(payload)
    metrics = path_metrics if decision.status == "OBSERVED" else None
    metric_values = ({key: value.quantize(_METRIC_QUANTUM, rounding=ROUND_HALF_UP)
                      for key, value in metrics.items()} if metrics else {})
    canonical_input_digest = digest({"contract_id": CONTRACT_ID,
                                     "base_input_digest": input_digest,
                                     "anchor_id": due.anchor_id,
                                     "horizon": due.horizon,
                                     "target_trade_date": decision.target_trade_date,
                                     "status": decision.status,
                                     "evidence": payload,
                                     "metrics": metric_values})
    result = OutcomeRecord(
        due.anchor_id, due.horizon, decision.target_trade_date or due.target_date,
        decision.status, due.evaluation_basis,
        metric_values.get("forward_return"), metric_values.get("mfe"),
        metric_values.get("mae"), metric_values.get("mdd"),
        canonical_input_digest, (decision.reason_code,), payload)
    result.validate()
    return result


def due_anchor_plan(repository, *, calendar: Sequence[date], as_of_date: date,
                    force_revisions: set[tuple[str, int]] | None = None) -> tuple[DueAnchor, ...]:
    """List exact due targets; an outcome head never moves a target date."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    if not calendar or list(calendar) != sorted(set(calendar)) or as_of_date not in calendar:
        raise ValueError("complete frozen calendar through as-of date required")
    forced = force_revisions or set()
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select a.anchor_id,a.episode_id,e.source_family,e.selection_contract_family,"
            "e.entity_type,e.entity_id,"
            "a.anchor_type,a.trade_date,a.price_basis,a.reference_price,a.source_fact_digest,"
            "r.evaluation_basis "
            "from {}.focus_episode_anchors a join {}.focus_episodes e using(episode_id) "
            "join {}.focus_runs r on r.focus_run_id=a.focus_run_id "
            "where a.anchor_type = any(%s) and a.trade_date<=%s "
            "order by a.trade_date,a.episode_id,a.anchor_id").format(
                schema, schema, schema),
            (sorted(REQUIRED_ANCHORS), as_of_date))
        anchors = cur.fetchall()
        cur.execute(sql.SQL("select h.anchor_id,h.horizon,h.accepted_target_revision,o.status,"
                            "o.evidence "
                            "from {}.focus_outcome_heads h join {}.focus_episode_outcomes o "
                            "on o.anchor_id=h.anchor_id and o.horizon=h.horizon "
                            "and o.target_revision=h.accepted_target_revision").format(schema, schema))
        current_heads = {(str(row[0]), int(row[1])): (int(row[2]), str(row[3]), row[4])
                         for row in cur.fetchall()}
    target_dates = {target for row in anchors for horizon in HORIZONS
                    if (target := due_date(calendar, row[7], horizon)) is not None
                    and target <= as_of_date}
    source_by_date: dict[date, str] = {}
    if target_dates:
        with repository.connection.cursor() as cur:
            cur.execute(sql.SQL("select h.trade_date,p.publication_id,p.status,"
                                "p.source_identity_sha256 from {}.publication_heads h "
                                "join {}.publications p using(publication_id) "
                                "where h.trade_date=any(%s)").format(schema, schema),
                        (list(target_dates),))
            for target_date, publication_id, status, source_sha in cur.fetchall():
                if status != "SUCCESS":
                    continue
                exact_sha = bool(source_sha and _SHA.fullmatch(str(source_sha).strip()))
                source_by_date[target_date] = (
                    str(source_sha).strip() if exact_sha else
                    digest({"identity_kind": "PUBLICATION_ID_ONLY",
                            "publication_id": str(publication_id)}))
    with repository.connection.cursor() as cur:
        cur.execute("select sha256 from workbench_meta.artifact_catalog "
                    "where relative_path=%s and availability='AVAILABLE' "
                    "order by discovered_at desc limit 1",
                    ("data/normalized/adjusted_daily.parquet",))
        artifact = cur.fetchone()
    current_artifact_sha = str(artifact[0]).strip() if artifact else None
    result = []
    for (anchor_id, episode_id, family, selection_family, entity_type, entity_id,
         anchor_type, anchor_date, price_basis, reference_price, anchor_digest, basis) in anchors:
        for horizon in HORIZONS:
            target = due_date(calendar, anchor_date, horizon)
            if target is None or target > as_of_date:
                continue
            key = (str(anchor_id), horizon)
            revision, status, current_evidence = current_heads.get(key, (None, None, None))
            stored_source = ((current_evidence or {}).get("target_source_identity_digest"))
            stored_artifact = ((current_evidence or {}).get("normalized_artifact_sha256"))
            source_revised = bool(
                status in TERMINAL and key not in forced and current_evidence and
                ((source_by_date.get(target) is not None and
                  stored_source != source_by_date.get(target)) or
                 (current_artifact_sha is not None and
                  stored_artifact != current_artifact_sha)))
            if status in TERMINAL and key not in forced and not source_revised:
                continue
            result.append(DueAnchor(str(anchor_id), str(episode_id), str(family),
                                    str(selection_family), str(entity_type),
                                    str(entity_id), str(anchor_type),
                                    anchor_date, horizon, target, str(price_basis),
                                    Decimal(reference_price) if reference_price is not None else None,
                                    str(anchor_digest).strip(), str(basis),
                                    int(revision) if revision is not None else None,
                                    str(status) if status else None,
                                    current_evidence, source_revised))
    identities = [(row.anchor_id, row.horizon) for row in result]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate due anchor/horizon")
    return tuple(result)


def _row_value(record: OutcomeRecord) -> tuple[Any, ...]:
    return (record.target_trade_date, record.status, record.evaluation_basis,
            record.forward_return, record.mfe, record.mae, record.mdd,
            record.input_digest, list(record.reason_codes),
            _json_safe(record.evidence))


def _insert_followup_event(repository, *, episode_id: str, event_type: str,
                           event_trade_date: date, focus_run_id: str,
                           settlement_batch_id: str, evidence: Mapping[str, Any],
                           reason_codes: Sequence[str]) -> None:
    schema = sql.Identifier(repository.schema)
    evidence_digest = digest({"contract_id": "FOCUS_FOLLOWUP_TERMINATION_V1",
                              "episode_id": episode_id, "event_type": event_type,
                              "event_trade_date": event_trade_date,
                              "focus_run_id": focus_run_id,
                              "settlement_batch_id": settlement_batch_id,
                              "evidence": evidence, "reason_codes": list(reason_codes)})
    event_id = "focus-followup-" + evidence_digest[:32]
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("insert into {}.focus_episode_followup_events "
                            "(event_id,episode_id,event_type,event_trade_date,focus_run_id,"
                            "settlement_batch_id,evidence_digest,reason_codes) "
                            "values (%s,%s,%s,%s,%s,%s,%s,%s::jsonb) "
                            "on conflict (episode_id,event_type,settlement_batch_id) do nothing")
                    .format(schema),
                    (event_id, episode_id, event_type, event_trade_date, focus_run_id,
                     settlement_batch_id, evidence_digest,
                     Jsonb(list(reason_codes))))
        cur.execute(sql.SQL("select event_id,evidence_digest from {}.focus_episode_followup_events "
                            "where episode_id=%s and event_type=%s and settlement_batch_id=%s")
                    .format(schema), (episode_id, event_type, settlement_batch_id))
        stored = cur.fetchone()
    if stored != (event_id, evidence_digest):
        raise ValueError("immutable follow-up event conflict")


def _latest_followup_event(repository, episode_id: str) -> str | None:
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("select event_type from {}.focus_episode_followup_events "
                            "where episode_id=%s order by event_trade_date desc,created_at_utc desc,event_id desc limit 1")
                    .format(schema), (episode_id,))
        row = cur.fetchone()
    return str(row[0]) if row else None


def persist_outcome_batch(repository, *, focus_run_id: str,
                          as_of_trade_date: date, evaluation_basis: str,
                          normalized_artifact_sha256: str,
                          calendar: Sequence[date],
                          outcomes: Sequence[OutcomeRecord],
                          force_revisions: set[tuple[str, int]] | None = None) -> dict[str, Any]:
    """Persist one accepted, sealed settlement batch atomically.

    Caller opens the transaction and owns commit/rollback. The batch must
    cover every currently due target returned by ``due_anchor_plan``.
    """
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    if evaluation_basis not in {"REAL_FORWARD", "HISTORICAL_RECONSTRUCTED"}:
        raise ValueError("invalid settlement basis")
    if not _SHA.fullmatch(normalized_artifact_sha256):
        raise ValueError("normalized artifact SHA-256 required")
    if not calendar or list(calendar) != sorted(set(calendar)) or as_of_trade_date not in calendar:
        raise ValueError("frozen calendar through settlement date required")
    for row in outcomes:
        row.validate()
        if row.evaluation_basis != evaluation_basis:
            raise ValueError("outcome basis differs from settlement batch")
        if row.target_trade_date != due_date(calendar, _anchor_date(repository, row.anchor_id), row.horizon):
            raise ValueError("outcome target date differs from frozen calendar")
        if row.target_trade_date > as_of_trade_date:
            raise ValueError("future outcome target cannot settle")
        if row.evidence.get("normalized_artifact_sha256") != normalized_artifact_sha256:
            raise ValueError("outcome artifact identity differs from settlement batch")
    keys = [(row.anchor_id, row.horizon) for row in outcomes]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate outcome candidate")
    schema = sql.Identifier(repository.schema)
    calendar_digest = digest(list(calendar))
    input_digest = digest({"contract_id": CONTRACT_ID, "focus_run_id": focus_run_id,
                           "as_of_trade_date": as_of_trade_date,
                           "evaluation_basis": evaluation_basis,
                           "calendar_digest": calendar_digest,
                           "normalized_artifact_sha256": normalized_artifact_sha256,
                           "outcomes": [(r.anchor_id, r.horizon, r.target_trade_date,
                                         r.status, r.input_digest) for r in outcomes]})
    batch_id = "focus-settlement-" + input_digest[:32]
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("select r.trade_date,r.evaluation_basis,r.source_identity_digest,"
                            "r.calendar_digest,h.accepted_focus_run_id,h.lineage_state "
                            "from {}.focus_runs r join {}.focus_trade_date_heads h "
                            "on h.trade_date=r.trade_date and h.accepted_focus_run_id=r.focus_run_id "
                            "where r.focus_run_id=%s and h.source_authority_contract_id=%s")
                    .format(schema, schema), (focus_run_id, SOURCE_AUTHORITY_CONTRACT))
        run = cur.fetchone()
        if (run is None or run[0] != as_of_trade_date or run[1] != evaluation_basis or
                run[4] != focus_run_id or run[5] != "VALID"):
            raise ValueError("settlement requires the exact valid accepted core run")
        if not run[2] or not run[3] or str(run[3]).strip() != calendar_digest:
            raise ValueError("accepted core run identity is incomplete")
        cur.execute(sql.SQL("select count(*) from {}.focus_trade_date_heads "
                            "where source_authority_contract_id=%s and lineage_state='REPLAY_REQUIRED' "
                            "and trade_date<=%s").format(schema),
                    (SOURCE_AUTHORITY_CONTRACT, as_of_trade_date))
        if int(cur.fetchone()[0]):
            raise ValueError("settlement blocked by pending core replay")
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("select settlement_batch_id,outcome_count,terminal_count "
                            "from {}.focus_outcome_settlement_batches "
                            "where focus_run_id=%s and input_digest=%s").format(schema),
                    (focus_run_id, input_digest))
        existing_batch = cur.fetchone()
    if existing_batch:
        expected_counts = (batch_id, len(outcomes), sum(row.status in TERMINAL for row in outcomes))
        if existing_batch != expected_counts:
            raise ValueError("idempotent settlement batch identity conflict")
        return {"settlement_batch_id": batch_id, "input_digest": input_digest,
                "outcome_count": len(outcomes),
                "terminal_count": expected_counts[2],
                "pending_count": len(outcomes)-expected_counts[2],
                "changed_episodes": 0, "idempotent": True}

    plan = due_anchor_plan(repository, calendar=calendar,
                           as_of_date=as_of_trade_date,
                           force_revisions=force_revisions)
    plan_by_key = {(item.anchor_id, item.horizon): item for item in plan}
    expected = set(plan_by_key)
    if set(keys) != expected:
        raise ValueError("settlement batch does not cover exact due anchor set")
    for row in outcomes:
        due = plan_by_key[(row.anchor_id, row.horizon)]
        if row.target_trade_date != due.target_date or row.evaluation_basis != due.evaluation_basis:
            raise ValueError("outcome target identity/basis differs from accepted anchor")
        if row.evidence.get("target_trade_date") != row.target_trade_date.isoformat():
            raise ValueError("outcome evidence target date mismatch")

    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("insert into {}.focus_outcome_settlement_batches "
                            "(settlement_batch_id,focus_run_id,as_of_trade_date,evaluation_basis,"
                            "source_identity_digest,calendar_digest,normalized_artifact_sha256,"
                            "input_digest,outcome_count,terminal_count) "
                            "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                            "on conflict (focus_run_id,input_digest) do nothing").format(schema),
                    (batch_id, focus_run_id, as_of_trade_date, evaluation_basis,
                     str(run[2]).strip(), calendar_digest, normalized_artifact_sha256,
                     input_digest, len(outcomes), sum(row.status in TERMINAL for row in outcomes)))
        cur.execute(sql.SQL("select settlement_batch_id from {}.focus_outcome_settlement_batches "
                            "where focus_run_id=%s and input_digest=%s").format(schema),
                    (focus_run_id, input_digest))
        stored_batch = cur.fetchone()
        if stored_batch is None or stored_batch[0] != batch_id:
            raise ValueError("settlement batch identity conflict")

    changed_episodes: set[str] = set()
    for record in sorted(outcomes, key=lambda item: (item.anchor_id, item.horizon)):
        record.validate()
        row_value = _row_value(record)
        with repository.connection.cursor() as cur:
            cur.execute(sql.SQL("select accepted_target_revision from {}.focus_outcome_heads "
                                "where anchor_id=%s and horizon=%s for update").format(schema),
                        (record.anchor_id, record.horizon))
            old_head = cur.fetchone()
            if old_head:
                old_revision = int(old_head[0])
                cur.execute(sql.SQL("select target_trade_date,status,evaluation_basis,forward_return,"
                                    "mfe,mae,mdd,input_digest,reason_codes,evidence "
                                    "from {}.focus_episode_outcomes where anchor_id=%s and horizon=%s "
                                    "and target_revision=%s").format(schema),
                            (record.anchor_id, record.horizon, old_revision))
                old_value = cur.fetchone()
                if old_value == row_value:
                    continue
                revision = old_revision + 1
            else:
                revision = 1
            cur.execute(sql.SQL("select episode_id from {}.focus_episode_anchors "
                                "where anchor_id=%s").format(schema), (record.anchor_id,))
            anchor = cur.fetchone()
            if anchor is None:
                raise ValueError("outcome anchor disappeared")
            episode_id = str(anchor[0])
            cur.execute(sql.SQL("insert into {}.focus_episode_outcomes "
                                "(anchor_id,horizon,target_revision,target_trade_date,status,"
                                "evaluation_basis,forward_return,mfe,mae,mdd,input_digest,reason_codes,evidence) "
                                "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)")
                        .format(schema),
                        (record.anchor_id, record.horizon, revision,
                         record.target_trade_date, record.status, record.evaluation_basis,
                         record.forward_return, record.mfe, record.mae, record.mdd,
                         record.input_digest, Jsonb(list(record.reason_codes)),
                              Jsonb(_json_safe(record.evidence))))
            cur.execute(sql.SQL("insert into {}.focus_outcome_heads "
                                "(anchor_id,horizon,accepted_target_revision,activated_at_utc) "
                                "values (%s,%s,%s,now()) on conflict (anchor_id,horizon) do update "
                                "set accepted_target_revision=excluded.accepted_target_revision,"
                                "activated_at_utc=excluded.activated_at_utc").format(schema),
                        (record.anchor_id, record.horizon, revision))
            changed_episodes.add(episode_id)

    for episode_id in sorted(changed_episodes):
        if _latest_followup_event(repository, episode_id) == "FOLLOW_UP_COMPLETED":
            _insert_followup_event(repository, episode_id=episode_id,
                                   event_type="SETTLEMENT_REOPENED",
                                   event_trade_date=as_of_trade_date,
                                   focus_run_id=focus_run_id,
                                   settlement_batch_id=batch_id,
                                   evidence={"changed_outcome_batch": input_digest},
                                   reason_codes=("ACCEPTED_OUTCOME_REVISION",))

    incomplete_count = sum(row.status not in TERMINAL for row in outcomes)
    _write_followup_completion(repository, episodes=changed_episodes,
                               as_of_trade_date=as_of_trade_date,
                               focus_run_id=focus_run_id,
                               settlement_batch_id=batch_id,
                               calendar=calendar)
    with repository.connection.cursor() as cur:
        task_status = "RETRY_PENDING" if incomplete_count else "COMPLETE"
        cur.execute(sql.SQL("insert into {}.focus_outcome_settlement_tasks "
                            "(focus_run_id,as_of_trade_date,status,attempt_count,last_error_code,"
                            "last_input_digest,next_retry_at_utc,updated_at_utc) "
                            "values (%s,%s,%s,1,null,%s,"
                            "case when %s='RETRY_PENDING' then now()+interval '15 minutes' else null end,now()) "
                            "on conflict (focus_run_id,as_of_trade_date) do update set "
                            "status=excluded.status,attempt_count=case "
                            "when {}.focus_outcome_settlement_tasks.status='RETRY_PENDING' "
                            "then {}.focus_outcome_settlement_tasks.attempt_count+1 else 1 end,"
                            "last_error_code=null,last_input_digest=excluded.last_input_digest,"
                            "next_retry_at_utc=case when excluded.status='RETRY_PENDING' then now()+case "
                            "when {}.focus_outcome_settlement_tasks.status='RETRY_PENDING' then "
                            "least(15*power(2,{}.focus_outcome_settlement_tasks.attempt_count),1440) "
                            "* interval '1 minute' else interval '15 minutes' end else null end,"
                            "updated_at_utc=now()").format(schema, schema, schema, schema, schema),
                    (focus_run_id, as_of_trade_date, task_status, input_digest, task_status))
        cur.execute(sql.SQL("update {}.focus_runs set outcome_settlement_status=%s "
                            "where focus_run_id=%s").format(schema),
                    ("DEGRADED" if incomplete_count else "COMPLETE", focus_run_id))
    return {"settlement_batch_id": batch_id, "input_digest": input_digest,
            "outcome_count": len(outcomes), "terminal_count": len(outcomes)-incomplete_count,
            "pending_count": incomplete_count, "changed_episodes": len(changed_episodes)}


def _anchor_date(repository, anchor_id: str) -> date:
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("select trade_date from {}.focus_episode_anchors "
                            "where anchor_id=%s").format(schema), (anchor_id,))
        row = cur.fetchone()
    if row is None:
        raise ValueError("unknown outcome anchor")
    return row[0]


def pending_followup_keys(repository, *, as_of_trade_date: date) -> set[FocusKey]:
    """Return exited episodes not yet completed or explicitly reopened."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select e.source_family,e.entity_type,e.entity_id,e.selection_contract_family "
            "from {}.focus_episodes e join lateral ("
            " select o.source_membership_state from {}.focus_episode_observations o "
            " join {}.focus_trade_date_heads h on h.accepted_focus_run_id=o.focus_run_id "
            " and h.trade_date=o.trade_date where o.episode_id=e.episode_id "
            " and o.evaluation_mode='AS_RECORDED' and h.lineage_state='VALID' "
            " and h.trade_date<=%s order by h.trade_date desc,o.source_revision desc limit 1"
            ") last_obs on true left join lateral ("
            " select event_type from {}.focus_episode_followup_events f "
            " where f.episode_id=e.episode_id and f.event_trade_date<=%s "
            " order by f.event_trade_date desc,f.created_at_utc desc,f.event_id desc limit 1"
            ") last_event on true where last_obs.source_membership_state='NONE' "
            " and coalesce(last_event.event_type,'')<>'FOLLOW_UP_COMPLETED' "
            "order by e.source_family,e.entity_type,e.entity_id")
                    .format(schema, schema, schema, schema),
                    (as_of_trade_date, as_of_trade_date))
        rows = cur.fetchall()
    return {FocusKey(str(family), str(entity_type), str(entity_id), str(selection))
            for family, entity_type, entity_id, selection in rows}


def due_outcome_keys(repository, *, calendar: Sequence[date],
                     as_of_trade_date: date) -> set[FocusKey]:
    """Return entity keys whose fixed target dates need settlement or retry."""
    return {FocusKey(item.source_family, item.entity_type, item.entity_id,
                     item.selection_contract_family)
            for item in due_anchor_plan(repository, calendar=calendar,
                                        as_of_date=as_of_trade_date)}


def pending_settlement_tasks(repository, *, limit: int = 100) -> tuple[dict[str, Any], ...]:
    """Fetch a bounded page of retry tasks whose backoff has elapsed."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    if not 1 <= limit <= 1000:
        raise ValueError("settlement retry page limit outside 1..1000")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("select t.focus_run_id,t.as_of_trade_date,t.attempt_count,"
                            "t.last_error_code,t.last_input_digest,t.next_retry_at_utc "
                            "from {}.focus_outcome_settlement_tasks t "
                            "join {}.focus_runs r using(focus_run_id) "
                            "join {}.focus_trade_date_heads h on h.trade_date=t.as_of_trade_date "
                            "and h.accepted_focus_run_id=t.focus_run_id "
                            "and h.source_authority_contract_id=%s and h.lineage_state='VALID' "
                            "where t.status='RETRY_PENDING' "
                            "and r.core_publication_status='ACTIVATED' "
                            "and t.next_retry_at_utc<=clock_timestamp() "
                            "order by t.next_retry_at_utc,t.as_of_trade_date,t.focus_run_id limit %s")
                    .format(schema, schema, schema),
                    (SOURCE_AUTHORITY_CONTRACT, limit))
        rows = cur.fetchall()
    return tuple({"focus_run_id": str(row[0]), "as_of_trade_date": row[1],
                  "attempt_count": int(row[2]), "last_error_code": row[3],
                  "last_input_digest": row[4], "next_retry_at_utc": row[5]}
                 for row in rows)


def record_settlement_failure(repository, *, focus_run_id: str,
                              as_of_trade_date: date, error_code: str,
                              input_digest: str | None = None) -> None:
    """Persist retry status separately after the settlement transaction rolls back."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    if not re.fullmatch(r"[A-Z0-9_]{3,80}", error_code):
        raise ValueError("settlement error code must be a safe stable token")
    if input_digest is not None and not _SHA.fullmatch(input_digest):
        raise ValueError("invalid failed settlement input digest")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("update {}.focus_runs r set outcome_settlement_status='DEGRADED' "
                            "from {}.focus_trade_date_heads h "
                            "where r.focus_run_id=%s and r.core_publication_status='ACTIVATED' "
                            "and h.trade_date=%s and h.accepted_focus_run_id=r.focus_run_id "
                            "and h.source_authority_contract_id=%s and h.lineage_state='VALID'")
                    .format(schema, schema),
                    (focus_run_id, as_of_trade_date, SOURCE_AUTHORITY_CONTRACT))
        if cur.rowcount != 1:
            raise ValueError("retry task requires an activated core run")
        cur.execute(sql.SQL("insert into {}.focus_outcome_settlement_tasks "
                            "(focus_run_id,as_of_trade_date,status,attempt_count,last_error_code,"
                            "last_input_digest,next_retry_at_utc,updated_at_utc) "
                            "values (%s,%s,'RETRY_PENDING',1,%s,%s,now()+interval '15 minutes',now()) "
                            "on conflict (focus_run_id,as_of_trade_date) do update set "
                            "status='RETRY_PENDING',attempt_count=case "
                            "when {}.focus_outcome_settlement_tasks.status='RETRY_PENDING' "
                            "then {}.focus_outcome_settlement_tasks.attempt_count+1 else 1 end,"
                            "last_error_code=excluded.last_error_code,"
                            "last_input_digest=excluded.last_input_digest,"
                            "next_retry_at_utc=now()+case "
                            "when {}.focus_outcome_settlement_tasks.status='RETRY_PENDING' then "
                            "least(15*power(2,{}.focus_outcome_settlement_tasks.attempt_count),1440) "
                            "* interval '1 minute' else interval '15 minutes' end,updated_at_utc=now()")
                    .format(schema, schema, schema, schema, schema),
                    (focus_run_id, as_of_trade_date, error_code, input_digest))


def settle_outcome_batch(repository, **kwargs: Any) -> dict[str, Any]:
    """Commit an outcome batch; record bounded retry state after any rollback."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    focus_run_id = str(kwargs["focus_run_id"])
    as_of_trade_date = kwargs["as_of_trade_date"]
    try:
        result = persist_outcome_batch(repository, **kwargs)
        repository.connection.commit()
        return result
    except Exception as exc:
        repository.connection.rollback()
        code = "OUTCOME_" + type(exc).__name__.upper()
        try:
            record_settlement_failure(repository, focus_run_id=focus_run_id,
                                      as_of_trade_date=as_of_trade_date,
                                      error_code=code)
            repository.connection.commit()
        except Exception:
            repository.connection.rollback()
            raise
        raise


def settle_due_outcomes(repository, *, focus_run_id: str,
                        as_of_trade_date: date, evaluation_basis: str,
                        normalized_artifact_sha256: str,
                        calendar: Sequence[date],
                        normalized: VerifiedNormalizedSlice,
                        baskets_by_episode: Mapping[str, SectorBasket],
                        force_revisions: set[tuple[str, int]] | None = None) -> dict[str, Any]:
    """Materialize from accepted PG target evidence and commit one settlement transaction."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    from psycopg.pq import TransactionStatus
    connection = repository.connection
    if connection.info.transaction_status != TransactionStatus.IDLE:
        raise RuntimeError("OUTCOME_SETTLEMENT_REQUIRES_CLEAN_CONNECTION")
    try:
        with connection.transaction():
            with connection.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))",
                            ("FOCUS_OUTCOME_SETTLEMENT_" + focus_run_id +
                             "_" + as_of_trade_date.isoformat(),))
                cur.execute(sql.SQL("select status,next_retry_at_utc "
                                    "from {}.focus_outcome_settlement_tasks "
                                    "where focus_run_id=%s and as_of_trade_date=%s "
                                    "for update").format(sql.Identifier(repository.schema)),
                            (focus_run_id, as_of_trade_date))
                retry_task = cur.fetchone()
                if (retry_task is not None and retry_task[0] == "RETRY_PENDING" and
                        retry_task[1] is not None):
                    cur.execute("select %s > clock_timestamp()", (retry_task[1],))
                    if bool(cur.fetchone()[0]):
                        return {"status": "RETRY_BACKOFF",
                                "next_retry_at_utc": retry_task[1].isoformat()}
                if (retry_task is not None and retry_task[0] == "COMPLETE" and
                        not force_revisions):
                    return {"status": "ALREADY_COMPLETE",
                            "focus_run_id": focus_run_id,
                            "as_of_trade_date": as_of_trade_date.isoformat()}
            due = due_anchor_plan(repository, calendar=calendar,
                                  as_of_date=as_of_trade_date,
                                  force_revisions=force_revisions)
            target_dates = {anchor.target_date for anchor in due}
            target_seals = read_target_input_seals(
                repository, target_dates=target_dates,
                normalized_artifact_sha256=normalized_artifact_sha256,
                evaluation_basis=evaluation_basis)
            target_audits = read_target_data_audits(
                repository, due_anchors=due, target_seals=target_seals,
                normalized_artifact_sha256=normalized_artifact_sha256)
            outcomes = materialize_due_outcomes(
                repository, calendar=calendar, as_of_trade_date=as_of_trade_date,
                normalized=normalized, target_seals=target_seals,
                baskets_by_episode=baskets_by_episode,
                target_audits=target_audits,
                force_revisions=force_revisions)
            return persist_outcome_batch(
                repository, focus_run_id=focus_run_id,
                as_of_trade_date=as_of_trade_date,
                evaluation_basis=evaluation_basis,
                normalized_artifact_sha256=normalized_artifact_sha256,
                calendar=calendar, outcomes=outcomes,
                force_revisions=force_revisions)
    except Exception as exc:
        if connection.info.transaction_status != TransactionStatus.IDLE:
            connection.rollback()
        try:
            record_settlement_failure(
                repository, focus_run_id=focus_run_id,
                as_of_trade_date=as_of_trade_date,
                error_code="OUTCOME_" + type(exc).__name__.upper())
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        raise


def _write_followup_completion(repository, *, episodes: Iterable[str],
                               as_of_trade_date: date, focus_run_id: str,
                               settlement_batch_id: str,
                               calendar: Sequence[date]) -> None:
    schema = sql.Identifier(repository.schema)
    for episode_id in sorted(set(episodes)):
        with repository.connection.cursor() as cur:
            cur.execute(sql.SQL("select o.source_membership_state,o.followup_state "
                                "from {}.focus_episode_observations o "
                                "join {}.focus_episodes e using(episode_id) "
                                "join {}.focus_trade_date_heads h on h.accepted_focus_run_id=o.focus_run_id "
                                "and h.trade_date=o.trade_date "
                                "where o.episode_id=%s and o.evaluation_mode='AS_RECORDED' "
                                "and h.lineage_state='VALID' and h.trade_date<=%s "
                                "order by h.trade_date desc,o.source_revision desc limit 1")
                        .format(schema, schema, schema), (episode_id, as_of_trade_date))
            observation = cur.fetchone()
            cur.execute(sql.SQL("select a.anchor_id,a.anchor_type,a.trade_date,hz.horizon,"
                                "h.accepted_target_revision,o.status,o.evidence "
                                "from {}.focus_episode_anchors a "
                                "cross join (values (1),(3),(5),(10),(20)) as hz(horizon) "
                                "left join {}.focus_outcome_heads h on h.anchor_id=a.anchor_id "
                                "and h.horizon=hz.horizon "
                                "left join {}.focus_episode_outcomes o on o.anchor_id=h.anchor_id "
                                "and o.horizon=h.horizon and o.target_revision=h.accepted_target_revision "
                                "where a.episode_id=%s and a.anchor_type=any(%s) "
                                "order by a.trade_date,a.anchor_id,h.horizon")
                        .format(schema, schema, schema),
                        (episode_id, sorted(REQUIRED_ANCHORS)))
            anchor_rows = cur.fetchall()
        if not observation or observation[0] != "NONE" or not anchor_rows:
            continue
        outcome_statuses: list[str] = []
        evidence_items = []
        required = True
        for anchor_id, anchor_type, anchor_date, horizon, revision, status, evidence in anchor_rows:
            if horizon is None or status is None:
                required = False
                break
            expected = due_date(calendar, anchor_date, int(horizon))
            if expected is None or expected > as_of_trade_date:
                required = False
                break
            if status not in TERMINAL:
                required = False
                break
            if status == "DATA_GAP" and not _SHA.fullmatch(
                    str((evidence or {}).get("gap_audit_digest", ""))):
                required = False
                break
            if status == "SUSPENDED" and not _SHA.fullmatch(
                    str((evidence or {}).get("suspension_audit_digest", ""))):
                required = False
                break
            if status == "DELISTED" and not _SHA.fullmatch(
                    str((evidence or {}).get("delisting_audit_digest", ""))):
                required = False
                break
            outcome_statuses.append(str(status))
            evidence_items.append((anchor_id, int(horizon), int(revision), status,
                                   str((evidence or {}).get("input_digest", ""))))
        if not required:
            continue
        if not followup_complete(source_membership_exited=True,
                                 outcome_statuses=outcome_statuses,
                                 pending_revision=False, unaudited_gap=False):
            continue
        _insert_followup_event(repository, episode_id=episode_id,
                               event_type="FOLLOW_UP_COMPLETED",
                               event_trade_date=as_of_trade_date,
                               focus_run_id=focus_run_id,
                               settlement_batch_id=settlement_batch_id,
                               evidence={"outcome_heads": evidence_items,
                                         "latest_observation_followup": observation[1]},
                               reason_codes=("ALL_REQUIRED_ANCHORS_TERMINAL",))
