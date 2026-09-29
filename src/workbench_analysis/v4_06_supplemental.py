"""V4-06 append-only BaoStock supplemental enrichment and turnover context.

Core publication facts are inputs only. This module never creates or edits a
Core publication, and only BOUND_STRICT turnover observations can enter the
historical context calculation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

from workbench_analysis.baostock_supplemental import BaoStockClient, BaoStockError, NormalizedRow


CONTRACT_ID = "TURNOVER_CONTEXT_V1"
CONTRACT_VERSION = "1.0.0"
SOURCE_CONTRACT_ID = "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1"
PROVIDER = "BAOSTOCK"
BINDING_STATUSES = frozenset({
    "BOUND_STRICT", "BOUND_SOFT", "UNAVAILABLE", "STALE", "MISSING", "UNBOUND", "SOURCE_NOT_READY"
})
SESSION_STATES = frozenset({"BOUND_STRICT", "CONFIRMED_SUSPENSION", "UNKNOWN"})
WINDOWS = (5, 20, 60)
MAX_LOOKBACK = 250


class SupplementalError(ValueError):
    """Fail-closed supplemental contract or identity error."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _valid_sha(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def provider_code_from_local(source_security_key: str) -> str:
    """Apply the frozen market-prefix case map; never guess code changes."""
    value = str(source_security_key).strip()
    if "." not in value:
        raise SupplementalError("SECURITY_KEY_FORMAT_INVALID")
    market, number = value.split(".", 1)
    if market not in {"SH", "SZ"} or not number.isdigit():
        raise SupplementalError("SECURITY_KEY_NOT_SUPPORTED_BY_BAOSTOCK")
    return f"{market.lower()}.{number}"


