"""Point-in-time RPS20 inputs from each accepted date's sealed TDX bundle."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping, Sequence

from psycopg import sql

from tdx.security_master import current_a_stock_ids, read_industry_assignments
from .contracts import SOURCE_AUTHORITY_CONTRACT, digest
from .materialize import VerifiedNormalizedSlice
from .publication_identity import accepted_source_identity
from workbench_input.pipeline import verify_source_bundle_membership_identity


CONTRACT_ID = "FOCUS_PIT_RPS20_HISTORY_V1"
PRICE_CONTRACT_ID = "TDX_NATIVE_QFQ_RET20_V1"
MIN_VALID_UNIVERSE = 100
WINDOW = 20
NORMAL_LOOKBACK = 20
NORMAL_MIN_COVERAGE = Decimal("0.75")
# Mirrors normalize.phase1's bounded 251-session adjusted history. The window
# includes the evaluation date and leaves room to establish 120 actual bars.
HISTORY_LOOKBACK_SESSIONS = 251


@dataclass(frozen=True)
class PITUniverse:
    trade_date: date
    publication_id: str
    source_bundle_id: str
    bundle_manifest_sha256: str
    package_sha256: str
    metadata_snapshot_id: str
    security_ids: frozenset[str]
    identity_binding: str


def read_accepted_pit_universes(repository, *, trade_dates: set[date],
                                project_root: Path) -> dict[date, PITUniverse]:
    """Load only membership snapshots bound to exact successful PG heads.

    The package and metadata hashes are rechecked locally. Legacy publications
    without a package SHA remain explicitly path-bound and are never silently
    represented as a native PostgreSQL SHA identity.
    """
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    if not trade_dates:
        return {}
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select h.trade_date,p.publication_id,p.status,p.source_identity_sha256,"
            "p.source_path,m.source_identity_sha256 "
            "from {}.publication_heads h join {}.publications p using(publication_id) "
            "left join {}.publication_source_identity_migrations m using(publication_id) "
            "where h.trade_date=any(%s) order by h.trade_date"
        ).format(schema, schema, schema), (sorted(trade_dates),))
        rows = cur.fetchall()
    by_date: dict[date, tuple] = {}
    for row in rows:
        if row[0] in by_date:
            raise ValueError("PIT_RPS_AMBIGUOUS_ACCEPTED_PUBLICATION")
        by_date[row[0]] = row
    result: dict[date, PITUniverse] = {}
    for day in sorted(trade_dates):
        row = by_date.get(day)
        if row is None or row[2] != "SUCCESS" or not row[4]:
            continue
        publication_id, source_sha, raw_path, migrated_sha = str(row[1]), row[3], str(row[4]), row[5]
        source_path = Path(raw_path)
        if not source_path.is_absolute():
            source_path = project_root / source_path
        source_path = source_path.resolve(strict=True)
        bundle_root = (project_root / "data/source_bundles").resolve(strict=True)
        if source_path.parent != bundle_root and bundle_root not in source_path.parents:
            raise ValueError("PIT_RPS_BUNDLE_PATH_OUTSIDE_PROJECT_CATALOG")
        bundle_path = source_path / "source_bundle.json"
        identity = verify_source_bundle_membership_identity(bundle_path)
        bundle_id = str(identity["source_bundle_id"])
        if source_path.name != bundle_id or date.fromisoformat(str(identity["target_trade_date"])) != day:
            raise ValueError("PIT_RPS_PUBLICATION_BUNDLE_BINDING_MISMATCH")
        expected_sha, identity_kind = accepted_source_identity(source_sha, migrated_sha)
        exact_pg = bool(expected_sha and expected_sha == identity["package_sha256"])
        if expected_sha and not exact_pg:
            raise ValueError("PIT_RPS_POSTGRES_PACKAGE_IDENTITY_MISMATCH")
        metadata_root = Path(identity["metadata_root"])
        cache = metadata_root / "T0002/hq_cache"
        assignments = read_industry_assignments(cache / "tdxhy.cfg")
        current = current_a_stock_ids(assignments)
        if not current:
            raise ValueError("PIT_RPS_EMPTY_ACCEPTED_UNIVERSE")
        result[day] = PITUniverse(
            day, publication_id, bundle_id, str(identity["manifest_sha256"]),
            str(identity["package_sha256"]),
            str(identity.get("metadata_snapshot_id") or ""),
            frozenset(current),
            "POSTGRES_PACKAGE_SHA256" if exact_pg and identity_kind == "SOURCE_SHA256" else
            "MIGRATED_PACKAGE_SHA256" if exact_pg else
            "ACCEPTED_PUBLICATION_PATH_REVERIFIED")
    return result


def _decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() else None


def _rank_percentiles(values: Mapping[str, Decimal]) -> dict[str, Decimal]:
    ordered = sorted((value, sid) for sid, value in values.items())
    count = len(ordered)
    result = {}
    index = 0
    while index < count:
        end = index + 1
        while end < count and ordered[end][0] == ordered[index][0]:
            end += 1
        average_one_based_rank = (Decimal(index + 1) + Decimal(end)) / Decimal(2)
        percentile = average_one_based_rank / Decimal(count)
        for _, sid in ordered[index:end]:
            result[sid] = percentile
        index = end
    return result


def calculate_pit_rps20_deltas(*, normalized: VerifiedNormalizedSlice,
                               universes: Mapping[date, PITUniverse],
                               evaluation_sessions: Sequence[date],
                               min_universe: int = MIN_VALID_UNIVERSE
                               ) -> tuple[dict[date, dict[str, str | None]], dict[str, object]]:
    """Compute same-date point-in-time RPS20 and its 3-session difference.

    Eligibility matches the sealed Phase 1 normal-universe rule at that date:
    accepted current membership, a current actual bar, 120 actual bars, and at
    least 75% actual bars over the last 20 master sessions. The percentile uses
    average tie rank divided by same-date finite-return N, matching M8 RPS.
    """
    calendar = normalized.calendar
    positions = {day: index for index, day in enumerate(calendar)}
    if not evaluation_sessions or tuple(evaluation_sessions) != tuple(sorted(set(evaluation_sessions))):
        raise ValueError("PIT_RPS_INVALID_EVALUATION_SESSIONS")
    needed = set()
    for day in evaluation_sessions:
        if day not in positions:
            raise ValueError("PIT_RPS_EVALUATION_DATE_OUTSIDE_VERIFIED_SLICE")
        index = positions[day]
        if index >= 3:
            needed.update((day, calendar[index - 3]))
    levels: dict[date, dict[str, Decimal]] = {}
    quality: dict[str, object] = {}
    for day in sorted(needed):
        universe = universes.get(day)
        if universe is None:
            quality[day.isoformat()] = {"status": "UNAVAILABLE", "reason": "PIT_UNIVERSE_SNAPSHOT_UNAVAILABLE"}
            continue
        position = positions[day]
        if position < WINDOW:
            quality[day.isoformat()] = {"status": "UNAVAILABLE", "reason": "INSUFFICIENT_RET20_HISTORY"}
            continue
        return_window = calendar[position - WINDOW:position + 1]
        normal_window = calendar[max(0, position - NORMAL_LOOKBACK + 1):position + 1]
        returns: dict[str, Decimal] = {}
        missing_expected = []
        for sid in sorted(universe.security_ids):
            rows = normalized.by_security.get(sid)
            if rows is None:
                missing_expected.append(sid)
                continue
            row_today = rows.get(day)
            actual_today = bool(row_today and row_today.get("has_actual_bar") is True)
            actual_recent = sum(bool(rows.get(session) and rows[session].get("has_actual_bar") is True)
                                for session in normal_window)
            if (not actual_today or actual_recent < int(len(normal_window) * NORMAL_MIN_COVERAGE)):
                continue
            actual_history = sum(bool(row and row.get("has_actual_bar") is True)
                                 for session, row in rows.items() if session <= day)
            if actual_history < 120:
                continue
            closes = []
            versions = set()
            for session in return_window:
                row = rows.get(session)
                if not row or row.get("has_actual_bar") is not True:
                    closes = []
                    break
                if not str(row.get("adjustment_status", "")).startswith("VERIFIED"):
                    closes = []
                    break
                raw_close = _decimal(row.get("raw_close"))
                multiplier = _decimal(row.get("qfq_mul"))
                offset = _decimal(row.get("qfq_add"))
                close = (raw_close * multiplier + offset
                         if raw_close is not None and multiplier is not None and offset is not None
                         else None)
                if close is None or close <= 0:
                    closes = []
                    break
                closes.append(close)
                versions.add(row.get("adjustment_version"))
            if len(closes) != WINDOW + 1 or len(versions) != 1:
                continue
            returns[sid] = closes[-1] / closes[0] - Decimal(1)
        if missing_expected:
            quality[day.isoformat()] = {
                "status": "UNAVAILABLE", "reason": "PIT_UNIVERSE_ARTIFACT_COVERAGE_GAP",
                "universe_members": len(universe.security_ids),
                "missing_security_count": len(missing_expected),
                "missing_security_samples": missing_expected[:20]}
            continue
        if len(returns) < min_universe:
            quality[day.isoformat()] = {
                "status": "UNAVAILABLE", "reason": "INSUFFICIENT_PIT_RPS20_UNIVERSE",
                "finite_return_count": len(returns), "minimum": min_universe}
            continue
        levels[day] = _rank_percentiles(returns)
        quality[day.isoformat()] = {
            "status": "READY", "finite_return_count": len(returns),
            "minimum": min_universe, "membership_count": len(universe.security_ids),
            "publication_id": universe.publication_id,
            "source_bundle_id": universe.source_bundle_id,
            "bundle_manifest_sha256": universe.bundle_manifest_sha256,
            "package_sha256": universe.package_sha256,
            "metadata_snapshot_id": universe.metadata_snapshot_id,
            "identity_binding": universe.identity_binding}
    deltas: dict[date, dict[str, str | None]] = {}
    delta_quality: dict[str, dict[str, object]] = {}
    for day in evaluation_sessions:
        index = positions[day]
        previous = calendar[index - 3] if index >= 3 else None
        current_levels, previous_levels = levels.get(day), levels.get(previous) if previous else None
        values = {}
        if current_levels is not None and previous_levels is not None:
            for sid in current_levels.keys() & previous_levels.keys():
                values[sid] = str(current_levels[sid] - previous_levels[sid])
        deltas[day] = values
        ready = current_levels is not None and previous_levels is not None
        delta_quality[day.isoformat()] = {
            "status": "READY" if ready else "UNAVAILABLE",
            "reason": None if ready else "PIT_RPS20_LEVEL_OR_T_MINUS_3_UNAVAILABLE",
            "prior_trade_date": previous.isoformat() if previous else None,
            "finite_delta_count": len(values)}
    provider_digest = digest({"contract_id": CONTRACT_ID,
                              "price_contract_id": PRICE_CONTRACT_ID,
                              "normalized_artifact_sha256": normalized.artifact_sha256,
                              "evaluation_sessions": list(evaluation_sessions),
                              "history_lookback_sessions": HISTORY_LOOKBACK_SESSIONS,
                              "rps_dates": quality,
                              "delta_quality": delta_quality,
                              "deltas": {day.isoformat(): values for day, values in deltas.items()}})
    return deltas, {"contract_id": CONTRACT_ID, "price_contract_id": PRICE_CONTRACT_ID,
                    "min_universe": min_universe, "rps_date_quality": quality,
                    "history_lookback_sessions": HISTORY_LOOKBACK_SESSIONS,
                    "delta_quality": delta_quality,
                    "provider_digest": provider_digest}
