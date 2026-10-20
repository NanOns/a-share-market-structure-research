"""Copy a configured TDX input tree into an immutable, project-managed snapshot."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import shutil
import struct
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


class LocalSnapshotError(ValueError):
    pass


LOCAL_NATIVE_DEV_CONTRACT_ID = "V4_TDX_LOCAL_NATIVE_SOURCE_V1"
LOCAL_NATIVE_DEV_CONTRACT_VERSION = "1.0.0"
LOCAL_NATIVE_DEV_FACT_KIND = "tdx_local_native_dev_candidate"
_DAY = struct.Struct("<IIIIIfII")
_DAY_RECORD_BYTES = 32
_DAY_PRICE_DIVISOR = 100.0
_BOARD_PREFIXES = {
    "SH_MAIN": ("SH", ("600", "601", "603", "605")),
    "SZ_MAIN": ("SZ", ("000", "001", "002", "003")),
    "CHINEXT": ("SZ", ("300", "301")),
    "STAR": ("SH", ("688", "689")),
}


def local_native_dev_contract_seed() -> dict[str, Any]:
    """开发期本地原生来源合同的唯一迁入字节；运行校验仍从PG读取。"""
    return {
        "contract_id": LOCAL_NATIVE_DEV_CONTRACT_ID,
        "contract_version": LOCAL_NATIVE_DEV_CONTRACT_VERSION,
        "owner": "V4-00D",
        "source_role": "TDX_LOCAL_NATIVE",
        "purpose": "STAGE00_DEVELOPMENT_VALIDATION_ONLY",
        "source_format": "TDX_DAY_BINARY_V1",
        "target_fields": {
            "open": "CNY/share", "high": "CNY/share", "low": "CNY/share",
            "close": "CNY/share", "amount": "CNY", "volume": "share",
        },
        "identity_source": "V4_PG_SECURITY_LIFECYCLE_HISTORY_CANDIDATE",
        "required_scope": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"],
        "required_provenance": [
            "T0", "source_file_sha256", "target_rows_sha256", "universe_sha256",
            "source_observed_at_utc", "pg_candidate_binding_sha256",
        ],
        "knowledge_clock": {
            "AS_RECORDED": False, "PIT_ELIGIBLE": False,
            "first_provider_available_at": "UNKNOWN_UNLESS_INDEPENDENTLY_PROVEN",
        },
        "authority": {
            "candidate_status": "DEV_VALIDATED",
            "formal_source_acceptance": False,
            "official_tdx_zip": False,
            "production_head_eligible": False,
        },
        "suspension_rule": "A listed T0 roster member without a TDX T0 bar requires same-date BaoStock tradestatus=0 evidence; preserve blank volume/amount.",
        "cross_source_rule": "BaoStock close/volume/amount is diagnostic only; exact differences do not replace TDX or block this development candidate.",
    }


def _local_board(market: str, code: str) -> str | None:
    normalized_market = market.upper()
    for board, (expected_market, prefixes) in _BOARD_PREFIXES.items():
        if normalized_market == expected_market and code.startswith(prefixes):
            return board
    return None


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _load_active_identity_candidates(pg: Any, target: str) -> dict[str, dict[str, Any]]:
    rows = pg.execute(
        """SELECT upper(symbol), security_id, security_type, list_date, delist_date,
                  quality, source_revision_id, system_available_at
             FROM v4.security_lifecycle_history
            WHERE symbol IS NOT NULL"""
    ).fetchall()
    grouped: dict[str, list[tuple[Any, ...]]] = {}
    for row in rows:
        grouped.setdefault(str(row[0]), []).append(row)
    output: dict[str, dict[str, Any]] = {}
    target_day = datetime.fromisoformat(target).date()
    for symbol, candidates in grouped.items():
        if "." not in symbol:
            continue
        market, code = symbol.split(".", 1)
        if not code.isdigit() or len(code) != 6 or _local_board(market, code) is None:
            continue
        active = [row for row in candidates if (
            row[2] == "A_STOCK" and row[3] is not None and row[3] <= target_day
            and (row[4] is None or row[4] >= target_day)
        )]
        security_ids = {str(row[1]).strip() for row in active if row[1]}
        if len(security_ids) != 1:
            continue
        active.sort(key=lambda row: (row[7] or datetime.min.replace(tzinfo=timezone.utc), str(row[6] or "")))
        chosen = active[-1]
        output[symbol] = {
            "source_security_key": symbol,
            "security_id": next(iter(security_ids)),
            "board_scope": _local_board(market, code),
            "identity_status": "PG_CANDIDATE_ONLY",
            "identity_quality": str(chosen[5] or "UNKNOWN"),
            "identity_source_revision_id": str(chosen[6] or ""),
            "identity_system_available_at": chosen[7].isoformat() if chosen[7] else None,
            "security_type": "A_STOCK",
            "listing_from": chosen[3].isoformat(),
            "listing_to": chosen[4].isoformat() if chosen[4] else None,
        }
    return output


def _read_native_target_file(path: Path, *, market: str, target_day: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    info_before = path.stat()
    raw = path.read_bytes()
    info_after = path.stat()
    if (info_before.st_size, info_before.st_mtime_ns) != (info_after.st_size, info_after.st_mtime_ns):
        raise LocalSnapshotError("TDX_SOURCE_CHANGED_DURING_READ")
    if not raw or len(raw) % _DAY_RECORD_BYTES:
        raise LocalSnapshotError("TDX_DAY_FILE_LENGTH_INVALID:" + path.name)
    file_sha = hashlib.sha256(raw).hexdigest()
    count = len(raw) // _DAY_RECORD_BYTES
    low, high = 0, count
    while low < high:
        middle = (low + high) // 2
        day = struct.unpack_from("<I", raw, middle * _DAY_RECORD_BYTES)[0]
        if day < target_day:
            low = middle + 1
        else:
            high = middle
    target_record = None
    if low < count:
        offset = low * _DAY_RECORD_BYTES
        record = _DAY.unpack_from(raw, offset)
        day, open_, high_, low_, close, amount, volume, _reserved = record
        try:
            datetime.strptime(str(day), "%Y%m%d")
        except ValueError as exc:
            raise LocalSnapshotError("TDX_DAY_DATE_INVALID:" + path.name) from exc
        previous_day = struct.unpack_from("<I", raw, max(0, low - 1) * _DAY_RECORD_BYTES)[0] if low else 0
        next_day = struct.unpack_from("<I", raw, (low + 1) * _DAY_RECORD_BYTES)[0] if low + 1 < count else 0
        if (day < previous_day) or (next_day and next_day <= day):
            raise LocalSnapshotError("TDX_DAY_DATE_ORDER_INVALID:" + path.name)
        if day == target_day:
            if not (open_ == high_ == low_ == close == 0) and (
                high_ < max(open_, low_, close) or low_ > min(open_, high_, close)
            ):
                raise LocalSnapshotError("TDX_DAY_OHLC_INVALID:" + path.name)
            if amount < 0 or volume < 0:
                raise LocalSnapshotError("TDX_DAY_AMOUNT_OR_VOLUME_INVALID:" + path.name)
            target_record = {
                "open": open_ / _DAY_PRICE_DIVISOR,
                "high": high_ / _DAY_PRICE_DIVISOR,
                "low": low_ / _DAY_PRICE_DIVISOR,
                "close": close / _DAY_PRICE_DIVISOR,
                "amount": float(amount),
                "volume": int(volume),
            }
    last_trade_date = struct.unpack_from("<I", raw, (count - 1) * _DAY_RECORD_BYTES)[0]
    if target_record is None:
        return None, {"source_file_sha256": file_sha, "byte_count": len(raw),
                      "record_count": count,
                      "last_trade_date": last_trade_date}
    relative = path.relative_to(path.parents[2]).as_posix()
    target_record.update({
        "source_entry": relative,
        "source_file_sha256": file_sha,
        "file_byte_count": len(raw),
        "file_record_count": count,
        "source_file_mtime_utc": datetime.fromtimestamp(info_after.st_mtime, timezone.utc).isoformat(),
        "source_security_key": market.upper() + "." + path.stem[2:],
        "trade_date": str(target_day),
    })
    return target_record, {"source_file_sha256": file_sha, "byte_count": len(raw),
                           "record_count": count,
                           "last_trade_date": last_trade_date}


def validate_local_native_dev_record(record: dict[str, Any], *, contract_sha256: str) -> list[str]:
    """校验本地TDX开发候选的自洽性；不授予正式来源或Head资格。"""
    errors: list[str] = []
    if not isinstance(record, dict) or record.get("contract_id") != "V4_TDX_LOCAL_NATIVE_DEV_CANDIDATE_R1":
        return ["LOCAL_NATIVE_DEV_CANDIDATE_CONTRACT_INVALID"]
    manifest = record.get("manifest")
    if not isinstance(manifest, dict):
        return ["LOCAL_NATIVE_DEV_MANIFEST_INVALID"]
    for key, expected in (("source_role", "TDX_LOCAL_NATIVE"),
                          ("candidate_status", "DEV_VALIDATED"),
                          ("formal_source_acceptance", False),
                          ("official_tdx_zip", False),
                          ("production_head_eligible", False),
                          ("AS_RECORDED", False), ("PIT_ELIGIBLE", False)):
        if manifest.get(key) != expected:
            errors.append("LOCAL_NATIVE_DEV_MANIFEST_" + key.upper() + "_INVALID")
    if record.get("contract_ref", {}).get("raw_sha256") != contract_sha256:
        errors.append("LOCAL_NATIVE_DEV_CONTRACT_BINDING_MISMATCH")
    if (record.get("contract_ref", {}).get("contract_id") != LOCAL_NATIVE_DEV_CONTRACT_ID
            or record.get("contract_ref", {}).get("version") != LOCAL_NATIVE_DEV_CONTRACT_VERSION):
        errors.append("LOCAL_NATIVE_DEV_CONTRACT_IDENTITY_INVALID")
    owner = record.get("owner_candidate")
    if (not isinstance(owner, dict) or owner.get("owner_id") != "V4-00D"
            or owner.get("status") != "DEV_CANDIDATE_UNSIGNED"
            or owner.get("formal_owner_approval") is not False):
        errors.append("LOCAL_NATIVE_DEV_OWNER_CANDIDATE_INVALID")
    rows = manifest.get("target_bars")
    universe = manifest.get("universe")
    if not isinstance(rows, list) or not rows or not isinstance(universe, list) or not universe:
        return errors + ["LOCAL_NATIVE_DEV_DATASET_REQUIRED"]
    if manifest.get("target_bar_count") != len(rows) or manifest.get("universe_count") != len(universe):
        errors.append("LOCAL_NATIVE_DEV_ROW_COUNT_MISMATCH")
    if len({row.get("source_security_key") for row in rows if isinstance(row, dict)}) != len(rows):
        errors.append("LOCAL_NATIVE_DEV_TDX_SYMBOL_DUPLICATE")
    if len({row.get("source_security_key") for row in universe if isinstance(row, dict)}) != len(universe):
        errors.append("LOCAL_NATIVE_DEV_UNIVERSE_SYMBOL_DUPLICATE")
    if set(manifest.get("board_counts", {})) != set(_BOARD_PREFIXES):
        errors.append("LOCAL_NATIVE_DEV_BOARD_SCOPE_INVALID")
    expected_rows_sha = hashlib.sha256(_canonical_json(rows)).hexdigest()
    expected_universe_sha = hashlib.sha256(_canonical_json(universe)).hexdigest()
    if manifest.get("target_rows_sha256") != expected_rows_sha:
        errors.append("LOCAL_NATIVE_DEV_TDX_ROWS_DIGEST_MISMATCH")
    if manifest.get("universe_sha256") != expected_universe_sha:
        errors.append("LOCAL_NATIVE_DEV_UNIVERSE_DIGEST_MISMATCH")
    if manifest.get("price_basis") != "TDX_RAW_UNADJUSTED_NATIVE":
        errors.append("LOCAL_NATIVE_DEV_PRICE_BASIS_INVALID")
    if manifest.get("units") != {"price": "CNY/share", "amount": "CNY", "volume": "share"}:
        errors.append("LOCAL_NATIVE_DEV_UNITS_INVALID")
    retention = manifest.get("pg_retention")
    if (not isinstance(retention, dict)
            or retention.get("retained") != "T0_PARSED_ROWS_AND_FULL_SOURCE_FILE_SHA256_ONLY"
            or retention.get("full_raw_day_bytes_stored") is not False):
        errors.append("LOCAL_NATIVE_DEV_PG_RETENTION_SCOPE_INVALID")
    board_counts = {board: sum(row.get("board_scope") == board for row in rows if isinstance(row, dict))
                    for board in _BOARD_PREFIXES}
    board_universe_counts = {board: sum(row.get("board_scope") == board for row in universe if isinstance(row, dict))
                             for board in _BOARD_PREFIXES}
    if manifest.get("board_counts") != board_counts or manifest.get("board_universe_counts") != board_universe_counts:
        errors.append("LOCAL_NATIVE_DEV_BOARD_COUNTS_INVALID")
    identity_binding_sha = hashlib.sha256(_canonical_json([
        {"symbol": row.get("source_security_key"), "security_id": row.get("security_id"),
         "source_revision_id": row.get("identity_source_revision_id"),
         "system_available_at": row.get("identity_system_available_at")}
        for row in sorted(universe, key=lambda item: item.get("source_security_key", ""))
        if isinstance(row, dict)
    ])).hexdigest()
    if manifest.get("pg_candidate_binding_sha256") != identity_binding_sha:
        errors.append("LOCAL_NATIVE_DEV_PG_IDENTITY_BINDING_MISMATCH")
    if not isinstance(manifest.get("source_observed_at_utc"), str):
        errors.append("LOCAL_NATIVE_DEV_OBSERVATION_CLOCK_REQUIRED")
    baostock = manifest.get("baostock_diagnostics")
    if not isinstance(baostock, dict) or baostock.get("binding_status") != "DIAGNOSTIC_ONLY":
        errors.append("LOCAL_NATIVE_DEV_BAOSTOCK_DIAGNOSTIC_BINDING_INVALID")
    return errors


def build_local_native_dev_candidate(
    *, source_root: Path, trade_date: str, identity_candidates: dict[str, dict[str, Any]],
    baostock_rows: list[dict[str, Any]], observed_at_utc: str,
    contract_sha256: str, baostock_query_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a complete T0 development candidate from configured local TDX plus PG identity candidates."""
    target_day = int(trade_date.replace("-", ""))
    if len(trade_date) != 10 or not trade_date[4:5] == "-" or not trade_date[7:8] == "-":
        raise LocalSnapshotError("LOCAL_NATIVE_DEV_TRADE_DATE_INVALID")
    try:
        datetime.fromisoformat(observed_at_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LocalSnapshotError("LOCAL_NATIVE_DEV_OBSERVATION_CLOCK_INVALID") from exc
    if not observed_at_utc.endswith(("Z", "+00:00")):
        raise LocalSnapshotError("LOCAL_NATIVE_DEV_OBSERVATION_CLOCK_MUST_BE_UTC")
    source = Path(source_root).resolve(strict=True)
    vipdoc = source / "vipdoc"
    if not vipdoc.is_dir():
        raise LocalSnapshotError("LOCAL_NATIVE_DEV_TDX_VIPDOC_REQUIRED")
    bao_by_code = {}
    for row in baostock_rows:
        code = str(row.get("code") or "").strip().lower()
        if not code or code in bao_by_code:
            raise LocalSnapshotError("LOCAL_NATIVE_DEV_BAOSTOCK_SYMBOL_INVALID_OR_DUPLICATE")
        if str(row.get("date") or trade_date) != trade_date:
            raise LocalSnapshotError("LOCAL_NATIVE_DEV_BAOSTOCK_T0_MISMATCH")
        bao_by_code[code] = dict(row)
    adjustflags = sorted({str(row.get("adjustflag")) for row in bao_by_code.values() if row.get("adjustflag") is not None})
    if adjustflags and adjustflags != ["3"]:
        raise LocalSnapshotError("LOCAL_NATIVE_DEV_BAOSTOCK_ADJUSTMENT_BASIS_MISMATCH")

    target_bars: list[dict[str, Any]] = []
    universe: list[dict[str, Any]] = []
    source_inventory: list[dict[str, Any]] = []
    for symbol, identity in sorted(identity_candidates.items()):
        market, code = symbol.split(".", 1)
        board = _local_board(market, code)
        if not board or identity.get("security_id") is None:
            raise LocalSnapshotError("LOCAL_NATIVE_DEV_PG_IDENTITY_CANDIDATE_INVALID:" + symbol)
        path = vipdoc / market.lower() / "lday" / (market.lower() + code + ".day")
        target, file_meta = (None, None)
        if path.is_file():
            target, file_meta = _read_native_target_file(path, market=market, target_day=target_day)
            source_inventory.append({"source_entry": path.relative_to(vipdoc).as_posix(), **file_meta})
        bao = bao_by_code.get(symbol.lower())
        if target is None:
            if not bao or str(bao.get("tradestatus")) != "0":
                raise LocalSnapshotError("LOCAL_NATIVE_DEV_T0_BAR_GAP_WITHOUT_SUSPENSION_PROOF:" + symbol)
            universe.append({
                **identity, "trade_date": trade_date, "t0_status": "SUSPENDED_NO_TDX_BAR",
                "tdx_bar_present": False,
                "baostock_suspension_evidence": {
                    "code": symbol, "date": trade_date, "tradestatus": "0",
                    "observed_at_utc": observed_at_utc,
                },
                "source_file_sha256": file_meta.get("source_file_sha256") if file_meta else None,
            })
            continue
        target.update({
            **identity,
            "security_id": str(identity["security_id"]),
            "source_security_key": symbol.lower(),
            "board_scope": board,
        })
        target_bars.append(target)
        universe.append({
            **identity, "trade_date": trade_date, "t0_status": "TDX_BAR_PRESENT",
            "tdx_bar_present": True, "source_file_sha256": target["source_file_sha256"],
        })

    if not universe:
        raise LocalSnapshotError("LOCAL_NATIVE_DEV_UNIVERSE_EMPTY")
    pg_symbols_lower = {symbol.lower() for symbol in identity_candidates}
    for code in bao_by_code:
        if code not in pg_symbols_lower:
            raise LocalSnapshotError("LOCAL_NATIVE_DEV_BAOSTOCK_OUTSIDE_PG_CANDIDATE_UNIVERSE:" + code)
    target_bars.sort(key=lambda row: row["source_security_key"])
    universe.sort(key=lambda row: row["source_security_key"])
    board_counts = {board: sum(row["board_scope"] == board for row in target_bars) for board in _BOARD_PREFIXES}
    board_universe_counts = {board: sum(row["board_scope"] == board for row in universe) for board in _BOARD_PREFIXES}
    target_rows_sha = hashlib.sha256(_canonical_json(target_bars)).hexdigest()
    universe_sha = hashlib.sha256(_canonical_json(universe)).hexdigest()
    identity_binding_sha = hashlib.sha256(_canonical_json([
        {"symbol": row["source_security_key"], "security_id": row["security_id"],
         "source_revision_id": row["identity_source_revision_id"],
         "system_available_at": row["identity_system_available_at"]}
        for row in universe
    ])).hexdigest()
    from .baostock_daily_update_source import crosscheck_tdx_with_baostock
    diagnostics = crosscheck_tdx_with_baostock(
        trade_date=trade_date, tdx_rows=target_bars,
        baostock_rows=[row for row in baostock_rows if str(row.get("code", "")).lower() in
                       {item["source_security_key"] for item in target_bars}],
    )
    manifest = {
        "source_role": "TDX_LOCAL_NATIVE", "candidate_status": "DEV_VALIDATED",
        "formal_source_acceptance": False, "official_tdx_zip": False,
        "production_head_eligible": False, "AS_RECORDED": False, "PIT_ELIGIBLE": False,
        "price_basis": "TDX_RAW_UNADJUSTED_NATIVE",
        "units": {"price": "CNY/share", "amount": "CNY", "volume": "share"},
        "pg_retention": {
            "retained": "T0_PARSED_ROWS_AND_FULL_SOURCE_FILE_SHA256_ONLY",
            "full_raw_day_bytes_stored": False,
        },
        "trade_date": trade_date, "source_root_read_only": True,
        "source_scope": "vipdoc/{sh,sz}/lday/*.day", "source_inventory": source_inventory,
        "source_observed_at_utc": observed_at_utc,
        "target_bars": target_bars, "target_bar_count": len(target_bars),
        "target_rows_sha256": target_rows_sha,
        "universe": universe, "universe_count": len(universe),
        "universe_sha256": universe_sha, "pg_candidate_binding_sha256": identity_binding_sha,
        "board_counts": board_counts, "board_universe_counts": board_universe_counts,
        "baostock_diagnostics": {
            "binding_status": "DIAGNOSTIC_ONLY", "result": diagnostics,
            "query_evidence": baostock_query_evidence,
            "rows": [row for row in baostock_rows if str(row.get("code", "")).lower() in
                     {item["source_security_key"] for item in target_bars} or
                     str(row.get("tradestatus")) == "0"],
        },
    }
    record = {
        "contract_id": "V4_TDX_LOCAL_NATIVE_DEV_CANDIDATE_R1", "contract_version": "1.0.0",
        "contract_ref": {"contract_id": LOCAL_NATIVE_DEV_CONTRACT_ID,
                         "version": LOCAL_NATIVE_DEV_CONTRACT_VERSION, "raw_sha256": contract_sha256},
        "owner_candidate": {"owner_id": "V4-00D", "status": "DEV_CANDIDATE_UNSIGNED",
                            "formal_owner_approval": False},
        "manifest": manifest,
    }
    errors = validate_local_native_dev_record(record, contract_sha256=contract_sha256)
    if errors:
        raise LocalSnapshotError("LOCAL_NATIVE_DEV_CANDIDATE_INVALID:" + ",".join(errors))
    record["candidate_sha256"] = hashlib.sha256(_canonical_json(record)).hexdigest()
    return record


def persist_local_native_dev_candidate(snapshot_root: Path, record: dict[str, Any]) -> dict[str, Any]:
    """Append a DEV-only candidate to existing PG fact storage and independently read it back."""
    trade_date = str(record.get("manifest", {}).get("trade_date") or "")
    if not trade_date:
        raise LocalSnapshotError("LOCAL_NATIVE_DEV_T0_REQUIRED")
    candidate_key = "tdx-local-native:" + trade_date.replace("-", "") + ":" + record["candidate_sha256"]
    store = _snapshot_store(snapshot_root)
    binding = store.append(LOCAL_NATIVE_DEV_FACT_KIND, candidate_key, record, migration_timeout_seconds=120)
    reader = _snapshot_store(snapshot_root)
    read_binding = reader.binding(LOCAL_NATIVE_DEV_FACT_KIND, candidate_key)
    read_record = reader.read(read_binding)
    if read_record != record or read_binding.get("pg_descriptor", {}).get("payload_sha256") != binding.get("pg_descriptor", {}).get("payload_sha256"):
        raise LocalSnapshotError("LOCAL_NATIVE_DEV_PG_READBACK_MISMATCH")
    return {"status": "PG_DEV_CANDIDATE_READBACK_VERIFIED", "binding": read_binding,
            "candidate_sha256": record["candidate_sha256"], "target_rows_sha256": record["manifest"]["target_rows_sha256"],
            "target_bar_count": record["manifest"]["target_bar_count"],
            "universe_count": record["manifest"]["universe_count"]}


def _snapshot_store(snapshot_root: Path):
    repo_root = Path(__file__).resolve().parents[2]
    if not Path(snapshot_root).resolve().is_relative_to(repo_root):
        raise LocalSnapshotError("LOCAL_SNAPSHOT_WORKSPACE_ROOT_REQUIRED")
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore
    return ForwardFactStore(repo_root, "data/v4/historical_source_ingress_pg_r1")


def _persist_manifest_pg(snapshot_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    store = _snapshot_store(snapshot_root)
    record = {"contract_id": "V4_TDX_LOCAL_SNAPSHOT_CANDIDATE_PG_R1",
              "contract_version": "1.0.0", "candidate_status": "DIAGNOSTIC_ONLY",
              "snapshot_id": manifest["snapshot_id"], "content_digest": manifest["content_digest"],
              "manifest": manifest, "AS_RECORDED": False, "PIT_ELIGIBLE": False,
              "accepted_head": False}
    binding = store.append("tdx_local_snapshot_candidate", manifest["snapshot_id"], record,
                           migration_timeout_seconds=120)
    if store.read(binding) != record:
        raise LocalSnapshotError("LOCAL_SNAPSHOT_PG_READBACK_MISMATCH")
    return binding


def _read_manifest_pg(snapshot_root: Path, snapshot_id: str):
    store = _snapshot_store(snapshot_root)
    for binding in store.refs("tdx_local_snapshot_candidate"):
        if binding.get("pg_descriptor", {}).get("fact_key") == snapshot_id:
            record = store.read(binding)
            manifest = record.get("manifest")
            if (record.get("contract_id") != "V4_TDX_LOCAL_SNAPSHOT_CANDIDATE_PG_R1"
                    or record.get("snapshot_id") != snapshot_id
                    or not isinstance(manifest, dict)
                    or manifest.get("content_digest") != record.get("content_digest")
                    or record.get("accepted_head") is not False):
                raise LocalSnapshotError("LOCAL_SNAPSHOT_PG_IDENTITY_INVALID")
            return manifest, binding
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    except Exception:
        Path(temp).unlink(missing_ok=True)
        raise


def _safe_relative(path: Path, base: Path) -> str:
    relative = path.relative_to(base).as_posix()
    parts = PurePosixPath(relative).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise LocalSnapshotError("TDX_RELATIVE_PATH_INVALID")
    return relative


def build_local_snapshot(
    source_root: Path,
    output_root: Path,
    *,
    persist_to_pg: bool = False,
) -> dict[str, Any]:
    """仅读取本地日线文件并原子复制到独立快照目录；入库须显式启用。"""
    def reject_reparse(path):
        info=path.lstat()
        if path.is_symlink() or stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0) & getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400):
            raise LocalSnapshotError('TDX_INPUT_SYMLINK_REJECTED')
    reject_reparse(source_root)
    reject_reparse(source_root/'vipdoc')
    source = source_root.resolve(strict=True)
    vipdoc = (source / "vipdoc").resolve(strict=True)
    if source == output_root.resolve() or source in output_root.resolve().parents:
        raise LocalSnapshotError("SNAPSHOT_OUTPUT_MUST_BE_OUTSIDE_TDX_ROOT")
    files: list[tuple[str, Path]] = []
    for market in ("sh", "sz", "bj"):
        market_root = vipdoc / market / "lday"
        if market_root.is_dir():
            reject_reparse(vipdoc/market)
            reject_reparse(market_root)
            for path in market_root.glob("*.day"):
                reject_reparse(path)
                if path.is_file():
                    files.append((_safe_relative(path, vipdoc), path))
    files.sort(key=lambda item: item[0].casefold())
    if not files:
        raise LocalSnapshotError("NO_TDX_DAY_FILES_FOUND")

    output_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=output_root))
    digest = hashlib.sha256()
    inventory: list[dict[str, Any]] = []
    total_bytes = 0
    try:
        for relative, source_file in files:
            before = source_file.stat()
            destination = staging / Path(*PurePosixPath(relative).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            item_digest = hashlib.sha256()
            byte_count = 0
            with source_file.open("rb") as src, destination.open("xb") as dst:
                for block in iter(lambda: src.read(1024 * 1024), b""):
                    item_digest.update(block)
                    dst.write(block)
                    byte_count += len(block)
                dst.flush()
                os.fsync(dst.fileno())
            after = source_file.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or byte_count != before.st_size:
                raise LocalSnapshotError("TDX_SOURCE_CHANGED_DURING_SNAPSHOT")
            file_sha = item_digest.hexdigest()
            inventory.append({"relative_path": relative, "byte_count": byte_count, "sha256": file_sha})
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(byte_count).encode("ascii"))
            digest.update(b"\0")
            digest.update(file_sha.encode("ascii"))
            digest.update(b"\n")
            total_bytes += byte_count

        content_digest = digest.hexdigest()
        snapshot_id = content_digest
        manifest = {
            "contract_id": "V4_TDX_LOCAL_SNAPSHOT_V1",
            "snapshot_id": snapshot_id,
            "content_digest": content_digest,
            "content_digest_algorithm": "SHA256(sorted relative_path NUL byte_count NUL file_sha256 LF)",
            "source_root": str(source),
            "source_scope": "vipdoc/{sh,sz,bj}/lday/*.day",
            "source_root_read_only": True,
            "copied_outside_source_root": True,
            "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "file_count": len(inventory),
            "byte_count": total_bytes,
            "files": inventory,
        }
        manifest_path = staging / "snapshot_manifest.json"
        _atomic_json(manifest_path, manifest)
        final = output_root / snapshot_id
        if final.exists():
            prior_path = final / "snapshot_manifest.json"
            if not prior_path.is_file():
                raise LocalSnapshotError("IMMUTABLE_SNAPSHOT_ID_COLLISION")
            prior = json.loads(prior_path.read_text(encoding="utf-8"))
            if prior.get("snapshot_id") != snapshot_id or prior.get("content_digest") != content_digest:
                raise LocalSnapshotError("IMMUTABLE_SNAPSHOT_ID_COLLISION")
            if prior.get("files") != inventory:
                raise LocalSnapshotError("IMMUTABLE_SNAPSHOT_INVENTORY_MISMATCH")
            for item in inventory:
                stored = final / Path(*PurePosixPath(item["relative_path"]).parts)
                if not stored.is_file() or stored.stat().st_size != item["byte_count"] or _sha256(stored) != item["sha256"]:
                    raise LocalSnapshotError("IMMUTABLE_SNAPSHOT_CONTENT_CHANGED")
            shutil.rmtree(staging)
            binding = _persist_manifest_pg(output_root, prior) if persist_to_pg else None
            return {"snapshot_id": snapshot_id, "manifest_path": str(prior_path), "file_count": len(inventory), "byte_count": total_bytes, "content_digest": content_digest, "pg_binding": binding, "status": "REUSED_IDENTICAL_SNAPSHOT"}
        os.replace(staging, final)
        binding = _persist_manifest_pg(output_root, manifest) if persist_to_pg else None
        return {"snapshot_id": snapshot_id, "manifest_path": str(final / "snapshot_manifest.json"), "file_count": len(inventory), "byte_count": total_bytes, "content_digest": content_digest, "pg_binding": binding, "status": "SNAPSHOT_CREATED"}
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def verify_local_snapshot(
    snapshot_root: Path,
    snapshot_id: str,
    *,
    require_pg_binding: bool = False,
) -> dict[str, Any]:
    """重新计算本地快照摘要；仅显式要求时才读取 PostgreSQL 绑定。"""
    snapshot = (snapshot_root / snapshot_id).resolve(strict=True)
    manifest_path = snapshot / "snapshot_manifest.json"
    binding = None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if require_pg_binding:
        pg_manifest = _read_manifest_pg(snapshot_root, snapshot_id)
        if pg_manifest is None:
            raise LocalSnapshotError("LOCAL_SNAPSHOT_PG_INGRESS_READBACK_REQUIRED")
        manifest, binding = pg_manifest
    if manifest.get("snapshot_id") != snapshot_id or manifest.get("content_digest_algorithm") != "SHA256(sorted relative_path NUL byte_count NUL file_sha256 LF)":
        raise LocalSnapshotError("LOCAL_SNAPSHOT_MANIFEST_IDENTITY_MISMATCH")
    digest = hashlib.sha256()
    total_bytes = 0
    seen: set[str] = set()
    for item in sorted(manifest.get("files", []), key=lambda row: row["relative_path"].casefold()):
        relative = item["relative_path"]
        posix = PurePosixPath(relative)
        if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts) or relative in seen:
            raise LocalSnapshotError("LOCAL_SNAPSHOT_INVENTORY_INVALID")
        seen.add(relative)
        path = (snapshot / Path(*posix.parts)).resolve(strict=True)
        if snapshot not in path.parents or not path.is_file() or path.stat().st_size != int(item["byte_count"]):
            raise LocalSnapshotError("LOCAL_SNAPSHOT_FILE_SIZE_OR_PATH_MISMATCH")
        actual_sha = _sha256(path)
        if actual_sha != item["sha256"]:
            raise LocalSnapshotError("LOCAL_SNAPSHOT_FILE_HASH_MISMATCH")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(path.stat().st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(actual_sha.encode("ascii"))
        digest.update(b"\n")
        total_bytes += path.stat().st_size
    actual_digest = digest.hexdigest()
    if actual_digest != snapshot_id or actual_digest != manifest.get("content_digest"):
        raise LocalSnapshotError("LOCAL_SNAPSHOT_CONTENT_DIGEST_MISMATCH")
    if len(seen) != int(manifest.get("file_count", -1)) or total_bytes != int(manifest.get("byte_count", -1)):
        raise LocalSnapshotError("LOCAL_SNAPSHOT_INVENTORY_TOTAL_MISMATCH")
    return {
        "status": "PASS",
        "snapshot_id": snapshot_id,
        "content_digest": actual_digest,
        "file_count": len(seen),
        "byte_count": total_bytes,
        "manifest_path": str(manifest_path),
        "pg_binding": binding,
    }
