"""Versioned, explainable sector semantic registry for M7A."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Iterable, Mapping

from sector.roles import sector_role as legacy_sector_role
from workbench_service.strength_association import EVENT_WORDS, EXCLUDED_ROLES, PRICE_WORDS, STATUS_WORDS


CONTRACT_ID = "workbench-semantic-v2.1"
NORMAL_ATTRIBUTE = "NORMAL_ATTRIBUTE"
PRICE_BEHAVIOR_TAG = "PRICE_BEHAVIOR_TAG"
EVENT_TAG = "EVENT_TAG"
STATUS_TAG = "STATUS_TAG"
UNKNOWN_TAG = "UNKNOWN_TAG"
KNOWN_BUCKETS = {NORMAL_ATTRIBUTE, PRICE_BEHAVIOR_TAG, EVENT_TAG, STATUS_TAG, UNKNOWN_TAG}
TYPE_TO_ROLE = {"INDUSTRY": "INDUSTRY", "THEME": "THEME", "STYLE": "STYLE"}


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _upper(value: object) -> str:
    return _text(value).upper()


def _type(value: object) -> str:
    value = _upper(value)
    return {"CONCEPT": "THEME", "INDUSTRY": "INDUSTRY", "THEME": "THEME", "STYLE": "STYLE"}.get(value, value)


def _keyword_hint(name: str) -> str | None:
    # This is only a review hint.  It never directly produces a final bucket.
    if any(word in name for word in PRICE_WORDS):
        return PRICE_BEHAVIOR_TAG
    if any(word in name for word in EVENT_WORDS):
        return EVENT_TAG
    if any(word in name for word in STATUS_WORDS):
        return STATUS_TAG
    return None


@dataclass(frozen=True)
class SemanticResolution:
    semantic_version: str
    sector_id: str
    bucket: str
    role: str
    is_attribute: bool
    is_market_tag: bool
    normal_rank_eligible: bool
    override: bool
    rule_id: str
    reason: str
    keyword_hint: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


class SemanticRegistry:
    """Resolve exact IDs first, then explicit fields, then conservative defaults."""

    def __init__(self, overrides: Mapping[str, Mapping[str, object]] | None = None, *, version: str = CONTRACT_ID):
        self.version = version
        self.overrides = {str(key): dict(value) for key, value in (overrides or {}).items()}

    def resolve(self, sector: Mapping[str, object]) -> SemanticResolution:
        sector_id = _text(sector.get("sector_id"))
        name = _text(sector.get("sector_name"))
        exact = self.overrides.get(sector_id)
        if exact is not None:
            bucket = _upper(exact.get("bucket") or exact.get("semantic_bucket"))
            role = _upper(exact.get("role") or sector.get("sector_role") or "STRUCTURAL_TAG")
            if bucket not in KNOWN_BUCKETS:
                raise ValueError(f"INVALID_SEMANTIC_BUCKET:{sector_id}")
            is_attribute = bucket == NORMAL_ATTRIBUTE
            return SemanticResolution(
                self.version,
                sector_id,
                bucket,
                role,
                is_attribute,
                not is_attribute,
                is_attribute and role not in EXCLUDED_ROLES and _upper(sector.get("sector_valid", True)) not in {"FALSE", "0"},
                True,
                _text(exact.get("rule_id")) or "EXACT_ID_OVERRIDE",
                _text(exact.get("reason")) or "EXACT_SECTOR_ID_OVERRIDE",
                _text(exact.get("keyword_hint")) or None,
            )

        explicit = _upper(sector.get("semantic_bucket"))
        if explicit and explicit not in KNOWN_BUCKETS:
            raise ValueError(f"INVALID_SEMANTIC_BUCKET:{sector_id}")
        sector_type = _type(sector.get("sector_type"))
        role = _upper(sector.get("sector_role"))
        if not role:
            legacy_type = {"THEME": "concept", "INDUSTRY": "industry", "STYLE": "style"}.get(sector_type, sector_type.lower())
            role = _upper(legacy_sector_role(legacy_type, name))
        hint = _keyword_hint(name)
        if explicit:
            bucket = explicit
            reason = "EXPLICIT_SEMANTIC_BUCKET"
            rule_id = "EXPLICIT_FIELD"
        elif hint:
            bucket = UNKNOWN_TAG
            reason = "KEYWORD_CANDIDATE_REQUIRES_ID_REVIEW"
            rule_id = "KEYWORD_REVIEW_HINT"
        elif sector_type in TYPE_TO_ROLE:
            bucket = NORMAL_ATTRIBUTE
            reason = "EXPLICIT_SECTOR_TYPE"
            rule_id = "SECTOR_TYPE_DEFAULT"
        else:
            bucket = UNKNOWN_TAG
            reason = "UNKNOWN_SECTOR_TYPE"
            rule_id = "UNKNOWN_DEFAULT"
        is_attribute = bucket == NORMAL_ATTRIBUTE
        return SemanticResolution(
            self.version,
            sector_id,
            bucket,
            role,
            is_attribute,
            not is_attribute,
            is_attribute and role not in EXCLUDED_ROLES and _upper(sector.get("sector_valid", True)) not in {"FALSE", "0"},
            False,
            rule_id,
            reason,
            hint,
        )


def resolve_semantics(
    sector: Mapping[str, object], overrides: Mapping[str, Mapping[str, object]] | None = None
) -> dict:
    return SemanticRegistry(overrides).resolve(sector).as_dict()


def attach_semantics(
    sector: Mapping[str, object], overrides: Mapping[str, Mapping[str, object]] | None = None
) -> dict:
    result = dict(sector)
    result.update(resolve_semantics(sector, overrides))
    return result


def resolve_semantic_records(
    sectors: Iterable[Mapping[str, object]],
    overrides: Mapping[str, Mapping[str, object]] | None = None,
) -> list[dict]:
    """Resolve a deterministic, de-duplicated semantic snapshot.

    A sector ID must not resolve to conflicting semantic records within one
    input snapshot.  This keeps the persisted registry authoritative for all
    downstream historical domains instead of allowing each adapter to infer a
    different bucket at query time.
    """
    resolved: dict[str, dict] = {}
    for sector in sectors:
        record = resolve_semantics(sector, overrides)
        sector_id = str(record["sector_id"])
        if not sector_id:
            raise ValueError("SEMANTIC_SECTOR_ID_REQUIRED")
        previous = resolved.get(sector_id)
        if previous is not None and previous != record:
            raise ValueError(f"SEMANTIC_SECTOR_CONFLICT:{sector_id}")
        resolved[sector_id] = record
    return [resolved[key] for key in sorted(resolved)]


def build_semantic_version_rows(
    sectors: Iterable[Mapping[str, object]],
    *,
    observed_at: datetime,
    source_id: str,
    valid_from: date | None = None,
    overrides: Mapping[str, Mapping[str, object]] | None = None,
) -> list[dict]:
    """Build rows for the M7A ``sector_semantic_versions`` table."""
    if not source_id:
        raise ValueError("SEMANTIC_SOURCE_ID_REQUIRED")
    rows = []
    for record in resolve_semantic_records(sectors, overrides):
        rows.append(
            {
                "version_id": record["semantic_version"],
                "sector_id": record["sector_id"],
                "bucket": record["bucket"],
                "rule_id": record["rule_id"],
                "reason": record["reason"],
                "valid_from": valid_from,
                "observed_at": observed_at,
                "override": bool(record["override"]),
                "source_id": source_id,
            }
        )
    return rows


def insert_semantic_version_rows(connection, rows: Iterable[Mapping[str, object]]) -> int:
    """Insert semantic rows idempotently without overwriting old versions."""
    inserted = 0
    for row in rows:
        key = [row["version_id"], row["sector_id"]]
        existing = connection.execute(
            """
            select version_id,sector_id,bucket,rule_id,reason,valid_from,
                   observed_at,override,source_id
              from sector_semantic_versions
             where version_id=? and sector_id=?
            """,
            key,
        ).fetchone()
        if existing:
            # ``valid_from`` describes the first date in the current
            # observation window; it is not a semantic rule change.  A daily
            # rebuild must be able to reuse the immutable semantic version
            # when the resolved rule, bucket, reason, override and source are
            # unchanged.  Actual rule/coverage changes still fail closed and
            # require a new version_id.
            expected = (
                row["version_id"], row["sector_id"], row["bucket"], row["rule_id"],
                row["reason"], bool(row["override"]), row["source_id"],
            )
            actual = (
                existing[0], existing[1], existing[2], existing[3], existing[4],
                bool(existing[7]), existing[8],
            )
            if actual != expected:
                raise ValueError(f"SEMANTIC_VERSION_IMMUTABLE_CONFLICT:{row['version_id']}:{row['sector_id']}")
            continue
        connection.execute(
            """
            insert into sector_semantic_versions
                (version_id,sector_id,bucket,rule_id,reason,valid_from,observed_at,override,source_id)
            values (?,?,?,?,?,?,?,?,?)
            """,
            [
                row["version_id"], row["sector_id"], row["bucket"], row["rule_id"],
                row["reason"], row["valid_from"], row["observed_at"],
                bool(row["override"]), row["source_id"],
            ],
        )
        inserted += 1
    return inserted