def validate_identity_map(rows: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    """Build canonical security_id -> BaoStock code from exact accepted keys."""
    result: dict[str, str] = {}
    reverse: dict[str, str] = {}
    for row in rows:
        security_id = str(row.get("security_id", ""))
        source_key = str(row.get("source_security_key", ""))
        if not security_id or not source_key:
            raise SupplementalError("SECURITY_IDENTITY_MISSING")
        code = provider_code_from_local(source_key)
        if security_id in result and result[security_id] != code:
            raise SupplementalError("SECURITY_IDENTITY_CONFLICT")
        if code in reverse and reverse[code] != security_id:
            raise SupplementalError("PROVIDER_CODE_AMBIGUOUS")
        result[security_id] = code
        reverse[code] = security_id
    return result


def map_code_change(old_code: str, new_code: str, security_id: str,
                    accepted_code_change_map: Mapping[str, str]) -> str:
    """Resolve code changes only through an explicit, versioned identity map."""
    expected = accepted_code_change_map.get(old_code)
    if not security_id or expected != new_code:
        raise SupplementalError("CODE_CHANGE_IDENTITY_UNACCEPTED")
    return new_code


def _tolerance_values(contract: Mapping[str, Any] | None) -> tuple[dict[str, float] | None, bool]:
    if not contract:
        return None, False
    raw = contract.get("tolerances")
    if not isinstance(raw, Mapping) or set(raw) != {"close", "volume", "amount"}:
        return None, False
    values = {key: float(raw[key]) for key in raw}
    if any(not math.isfinite(value) or value < 0 for value in values.values()):
        raise SupplementalError("TOLERANCE_CONTRACT_INVALID")
    accepted = (
        contract.get("acceptance") == "INDEPENDENTLY_ACCEPTED"
        and bool(contract.get("contract_id"))
        and bool(contract.get("version"))
        and _valid_sha(str(contract.get("evidence_digest", "")))
        and bool(contract.get("accepted_by"))
        and bool(contract.get("accepted_at_utc"))
        and contract.get("source_contract_id") == SOURCE_CONTRACT_ID
        and contract.get("dataset_id") == "BAOSTOCK_TURNOVER_DAILY_V1"
        and isinstance(contract.get("denominator_semantics_acceptance"), Mapping)
        and contract["denominator_semantics_acceptance"].get("status") == "INDEPENDENTLY_ACCEPTED"
        and contract["denominator_semantics_acceptance"].get("basis") == "PROVIDER_DEFINED_CIRCULATING_SHARES"
        and _valid_sha(str(contract["denominator_semantics_acceptance"].get("evidence_digest", "")))
        and bool(contract["denominator_semantics_acceptance"].get("accepted_by"))
        and bool(contract["denominator_semantics_acceptance"].get("accepted_at_utc"))
    )
    return values, accepted


def evaluate_binding(local: Mapping[str, Any], source: NormalizedRow | None, *,
                     expected_provider_code: str, tolerance_contract: Mapping[str, Any] | None,
                     provider_error_code: str | None = None) -> tuple[str, tuple[str, ...]]:
    """Bind supplemental data without allowing it to override dated local facts."""
    if provider_error_code:
        if str(provider_error_code) in {"10001015", "10001007", "10004011"}:
            return "SOURCE_NOT_READY", ("PROVIDER_SOURCE_NOT_READY",)
        return "UNAVAILABLE", ("PROVIDER_REQUEST_FAILED",)
    if source is None:
        return "MISSING", ("SOURCE_ROW_MISSING",)
    if not expected_provider_code or source.query_code != expected_provider_code or source.source_code != expected_provider_code:
        return "UNBOUND", ("SECURITY_IDENTITY_MISMATCH",)
    try:
        target_day = str(local["trade_date"])
        target_date = (date.fromisoformat(target_day) if "-" in target_day
                       else datetime.strptime(target_day, "%Y%m%d").date())
    except (KeyError, ValueError, TypeError):
        return "UNBOUND", ("LOCAL_TRADE_DATE_INVALID",)
    source_date = date.fromisoformat(source.trade_date)
    if source_date < target_date:
        return "STALE", ("SOURCE_DATE_STALE",)
    if source_date > target_date:
        return "UNBOUND", ("SOURCE_DATE_AFTER_TARGET",)
    if local.get("security_id") in {None, ""}:
        return "UNBOUND", ("LOCAL_SECURITY_ID_MISSING",)
    if source.turn_fraction is None:
        return "MISSING", ("TURNOVER_FIELD_MISSING",)
    if source.volume_shares is None or source.amount_cny is None:
        return "UNBOUND", ("FINGERPRINT_FIELDS_MISSING",)
    try:
        pairs = {
            "close": (float(local["close"]), source.close_price_cny),
            "volume": (float(local["volume"]), float(source.volume_shares)),
            "amount": (float(local["amount"]), source.amount_cny),
        }
    except (KeyError, TypeError, ValueError):
        return "UNBOUND", ("LOCAL_FINGERPRINT_MISSING",)
    if any(not math.isfinite(left) or not math.isfinite(right) for left, right in pairs.values()):
        return "UNBOUND", ("FINGERPRINT_VALUE_INVALID",)
    tolerance, independently_accepted = _tolerance_values(tolerance_contract)
    if tolerance is None:
        return "UNBOUND", ("SOURCE_TOLERANCE_UNFROZEN",)
    if any(abs(left - right) > tolerance[key] for key, (left, right) in pairs.items()):
        return "UNBOUND", ("LOCAL_SOURCE_FINGERPRINT_CONFLICT",)
    status_matches = (str(local.get("tradestatus", "")) == source.tradestatus
                      and str(local.get("isST", "")) == source.is_st)
    if not status_matches:
        return "BOUND_SOFT", ("LOCAL_STATUS_CROSSCHECK_CONFLICT",)
    if not independently_accepted:
        return "BOUND_SOFT", ("TOLERANCE_NOT_INDEPENDENTLY_ACCEPTED",)
    return "BOUND_STRICT", ()


def _rate(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0 or number > 1:
        raise SupplementalError("TURNOVER_RATE_OUT_OF_RANGE")
    return number


def _midpoint_percentile(current: float, prior: list[float]) -> float | None:
    if not prior:
        return None
    return (sum(value < current for value in prior) + 0.5 * sum(value == current for value in prior)) / len(prior)


def compute_turnover_context(*, target_trade_date: str, target: Mapping[str, Any] | None,
                             prior_sessions: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Compute V4-06 per-security context from strict prior samples only.

    `prior_sessions` includes known market sessions, most recent first or in any
    order. Confirmed local suspensions may be skipped. The first unknown session
    stops the prior sequence and older rows cannot be used across the gap.
    """
    try:
        target_day = date.fromisoformat(target_trade_date)
    except ValueError as exc:
        raise SupplementalError("TARGET_TRADE_DATE_INVALID") from exc
    empty: dict[str, Any] = {
        "turnover_rate": None, "turnover_ma5": None, "turnover_median20": None,
        "turnover_ratio20": None, "turnover_pct5": None, "turnover_pct20": None,
        "turnover_pct60": None, "turnover_delta3": None,
        "turnover_state": "UNAVAILABLE", "turnover_context": "UNKNOWN",
        "quality_codes": [], "prior_sample_dates": {"5": [], "20": [], "60": []},
        "prior_strict_sample_count": 0, "lookback_market_session_count": 0,
    }
    if target is None:
        return {**empty, "quality_codes": ["TARGET_ROW_MISSING"]}
    status = str(target.get("binding_status", "UNBOUND"))
    if status not in BINDING_STATUSES:
        raise SupplementalError("BINDING_STATUS_INVALID")
    if status != "BOUND_STRICT":
        return {**empty, "turnover_state": status, "quality_codes": ["TARGET_NOT_BOUND_STRICT"]}
    if str(target.get("local_tradestatus", "1")) != "1":
        return {**empty, "turnover_state": "UNAVAILABLE", "quality_codes": ["TARGET_NOT_ACTUAL_TRADE"]}
    current = _rate(target.get("turnover_rate"))
    if current is None:
        return {**empty, "turnover_state": "MISSING", "quality_codes": ["TARGET_TURNOVER_MISSING"]}

    sessions = []
    seen_dates: set[str] = set()
    for item in prior_sessions:
        day = str(item.get("trade_date", ""))
        try:
            parsed = date.fromisoformat(day)
        except ValueError as exc:
            raise SupplementalError("PRIOR_SESSION_DATE_INVALID") from exc
        if parsed >= target_day:
            raise SupplementalError("TARGET_OR_FUTURE_SESSION_IN_PRIOR_BASELINE")
        if day in seen_dates:
            raise SupplementalError("DUPLICATE_PRIOR_SESSION")
        seen_dates.add(day)
        sessions.append((parsed, dict(item)))
    sessions.sort(key=lambda pair: pair[0], reverse=True)
    sessions = sessions[:MAX_LOOKBACK]
    actual: list[dict[str, Any]] = []
    gap_seen = False
    for _, item in sessions:
        state = str(item.get("session_state", "UNKNOWN"))
        if state not in SESSION_STATES:
            state = "UNKNOWN"
        if state == "CONFIRMED_SUSPENSION":
            continue
        if state == "UNKNOWN":
            gap_seen = True
            break
        if str(item.get("local_tradestatus", "1")) != "1":
            gap_seen = True
            break
        value = _rate(item.get("turnover_rate"))
        if value is None:
            gap_seen = True
            break
        actual.append({"trade_date": str(item["trade_date"]), "turnover_rate": value})
        if len(actual) >= 60:
            break

    result = {**empty, "turnover_rate": current, "prior_strict_sample_count": len(actual),
              "lookback_market_session_count": len(sessions)}
    sample_dates: dict[str, list[str]] = {}
    for window in WINDOWS:
        sample = actual[:window]
        sample_dates[str(window)] = [item["trade_date"] for item in sample]
        if len(sample) == window:
            rates = [item["turnover_rate"] for item in sample]
            result[f"turnover_pct{window}"] = _midpoint_percentile(current, rates)
            if window == 5:
                result["turnover_ma5"] = sum(rates) / window
            elif window == 20:
                ordered = sorted(rates)
                result["turnover_median20"] = (ordered[9] + ordered[10]) / 2
                denominator = result["turnover_median20"]
                result["turnover_ratio20"] = current / denominator if denominator > 0 else None
            elif window == 60:
                result["turnover_context"] = (
                    "HIGH" if result["turnover_pct20"] is not None and result["turnover_pct20"] >= 0.8
                    else "LOW" if result["turnover_pct20"] is not None and result["turnover_pct20"] <= 0.2
                    else "NORMAL" if result["turnover_pct20"] is not None
                    else "UNKNOWN"
                )
    result["prior_sample_dates"] = sample_dates
    result["turnover_delta3"] = current - actual[2]["turnover_rate"] if len(actual) >= 3 else None
    if len(actual) >= 60 and not gap_seen:
        result["turnover_state"] = "AVAILABLE"
    else:
        result["turnover_state"] = "DEGRADED"
        result["turnover_context"] = "UNKNOWN"
    codes = []
    if len(actual) < 60:
        codes.append("INSUFFICIENT_PRIOR_STRICT_HISTORY")
    if gap_seen:
        codes.append("UNKNOWN_MISSING_SESSION_STOPS_HISTORY")
    if result["turnover_median20"] is not None and result["turnover_median20"] <= 0:
        codes.append("NONPOSITIVE_RATIO_DENOMINATOR")
    if len(actual) < 3:
        codes.append("DELTA3_ENDPOINT_MISSING")
    result["quality_codes"] = codes
    return result


def _row_digest_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"created_at", "logical_digest"}}


@dataclass(frozen=True)
class SupplementalRow:
    publication_id: str
    security_id: str
    enrichment_revision: int
    provider: str
    trade_date: str
    query_identity: dict[str, str]
    turnover_rate: float | None
    turnover_state: str
    turnover_context: str
    supplemental_participation_context: dict[str, Any]
    provider_asof: str | None
    binding_quality: str
    quality_codes: tuple[str, ...]
    source_contract_id: str
    source_revision_id: str
    source_digest: str
    raw_source_value: str | None
    raw_source_unit: str | None
    created_at: str
    source_contract_version: str = "1.1.0"
    turnover_ma5: float | None = None
    turnover_median20: float | None = None
    turnover_ratio20: float | None = None
    turnover_pct5: float | None = None
    turnover_pct20: float | None = None
    turnover_pct60: float | None = None
    turnover_delta3: float | None = None

    def validate(self) -> None:
        if not self.publication_id or not self.security_id or self.enrichment_revision < 1:
            raise SupplementalError("ENRICHMENT_IDENTITY_INVALID")
        if self.provider != PROVIDER or self.binding_quality not in BINDING_STATUSES:
            raise SupplementalError("ENRICHMENT_CAPABILITY_INVALID")
        if self.source_contract_id != SOURCE_CONTRACT_ID or not _valid_sha(self.source_digest):
            raise SupplementalError("ENRICHMENT_PROVENANCE_INVALID")
        required_query_keys = {"provider_code", "frequency", "start_date", "end_date", "adjustflag"}
        if not isinstance(self.query_identity, Mapping) or set(self.query_identity) != required_query_keys:
            raise SupplementalError("ENRICHMENT_QUERY_IDENTITY_INVALID")
        query_code = str(self.query_identity["provider_code"])
        market, separator, number = query_code.partition(".")
        if (not separator or market not in {"sh", "sz"} or not number.isdigit()
                or query_code != query_code.lower() or self.query_identity["frequency"] != "d"
                or self.query_identity["adjustflag"] != "3"):
            raise SupplementalError("ENRICHMENT_QUERY_IDENTITY_INVALID")
        try:
            query_start = date.fromisoformat(self.query_identity["start_date"])
            query_end = date.fromisoformat(self.query_identity["end_date"])
            target_day = date.fromisoformat(self.trade_date)
        except (TypeError, ValueError) as exc:
            raise SupplementalError("ENRICHMENT_QUERY_IDENTITY_INVALID") from exc
        if query_start > target_day or query_end < target_day or query_start > query_end:
            raise SupplementalError("ENRICHMENT_QUERY_IDENTITY_RANGE_INVALID")
        if self.turnover_rate is not None:
            _rate(self.turnover_rate)
        for name in ("turnover_ma5", "turnover_median20", "turnover_ratio20", "turnover_delta3"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(float(value)):
                raise SupplementalError("TURNOVER_METRIC_NOT_FINITE")
        for name in ("turnover_pct5", "turnover_pct20", "turnover_pct60"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(float(value)) or not 0 <= float(value) <= 1):
                raise SupplementalError("TURNOVER_PERCENTILE_OUT_OF_RANGE")
        if self.binding_quality == "BOUND_SOFT" and self.turnover_context not in {"UNKNOWN", "DIAGNOSTIC_ONLY"}:
            raise SupplementalError("SOFT_BINDING_SEMANTIC_USE_FORBIDDEN")
        if self.binding_quality != "BOUND_STRICT" and self.turnover_context not in {"UNKNOWN", "DIAGNOSTIC_ONLY"}:
            raise SupplementalError("UNBOUND_SEMANTIC_USE_FORBIDDEN")


def make_manifest(*, publication_id: str, enrichment_revision: int, provider: str,
                  source_contract_id: str, field_map_version: str, parameter_digest: str,
                  observed_at: str, ingested_at: str, provider_asof: str | None,
                  rows: Iterable[SupplementalRow]) -> dict[str, Any]:
    values = list(rows)
    if not publication_id or enrichment_revision < 1 or provider != PROVIDER:
        raise SupplementalError("MANIFEST_IDENTITY_INVALID")
    if not _valid_sha(parameter_digest):
        raise SupplementalError("MANIFEST_PARAMETER_DIGEST_INVALID")
    if source_contract_id != SOURCE_CONTRACT_ID or not field_map_version:
        raise SupplementalError("MANIFEST_SOURCE_CONTRACT_INVALID")
    identities = [(row.security_id, row.provider) for row in values]
    if len(identities) != len(set(identities)):
        raise SupplementalError("DUPLICATE_ENRICHMENT_SECURITY_PROVIDER")
    for row in values:
        row.validate()
        if row.publication_id != publication_id or row.enrichment_revision != enrichment_revision or row.provider != provider:
            raise SupplementalError("MANIFEST_ROW_IDENTITY_MISMATCH")
    strict = sum(row.binding_quality == "BOUND_STRICT" for row in values)
    soft = sum(row.binding_quality == "BOUND_SOFT" for row in values)
    unavailable = sum(row.binding_quality in {"UNAVAILABLE", "STALE", "MISSING", "UNBOUND", "SOURCE_NOT_READY"}
                      for row in values)
    revision_set = sorted(row.source_revision_id for row in values)
    base = {
        "publication_id": publication_id, "enrichment_revision": enrichment_revision,
        "provider": provider, "source_contract_id": source_contract_id,
        "field_map_version": field_map_version, "parameter_digest": parameter_digest,
        "observed_at": observed_at, "ingested_at": ingested_at, "provider_asof": provider_asof,
        "security_count": len(values), "strict_bound_count": strict, "soft_bound_count": soft,
        "unavailable_count": unavailable,
        "source_revision_set_digest": hashlib.sha256("\n".join(revision_set).encode()).hexdigest(),
    }
    logical_rows = sorted((_row_digest_payload(asdict(row)) for row in values),
                          key=lambda row: (row["security_id"], row["provider"]))
    return {**base, "logical_digest": digest_json({"manifest": base, "rows": logical_rows})}


def build_supplemental_row(*, publication_id: str, security_id: str, enrichment_revision: int,
                           trade_date: str, query_identity: Mapping[str, str],
                           binding_quality: str, source: NormalizedRow | None,
                           source_revision_id: str, source_digest: str,
                           turnover_context: Mapping[str, Any] | None,
                           created_at: str, provider_asof: str | None = None,
                           binding_quality_codes: Iterable[str] = ()) -> SupplementalRow:
    """Create a persistable row while keeping soft/unbound rows diagnostic."""
    if binding_quality not in BINDING_STATUSES:
        raise SupplementalError("BINDING_STATUS_INVALID")
    strict = binding_quality == "BOUND_STRICT"
    if strict and source is None:
        raise SupplementalError("STRICT_BINDING_SOURCE_ROW_REQUIRED")
    if not isinstance(query_identity, Mapping):
        raise SupplementalError("ENRICHMENT_QUERY_IDENTITY_INVALID")
    if source is not None and (
            query_identity.get("provider_code") != source.query_code
            or source.trade_date != trade_date):
        raise SupplementalError("ENRICHMENT_QUERY_SOURCE_MISMATCH")
    if source is not None and source.source_digest != source_digest:
        raise SupplementalError("SUPPLEMENTAL_SOURCE_DIGEST_MISMATCH")
    metrics = dict(turnover_context or {}) if strict else {}
    current = source.turn_fraction if source is not None else None
    quality_codes = tuple(sorted(set(binding_quality_codes) | set(metrics.get("quality_codes", []))))
    context_value = str(metrics.get("turnover_context", "UNKNOWN")) if strict else "UNKNOWN"
    state_value = str(metrics.get("turnover_state", "AVAILABLE")) if strict else binding_quality
    participation = {
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "binding_quality": binding_quality, "turnover_context": context_value,
        "prior_strict_sample_count": int(metrics.get("prior_strict_sample_count", 0)),
        "prior_sample_dates": metrics.get("prior_sample_dates", {"5": [], "20": [], "60": []}),
        "quality_codes": list(quality_codes), "effect": "NONE",
    }
    row = SupplementalRow(
        publication_id=publication_id, security_id=security_id, enrichment_revision=enrichment_revision,
        provider=PROVIDER, trade_date=trade_date, query_identity=dict(query_identity),
        turnover_rate=current, turnover_state=state_value,
        turnover_context=context_value, supplemental_participation_context=participation,
        provider_asof=provider_asof, binding_quality=binding_quality, quality_codes=quality_codes,
        source_contract_id=SOURCE_CONTRACT_ID,
        source_revision_id=source_revision_id,
        source_digest=source_digest,
        raw_source_value=source.turn_source_value if source is not None else None,
        raw_source_unit=source.turn_source_unit if source is not None else None,
        created_at=created_at,
        turnover_ma5=metrics.get("turnover_ma5"),
        turnover_median20=metrics.get("turnover_median20"),
        turnover_ratio20=metrics.get("turnover_ratio20"),
        turnover_pct5=metrics.get("turnover_pct5"),
        turnover_pct20=metrics.get("turnover_pct20"),
        turnover_pct60=metrics.get("turnover_pct60"),
        turnover_delta3=metrics.get("turnover_delta3"),
    )
    row.validate()
    return row


class AppendOnlySupplementalStore:
    """Small deterministic store used by the isolated writer/revision tests."""

    def __init__(self) -> None:
        self.manifests: list[dict[str, Any]] = []
        self.rows: list[SupplementalRow] = []

    def append(self, manifest: Mapping[str, Any], rows: Iterable[SupplementalRow]) -> None:
        values = list(rows)
        identity = (manifest["publication_id"], int(manifest["enrichment_revision"]), manifest["provider"])
        if any((item["publication_id"], item["enrichment_revision"], item["provider"]) == identity
               for item in self.manifests):
            raise SupplementalError("SUPPLEMENTAL_REVISION_ALREADY_EXISTS")
        expected = make_manifest(
            publication_id=manifest["publication_id"], enrichment_revision=int(manifest["enrichment_revision"]),
            provider=manifest["provider"], source_contract_id=manifest["source_contract_id"],
            field_map_version=manifest["field_map_version"], parameter_digest=manifest["parameter_digest"],
            observed_at=manifest["observed_at"], ingested_at=manifest["ingested_at"],
            provider_asof=manifest.get("provider_asof"), rows=values,
        )
        if dict(manifest) != expected:
            raise SupplementalError("SUPPLEMENTAL_MANIFEST_DIGEST_MISMATCH")
        existing_keys = {(row.publication_id, row.enrichment_revision, row.security_id, row.provider) for row in self.rows}
        if any((row.publication_id, row.enrichment_revision, row.security_id, row.provider) in existing_keys for row in values):
            raise SupplementalError("SUPPLEMENTAL_ROW_IDENTITY_ALREADY_EXISTS")
        self.manifests.append(dict(manifest))
        self.rows.extend(values)

    def next_revision(self, publication_id: str, provider: str = PROVIDER) -> int:
        revisions = [int(item["enrichment_revision"]) for item in self.manifests
                     if item["publication_id"] == publication_id and item["provider"] == provider]
        return max(revisions, default=0) + 1


class PostgresSupplementalWriter:
    """Atomic append-only PostgreSQL writer for V4-06 sidecar revisions."""

    @staticmethod
    def next_revision(connection: Any, publication_id: str, provider: str = PROVIDER) -> int:
        row = connection.execute(
            "select coalesce(max(enrichment_revision),0)+1 from v4.supplemental_enrichment_manifests where publication_id=%s and provider=%s",
            (publication_id, provider),
        ).fetchone()
        return int(row[0])

    @staticmethod
    def append_revision(connection: Any, manifest: Mapping[str, Any], rows: Iterable[SupplementalRow]) -> None:
        from psycopg.types.json import Jsonb

        values = list(rows)
        expected = make_manifest(
            publication_id=manifest["publication_id"], enrichment_revision=int(manifest["enrichment_revision"]),
            provider=manifest["provider"], source_contract_id=manifest["source_contract_id"],
            field_map_version=manifest["field_map_version"], parameter_digest=manifest["parameter_digest"],
            observed_at=manifest["observed_at"], ingested_at=manifest["ingested_at"],
            provider_asof=manifest.get("provider_asof"), rows=values,
        )
        if dict(manifest) != expected:
            raise SupplementalError("SUPPLEMENTAL_MANIFEST_DIGEST_MISMATCH")
        publication = connection.execute(
            "select trade_date,status from v4.publications where publication_id=%s",
            (manifest["publication_id"],),
        ).fetchone()
        if publication is None or publication[1] != "ACCEPTED":
            raise SupplementalError("ACCEPTED_CORE_PUBLICATION_REQUIRED")
        if any(str(row.trade_date) != str(publication[0]) for row in values):
            raise SupplementalError("ENRICHMENT_TRADE_DATE_PUBLICATION_MISMATCH")
        with connection.transaction():
            connection.execute(
                """insert into v4.supplemental_enrichment_manifests(
                    publication_id,enrichment_revision,provider,source_contract_id,field_map_version,
                    parameter_digest,observed_at,ingested_at,provider_asof,security_count,strict_bound_count,
                    soft_bound_count,unavailable_count,source_revision_set_digest,logical_digest)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (manifest["publication_id"], manifest["enrichment_revision"], manifest["provider"],
                 manifest["source_contract_id"], manifest["field_map_version"], manifest["parameter_digest"],
                 manifest["observed_at"], manifest["ingested_at"], manifest.get("provider_asof"),
                 manifest["security_count"], manifest["strict_bound_count"], manifest["soft_bound_count"],
                 manifest["unavailable_count"], manifest["source_revision_set_digest"], manifest["logical_digest"]),
            )
            for row in values:
                row.validate()
                connection.execute(
                    """insert into v4.stock_profile_enrichments(
                        publication_id,security_id,enrichment_revision,provider,trade_date,query_identity,source_contract_id,
                        source_contract_version,field_map_version,raw_source_value,raw_source_unit,turnover_rate,
                        turnover_ma5,turnover_median20,turnover_ratio20,turnover_pct5,turnover_pct20,
                        turnover_pct60,turnover_delta3,turnover_state,turnover_context,
                        supplemental_participation_context,provider_asof,binding_quality,quality_codes,
                        source_revision_id,source_digest,created_at)
                       values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (row.publication_id, row.security_id, row.enrichment_revision, row.provider, row.trade_date,
                     Jsonb(row.query_identity), row.source_contract_id, row.source_contract_version, "BAOSTOCK_FIELD_MAP_V1.1",
                     row.raw_source_value, row.raw_source_unit, row.turnover_rate, row.turnover_ma5,
                     row.turnover_median20, row.turnover_ratio20, row.turnover_pct5, row.turnover_pct20,
                     row.turnover_pct60, row.turnover_delta3, row.turnover_state, row.turnover_context,
                     Jsonb(row.supplemental_participation_context), row.provider_asof, row.binding_quality,
                     Jsonb(list(row.quality_codes)), row.source_revision_id, row.source_digest, row.created_at),
                )


def core_component_digests(components: Mapping[str, Any]) -> dict[str, str]:
    required = ("core_fact_digest", "core_profile_digest", "core_eligibility_digest",
                "core_state_digest", "core_event_digest", "validation_enrollment_digest")
    missing = set(required) - set(components)
    if missing:
        raise SupplementalError("CORE_ISOLATION_COMPONENT_MISSING")
    result = {key: str(components[key]) for key in required}
    if any(not _valid_sha(value) for value in result.values()):
        raise SupplementalError("CORE_ISOLATION_DIGEST_INVALID")
    return result


def run_core_isolation_matrix(core_components: Mapping[str, Any], scenarios: Mapping[str, Any]) -> dict[str, Any]:
    """Prove sidecar presence/order never mutates the supplied Core digest vector."""
    baseline = core_component_digests(core_components)
    required_scenarios = {"A_NO_TURNOVER", "B_TURNOVER_PRE_CACHED", "C_TURNOVER_AFTER_ACCEPTANCE",
                          "D_PROVIDER_STATUS_CONFLICT"}
    if set(scenarios) != required_scenarios:
        raise SupplementalError("CORE_ISOLATION_SCENARIO_SET_INVALID")
    results = {}
    for name, scenario in sorted(scenarios.items()):
        envelope = attach_supplemental_sidecar(baseline, scenario)
        after = envelope["core_component_digests"]
        results[name] = {"before": baseline, "after": after, "unchanged": baseline == after,
                         "supplemental_scenario_digest": envelope["supplemental_digest"]}
    return {"checks": results, "all_core_components_identical": all(item["unchanged"] for item in results.values()),
            "core_component_digests": baseline, "core_dependency": "NONE"}


def attach_supplemental_sidecar(core_components: Mapping[str, Any], supplemental: Mapping[str, Any]) -> dict[str, Any]:
    """Create an enrichment envelope that has no write path to Core fields."""
    baseline = core_component_digests(core_components)
    forbidden = set(baseline)
    stack = [supplemental]
    while stack:
        value = stack.pop()
        if isinstance(value, Mapping):
            keys = set(str(key) for key in value)
            if keys & forbidden or any(key.startswith("core_") or key == "validation_enrollment_digest" for key in keys):
                raise SupplementalError("SUPPLEMENTAL_SCENARIO_ATTEMPTS_CORE_MUTATION")
            stack.extend(value.values())
        elif isinstance(value, (list, tuple)):
            stack.extend(value)
    return {"core_component_digests": baseline, "supplemental_digest": digest_json(supplemental),
            "enrichment_revision": supplemental.get("enrichment_revision")}


def atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    import os
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    except Exception:
        Path(name).unlink(missing_ok=True)
        raise


def source_failure_state(error_code: str | None, *, timed_out: bool = False) -> str:
    if timed_out:
        return "UNAVAILABLE"
    if error_code and str(error_code) in {"10001015", "10001007", "10004011"}:
        return "SOURCE_NOT_READY"
    return "UNAVAILABLE"


@dataclass(frozen=True)
class ScheduledRequest:
    priority: str
    security_id: str
    provider_code: str
    trade_date: str


PRIORITY_ORDER = {"P0_DAILY_INCREMENTAL": 0, "P1_MISSING_RECENT_WINDOW": 1,
                  "P2_HISTORICAL_BACKFILL": 2, "P3_MANUAL_DIAGNOSTIC": 3}


def order_requests(requests: Iterable[ScheduledRequest]) -> list[ScheduledRequest]:
    values = list(requests)
    if any(item.priority not in PRIORITY_ORDER for item in values):
        raise SupplementalError("REQUEST_PRIORITY_INVALID")
    return sorted(values, key=lambda item: (PRIORITY_ORDER[item.priority], item.trade_date,
                                            item.security_id, item.provider_code))


def enforce_priority_budget(*, priority: str, daily_total: int, estimated_request_cost: int,
                            soft_stop: int = 40_000, p0_reserved: int = 5_000,
                            hard_stop: int = 45_000) -> None:
    if priority not in PRIORITY_ORDER:
        raise SupplementalError("REQUEST_PRIORITY_INVALID")
    if daily_total < 0 or estimated_request_cost < 1:
        raise SupplementalError("REQUEST_BUDGET_INPUT_INVALID")
    limit = soft_stop if priority == "P0_DAILY_INCREMENTAL" else soft_stop - p0_reserved
    if daily_total + estimated_request_cost > limit:
        raise SupplementalError("PRIORITY_BUDGET_RESERVED_HEADROOM")
    if daily_total + estimated_request_cost > hard_stop:
        raise SupplementalError("REQUEST_HARD_STOP")


class BoundedHistoryWorker:
    """Serial P0-P3 worker with checkpointing, bounded retries, and a breaker.

    The SDK client owns request accounting, per-call timeouts, retry charging,
    and the single-session/process locks. Checkpoints contain row digests and
    counters only; provider row payloads remain in memory.
    """

    def __init__(self, client: BaoStockClient, *, checkpoint_path: Path,
                 max_job_seconds: int = 21_600, circuit_breaker_failures: int = 3,
                 p0_reserved_requests: int = 5_000):
        if max_job_seconds < 1 or circuit_breaker_failures < 1 or p0_reserved_requests < 0:
            raise SupplementalError("WORKER_BOUND_INVALID")
        self.client = client
        self.checkpoint_path = checkpoint_path
        self.max_job_seconds = min(max_job_seconds, 21_600)
        self.circuit_breaker_failures = circuit_breaker_failures
        self.p0_reserved_requests = p0_reserved_requests

    def _daily_total(self) -> int:
        payload = self.client.budget._load()
        day = self.client.budget._today_shanghai()
        return int(payload.get("by_shanghai_date", {}).get(day, {}).get("count", 0))

    def run(self, requests: Iterable[ScheduledRequest], *, start_date: str, end_date: str,
            job_id: str, on_rows: Any | None = None) -> dict[str, Any]:
        import time
        ordered = order_requests(requests)
        if not ordered or not job_id or start_date > end_date:
            raise SupplementalError("WORKER_INPUT_INVALID")
        request_identity = {
            "job_id": job_id, "source_contract_id": SOURCE_CONTRACT_ID,
            "factor_contract_id": CONTRACT_ID, "requests_digest": digest_json([asdict(item) for item in ordered]),
            "start_date": start_date, "end_date": end_date,
        }
        if self.checkpoint_path.exists():
            try:
                checkpoint = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise SupplementalError("CHECKPOINT_UNREADABLE_FAIL_CLOSED") from exc
            if checkpoint.get("request_identity") != request_identity:
                raise SupplementalError("CHECKPOINT_IDENTITY_MISMATCH")
        else:
            checkpoint = {"request_identity": request_identity, "completed": {}, "failures": {}}
        completed = checkpoint.setdefault("completed", {})
        failures = checkpoint.setdefault("failures", {})
        started = time.monotonic()
        consecutive_failures = 0
        for item in ordered:
            key = f"{item.security_id}|{item.trade_date}|{item.provider_code}"
            if key in completed:
                continue
            if time.monotonic() - started >= self.max_job_seconds:
                checkpoint["status"] = "PAUSED_JOB_TIMEOUT"
                atomic_json_write(self.checkpoint_path, checkpoint)
                return checkpoint
            # Reserve the final 5,000 soft-stop requests for daily incremental
            # work. One call may retry once; login/logout are already in the
            # shared ledger and counted by BaoStockClient.
            try:
                enforce_priority_budget(
                    priority=item.priority, daily_total=self._daily_total(), estimated_request_cost=2,
                    p0_reserved=self.p0_reserved_requests,
                    hard_stop=self.client.budget.hard_limit,
                    soft_stop=self.client.budget.soft_limit,
                )
            except SupplementalError as exc:
                checkpoint["status"] = "PAUSED_BUDGET"
                checkpoint["pause_reason"] = str(exc)
                atomic_json_write(self.checkpoint_path, checkpoint)
                return checkpoint
            try:
                rows = self.client.query_daily(item.provider_code, start_date, end_date)
                if any(row.query_code != item.provider_code or row.source_code != item.provider_code
                       or not start_date <= row.trade_date <= end_date for row in rows):
                    raise BaoStockError("QUERY_RESPONSE_IDENTITY_OR_DATE_MISMATCH")
                source_digests = [row.source_digest for row in rows]
                if len(source_digests) != len(set(source_digests)):
                    raise BaoStockError("DUPLICATE_SOURCE_ROWS")
                summary = on_rows(item, rows) if on_rows else {}
                completed[key] = {
                    "source_row_count": len(rows),
                    "source_rows_digest": hashlib.sha256("\n".join(source_digests).encode("ascii")).hexdigest(),
                    "strict_bound_row_count": int((summary or {}).get("strict_bound_row_count", 0)),
                    "target_row_status": (summary or {}).get("target_row_status"),
                }
                failures.pop(key, None)
                consecutive_failures = 0
                checkpoint["status"] = "RUNNING"
                atomic_json_write(self.checkpoint_path, checkpoint)
            except Exception as exc:
                reason = str(exc) if isinstance(exc, (BaoStockError, SupplementalError)) else "BAOSTOCK_WORKER_FAILURE"
                code = getattr(exc, "provider_code", None)
                failures[key] = {"reason": reason, "provider_error_code": code}
                consecutive_failures += 1
                source_not_ready = code in {"10001015", "10001007", "10004011"}
                checkpoint["status"] = "CIRCUIT_OPEN" if source_not_ready or consecutive_failures >= self.circuit_breaker_failures else "BLOCKED_WITH_CHECKPOINT"
                atomic_json_write(self.checkpoint_path, checkpoint)
                if checkpoint["status"] == "CIRCUIT_OPEN":
                    checkpoint["circuit_breaker_reason"] = "PROVIDER_NOT_READY" if source_not_ready else "CONSECUTIVE_FAILURE_LIMIT"
                    atomic_json_write(self.checkpoint_path, checkpoint)
                    return checkpoint
                # Keep successful earlier items and resume after correcting the
                # provider/runtime condition; a failed item is never marked done.
                return checkpoint
        checkpoint["status"] = "COMPLETE" if not failures else "BLOCKED_WITH_CHECKPOINT"
        atomic_json_write(self.checkpoint_path, checkpoint)
        return checkpoint
