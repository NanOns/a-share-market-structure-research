"""Bounded, fail-closed BaoStock supplemental access.

BaoStock is never a price authority. Credentials are read only from process
environment variables and are never included in receipts or exception text.
The module keeps raw API rows in memory only; callers persist normalized,
hash-bound results through a separate accepted-data writer.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import json
import math
import os
import socket
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo


CONTRACT_ID = "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1"
CONTRACT_VERSION = "1.1.0"
FIELD_MAP_VERSION = "BAOSTOCK_FIELD_MAP_V1.1"
PUBLIC_PACKAGE_VERSION = "0.9.3"
VIP_PACKAGE_VERSION = "0.9.4"
SUPPORTED_PACKAGE_VERSIONS = {PUBLIC_PACKAGE_VERSION, VIP_PACKAGE_VERSION}
# Backward-compatible alias for tests and callers that historically referred to
# the public/runtime package version.
PACKAGE_VERSION = PUBLIC_PACKAGE_VERSION
AUTH_MODES = {"PUBLIC_ANONYMOUS", "PUBLIC_ACCOUNT", "VIP_API_KEY"}
DEFAULT_AUTH_MODE = "PUBLIC_ANONYMOUS"
FIELDS = "date,code,close,volume,amount,turn,tradestatus,isST"
ADJUSTFLAG = "3"
DAILY_HARD_LIMIT = 45_000
DAILY_SOFT_LIMIT = 40_000
REQUEST_TIMEOUT_SECONDS = 30
MAX_TRANSIENT_RETRIES = 1
_SESSION_LOCK = threading.Lock()


class BaoStockError(RuntimeError):
    """Sanitized source/contract failure; never contains credentials."""

    def __init__(self, message: str, *, provider_code: str | None = None, provider_message: str | None = None):
        super().__init__(message)
        self.provider_code = provider_code
        self.provider_message = provider_message


@dataclass(frozen=True)
class NormalizedRow:
    query_code: str
    source_code: str
    trade_date: str
    close_price_cny: float
    volume_shares: int | None
    amount_cny: float | None
    turn_fraction: float | None
    tradestatus: str
    is_st: str
    source_digest: str
    binding_status: str = "UNBOUND"


def normalize_turn(value: str | float | int | None) -> float | None:
    """BaoStock `turn` is percent points, e.g. 1.25 means 1.25%.

    This normalization is permitted only because the official API reference
    defines the field as a percentage; the denominator is circulating shares.
    It does not imply free-float semantics.
    """
    if value is None or str(value).strip() == "":
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise BaoStockError("INVALID_TURN_VALUE")
    return number / 100.0


def normalize_row(query_code: str, row: dict[str, Any]) -> NormalizedRow:
    try:
        source_code = str(row["code"]).strip()
        trade_date = str(row["date"]).strip()
        tradestatus = str(row["tradestatus"]).strip()
        is_st = str(row["isST"]).strip()
        close = float(row["close"])
        volume_raw = str(row.get("volume", "")).strip()
        amount_raw = str(row.get("amount", "")).strip()
        # BaoStock returns blank volume/amount on some suspended daily rows.
        # Preserve that absence; never silently coerce it to zero.
        if tradestatus != "0" and (not volume_raw or not amount_raw):
            raise BaoStockError("INVALID_BAOSTOCK_ROW")
        volume_number = float(volume_raw) if volume_raw else None
        volume = int(volume_number) if volume_number is not None else None
        amount = float(amount_raw) if amount_raw else None
        turn = normalize_turn(row.get("turn"))
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise BaoStockError("INVALID_BAOSTOCK_ROW") from exc
    try:
        datetime.strptime(trade_date, "%Y-%m-%d")
    except ValueError as exc:
        raise BaoStockError("INVALID_BAOSTOCK_ROW") from exc
    if not source_code or not math.isfinite(close) or close < 0:
        raise BaoStockError("INVALID_BAOSTOCK_ROW")
    if ((volume_number is not None and (not math.isfinite(volume_number) or volume_number != volume or volume < 0))
            or (amount is not None and (not math.isfinite(amount) or amount < 0))):
        raise BaoStockError("INVALID_BAOSTOCK_ROW")
    if tradestatus != "0" and (volume is None or amount is None):
        raise BaoStockError("INVALID_BAOSTOCK_ROW")
    if tradestatus not in {"0", "1"} or is_st not in {"0", "1"}:
        raise BaoStockError("INVALID_BAOSTOCK_STATUS")
    canonical = {
        "query_code": query_code,
        "source_code": source_code,
        "trade_date": trade_date,
        "close_price_cny": close,
        "volume_shares": volume,
        "amount_cny": amount,
        "turn_fraction": turn,
        "tradestatus": tradestatus,
        "is_st": is_st,
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return NormalizedRow(**canonical, source_digest=digest)


def strict_fingerprint(
    local: dict[str, float | int], source: NormalizedRow, tolerance: dict[str, float]
) -> bool:
    """Strictly bind only exact identity/date plus accepted source-specific limits."""
    if (local.get("security_id") != source.query_code or source.source_code != source.query_code
            or local.get("trade_date") != int(source.trade_date.replace("-", ""))):
        return False
    if source.volume_shares is None or source.amount_cny is None:
        return False
    pairs = {
        "close": (float(local["close"]), source.close_price_cny),
        "volume": (float(local["volume"]), float(source.volume_shares)),
        "amount": (float(local["amount"]), source.amount_cny),
    }
    if set(tolerance) != set(pairs):
        raise BaoStockError("TOLERANCE_CONTRACT_INVALID")
    for key, (expected, actual) in pairs.items():
        allowed = float(tolerance[key])
        if not math.isfinite(allowed) or allowed < 0:
            raise BaoStockError("TOLERANCE_CONTRACT_INVALID")
        if not math.isfinite(expected) or abs(expected - actual) > allowed:
            return False
    return True


def evaluate_binding(
    local: dict[str, float | int],
    source: NormalizedRow,
    tolerance_contract: dict[str, Any] | None,
) -> str:
    """Return strict only when independent tolerance acceptance is explicit."""
    if not tolerance_contract:
        return "UNBOUND"
    if not strict_fingerprint(local, source, (tolerance_contract or {}).get("tolerances", {})):
        return "UNBOUND"
    status_match = (str(local.get("tradestatus", "")) == source.tradestatus
                    and str(local.get("isST", "")) == source.is_st)
    if not status_match:
        return "BOUND_SOFT"
    if not tolerance_contract or tolerance_contract.get("acceptance") != "INDEPENDENTLY_ACCEPTED":
        return "BOUND_SOFT"
    required = {"contract_id", "version", "evidence_digest", "accepted_by", "accepted_at_utc"}
    if not required.issubset(tolerance_contract) or not all(tolerance_contract.get(key) for key in required):
        return "BOUND_SOFT"
    return "BOUND_STRICT"


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, sort_keys=True, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    except Exception:
        Path(name).unlink(missing_ok=True)
        raise


class RequestBudget:
    """Shanghai-day, durable request ledger. Retries consume budget too."""

    def __init__(self, ledger_path: Path, hard_limit: int = DAILY_HARD_LIMIT, soft_limit: int = DAILY_SOFT_LIMIT):
        if hard_limit < 1 or hard_limit > DAILY_HARD_LIMIT or soft_limit < 1 or soft_limit > hard_limit:
            raise BaoStockError("BUDGET_LIMIT_OUTSIDE_CONTRACT")
        self.path = ledger_path
        self.hard_limit = hard_limit
        self.soft_limit = soft_limit
        self.day = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
        self._mutex = threading.Lock()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"ledger_version": 1, "by_shanghai_date": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise BaoStockError("REQUEST_LEDGER_UNREADABLE_FAIL_CLOSED") from exc
        if not isinstance(data.get("by_shanghai_date"), dict):
            raise BaoStockError("REQUEST_LEDGER_INVALID_FAIL_CLOSED")
        return data

    def consume(self, operation: str, bypass_soft_stop: bool = False) -> int:
        if not operation or any(char in operation for char in "\r\n\t"):
            raise BaoStockError("REQUEST_OPERATION_INVALID")
        with self._mutex:
            payload = self._load()
            today = payload["by_shanghai_date"].setdefault(self.day, {"count": 0, "operations": {}})
            if not bypass_soft_stop and int(today.get("count", 0)) >= self.soft_limit:
                raise BaoStockError("DAILY_REQUEST_SOFT_STOP")
            if int(today.get("count", 0)) >= self.hard_limit:
                raise BaoStockError("DAILY_REQUEST_HARD_STOP")
            today["count"] = int(today["count"]) + 1
            ops = today.setdefault("operations", {})
            ops[operation] = int(ops.get(operation, 0)) + 1
            payload["last_updated_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            _atomic_json(self.path, payload)
            return int(today["count"])


class BaoStockClient:
    """One serialized SDK session with bounded calls and secret-free metadata."""

    def __init__(self, budget: RequestBudget, sdk: Any | None = None, timeout: int = REQUEST_TIMEOUT_SECONDS,
                 auth_mode: str | None = None):
        self.budget = budget
        self.sdk = sdk
        self.timeout = timeout
        self.auth_mode = (auth_mode or os.environ.get("BAOSTOCK_AUTH_MODE") or DEFAULT_AUTH_MODE).upper()
        self.logged_in = False
        self._lock_held = False
        self._process_lock: Path | None = None
        self.login_result: dict[str, str] = {"error_code": "NOT_ATTEMPTED", "error_msg": ""}
        self.logout_result: dict[str, str] = {"error_code": "NOT_ATTEMPTED", "error_msg": ""}
        self.runtime_endpoint: dict[str, Any] = {}
        self.last_query_result: dict[str, Any] = {"error_code": "NOT_ATTEMPTED", "error_msg": "", "fields": []}

    @staticmethod
    def credentials_present(auth_mode: str = DEFAULT_AUTH_MODE) -> bool:
        mode = auth_mode.upper()
        if mode == "PUBLIC_ANONYMOUS":
            return True
        if mode == "PUBLIC_ACCOUNT":
            return bool(os.environ.get("BAOSTOCK_USERNAME") and os.environ.get("BAOSTOCK_PASSWORD"))
        if mode == "VIP_API_KEY":
            return all(os.environ.get(name) for name in ("BAOSTOCK_USERNAME", "BAOSTOCK_PASSWORD", "BAOSTOCK_API_KEY"))
        return False

    @staticmethod
    def _safe_message(value: Any) -> str:
        message = str(value or "")[:500]
        for name in ("BAOSTOCK_USERNAME", "BAOSTOCK_PASSWORD", "BAOSTOCK_API_KEY"):
            secret = os.environ.get(name)
            if secret:
                message = message.replace(secret, "[REDACTED]")
        return message

    def _capture_endpoint(self) -> None:
        try:
            import baostock.common.contants as constants
            import baostock.common.context as context

            host = (constants.BAOSTOCK_VIP_SERVER_IP if self.auth_mode == "VIP_API_KEY"
                    else constants.BAOSTOCK_SERVER_IP)
            port = int(constants.BAOSTOCK_SERVER_PORT)
            sock = getattr(context, "default_socket", None)
            peer = sock.getpeername() if sock is not None else None
            self.runtime_endpoint = {
                "configured_host": host,
                "configured_port": port,
                "connected_peer_ip": peer[0] if peer else None,
                "connected_peer_port": peer[1] if peer else None,
            }
            if sock is not None:
                sock.settimeout(self.timeout)
        except Exception:
            self.runtime_endpoint = {"configured_host": None, "configured_port": None,
                                     "connected_peer_ip": None, "connected_peer_port": None}

    def __enter__(self) -> "BaoStockClient":
        if self.auth_mode not in AUTH_MODES:
            raise BaoStockError("BAOSTOCK_AUTH_MODE_INVALID")
        if not self.credentials_present(self.auth_mode):
            raise BaoStockError("BAOSTOCK_CREDENTIAL_ENV_MISSING_FOR_AUTH_MODE")
        if not _SESSION_LOCK.acquire(blocking=False):
            raise BaoStockError("ANOTHER_BAOSTOCK_SESSION_ACTIVE")
        self._lock_held = True
        try:
            self._process_lock = self.budget.path.with_suffix(self.budget.path.suffix + ".session.lock")
            self._process_lock.parent.mkdir(parents=True, exist_ok=True)
            try:
                fd = os.open(self._process_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            except FileExistsError as exc:
                raise BaoStockError("ANOTHER_BAOSTOCK_PROCESS_ACTIVE") from exc
            if self.sdk is None:
                import baostock as self_sdk  # type: ignore[no-redef]
                self.sdk = self_sdk
            version = importlib.metadata.version("baostock")
            expected_version = VIP_PACKAGE_VERSION if self.auth_mode == "VIP_API_KEY" else PUBLIC_PACKAGE_VERSION
            if version != expected_version:
                raise BaoStockError("BAOSTOCK_PACKAGE_VERSION_UNPINNED_FOR_AUTH_MODE")
            prior_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(self.timeout)
            try:
                self.budget.consume("login")
                with contextlib.redirect_stdout(_NullWriter()), contextlib.redirect_stderr(_NullWriter()):
                    if self.auth_mode == "PUBLIC_ANONYMOUS":
                        # SDK state is process-global. Clear a key left by an earlier
                        # in-process VIP client so this mode cannot silently route VIP.
                        import baostock.common.context as context
                        if hasattr(context, "apiKey"):
                            delattr(context, "apiKey")
                        result = self.sdk.login()
                    elif self.auth_mode == "PUBLIC_ACCOUNT":
                        result = self.sdk.login(os.environ["BAOSTOCK_USERNAME"], os.environ["BAOSTOCK_PASSWORD"])
                    else:
                        self.sdk.set_API_key(os.environ["BAOSTOCK_API_KEY"])
                        result = self.sdk.login(os.environ["BAOSTOCK_USERNAME"], os.environ["BAOSTOCK_PASSWORD"])
            finally:
                socket.setdefaulttimeout(prior_timeout)
            self.login_result = {
                "error_code": str(getattr(result, "error_code", "UNKNOWN")),
                "error_msg": self._safe_message(getattr(result, "error_msg", "")),
            }
            self._capture_endpoint()
            if getattr(result, "error_code", None) != "0":
                raise BaoStockError("BAOSTOCK_LOGIN_FAILED", provider_code=self.login_result["error_code"],
                                    provider_message=self.login_result["error_msg"])
            self.logged_in = True
            return self
        except Exception:
            self._release()
            raise

    def _release(self) -> None:
        if self._process_lock is not None:
            self._process_lock.unlink(missing_ok=True)
            self._process_lock = None
        if self._lock_held:
            self._lock_held = False
            _SESSION_LOCK.release()

    def query_daily(self, code: str, start_date: str, end_date: str) -> list[NormalizedRow]:
        if not self.logged_in or self.sdk is None:
            raise BaoStockError("BAOSTOCK_SESSION_NOT_READY")
        if not code or start_date > end_date:
            raise BaoStockError("QUERY_RANGE_INVALID")
        for attempt in range(MAX_TRANSIENT_RETRIES + 1):
            self.budget.consume("query_history_k_data_plus_adjustflag_3")
            try:
                with contextlib.redirect_stdout(_NullWriter()), contextlib.redirect_stderr(_NullWriter()):
                    result = self.sdk.query_history_k_data_plus(
                        code,
                        FIELDS,
                        start_date=start_date,
                        end_date=end_date,
                        frequency="d",
                        adjustflag=ADJUSTFLAG,
                    )
                    self.last_query_result = {
                        "error_code": str(getattr(result, "error_code", "UNKNOWN")),
                        "error_msg": self._safe_message(getattr(result, "error_msg", "")),
                        "fields": list(getattr(result, "fields", [])),
                    }
                    if getattr(result, "error_code", None) != "0":
                        provider_code = str(getattr(result, "error_code", "UNKNOWN"))
                        safe_code = "".join(char for char in provider_code if char.isalnum() or char in "-_")[:24] or "UNKNOWN"
                        raise BaoStockError("BAOSTOCK_QUERY_FAILED_CODE_" + safe_code,
                                            provider_code=safe_code,
                                            provider_message=self._safe_message(getattr(result, "error_msg", "")))
                    rows = []
                    while True:
                        if (getattr(result, "cur_row_num", 0) >= len(getattr(result, "data", []))
                                and len(getattr(result, "data", [])) == getattr(result, "per_page_count", -1)
                                and result.cur_row_num > 0):
                            self.budget.consume("query_history_k_data_plus_adjustflag_3_page")
                        if not result.next():
                            break
                        values = result.get_row_data()
                        rows.append(dict(zip(result.fields, values, strict=True)))
                return [normalize_row(code, row) for row in rows]
            except (TimeoutError, socket.timeout, ConnectionError, OSError):
                if attempt >= MAX_TRANSIENT_RETRIES:
                    raise BaoStockError("BAOSTOCK_QUERY_TRANSPORT_FAILED") from None
        raise BaoStockError("BAOSTOCK_QUERY_FAILED")

    def query_rows(self, operation: str, method_name: str, *args: Any, max_rows: int = 10_000,
                   max_pages: int = 10, **kwargs: Any) -> tuple[list[dict[str, str]], dict[str, Any]]:
        """Bounded metadata query with explicit accounting for SDK pagination."""
        if not self.logged_in or self.sdk is None:
            raise BaoStockError("BAOSTOCK_SESSION_NOT_READY")
        if max_rows < 1 or max_pages < 1:
            raise BaoStockError("QUERY_RESPONSE_BOUND_INVALID")
        self.budget.consume(operation)
        try:
            with contextlib.redirect_stdout(_NullWriter()), contextlib.redirect_stderr(_NullWriter()):
                result = getattr(self.sdk, method_name)(*args, **kwargs)
                pages = 1
                rows = []
                self.last_query_result = {
                    "error_code": str(getattr(result, "error_code", "UNKNOWN")),
                    "error_msg": self._safe_message(getattr(result, "error_msg", "")),
                    "fields": list(getattr(result, "fields", [])),
                }
                if getattr(result, "error_code", None) != "0":
                    provider_code = str(getattr(result, "error_code", "UNKNOWN"))
                    safe_code = "".join(char for char in provider_code if char.isalnum() or char in "-_")[:24] or "UNKNOWN"
                    raise BaoStockError(f"BAOSTOCK_{operation.upper()}_FAILED_CODE_{safe_code}",
                                        provider_code=safe_code,
                                        provider_message=self.last_query_result["error_msg"])
                while True:
                    if (getattr(result, "cur_row_num", 0) >= len(getattr(result, "data", []))
                            and len(getattr(result, "data", [])) == getattr(result, "per_page_count", -1)
                            and result.cur_row_num > 0):
                        if pages >= max_pages:
                            raise BaoStockError("QUERY_PAGE_BOUND_EXCEEDED")
                        self.budget.consume(operation + "_page")
                        pages += 1
                    if not result.next():
                        break
                    rows.append(dict(zip(result.fields, result.get_row_data(), strict=True)))
                    if len(rows) > max_rows:
                        raise BaoStockError("QUERY_ROW_BOUND_EXCEEDED")
                metadata = {
                    "error_code": str(getattr(result, "error_code", "UNKNOWN")),
                    "error_msg": self._safe_message(getattr(result, "error_msg", "")),
                    "fields": list(getattr(result, "fields", [])),
                    "page_count": pages,
                }
                if metadata["error_code"] != "0":
                    raise BaoStockError("BAOSTOCK_QUERY_FAILED_AFTER_PAGINATION",
                                        provider_code=metadata["error_code"],
                                        provider_message=metadata["error_msg"])
                self.last_query_result = metadata
                return rows, metadata
        except (TimeoutError, socket.timeout, ConnectionError, OSError):
            raise BaoStockError("BAOSTOCK_QUERY_TRANSPORT_FAILED") from None

    def probe_stock_basic(self, code: str) -> list[dict[str, str]]:
        """Single-security metadata probe used only to isolate API capability."""
        rows, _ = self.query_rows("query_stock_basic", "query_stock_basic", code=code, max_rows=5)
        return rows

    def probe_trade_dates(self, start_date: str, end_date: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
        return self.query_rows("query_trade_dates", "query_trade_dates", start_date=start_date,
                               end_date=end_date, max_rows=40, max_pages=1)

    def probe_all_stock(self, day: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
        return self.query_rows("query_all_stock", "query_all_stock", day=day, max_rows=10_000, max_pages=10)

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self.logged_in and self.sdk is not None:
                self.budget.consume("logout", bypass_soft_stop=True)
                with contextlib.redirect_stdout(_NullWriter()), contextlib.redirect_stderr(_NullWriter()):
                    result = self.sdk.logout()
                self.logout_result = {
                    "error_code": str(getattr(result, "error_code", "UNKNOWN")),
                    "error_msg": self._safe_message(getattr(result, "error_msg", "")),
                }
        finally:
            self.logged_in = False
            self._release()


class _NullWriter:
    def write(self, value: str) -> int:
        return len(value)

    def flush(self) -> None:
        return None


def package_metadata() -> dict[str, str]:
    """Return pinned runtime metadata without any credential-derived values."""
    dist = importlib.metadata.distribution("baostock")
    if dist.version not in SUPPORTED_PACKAGE_VERSIONS:
        raise BaoStockError("BAOSTOCK_PACKAGE_VERSION_UNPINNED")
    package_files = sorted(str(path).replace("\\", "/") for path in (dist.files or ()) if str(path).endswith(".py"))
    digest = hashlib.sha256()
    for relative in package_files:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(dist.locate_file(relative).read_bytes())
        digest.update(b"\n")
    return {
        "package": "baostock",
        "version": dist.version,
        "installed_python_sources_sha256": digest.hexdigest(),
        "supported_auth_modes": ",".join(sorted(AUTH_MODES)),
        "default_auth_mode": DEFAULT_AUTH_MODE,
        "expected_version_for_default_auth_mode": PUBLIC_PACKAGE_VERSION,
        "expected_version_for_vip_auth_mode": VIP_PACKAGE_VERSION,
        "adjustflag": ADJUSTFLAG,
        "fields": FIELDS,
    }


def run_history_job(
    client: BaoStockClient,
    codes: Iterable[str],
    start_date: str,
    end_date: str,
    checkpoint_path: Path,
    bind_row: Callable[[NormalizedRow], str],
    persist_bound_rows: Callable[[str, list[NormalizedRow]], None],
    job_id: str,
    max_job_seconds: int = 21_600,
) -> dict[str, Any]:
    """Serial, deterministic, resumable worker; checkpoint stores no market rows."""
    ordered_codes = sorted(set(codes))
    if not ordered_codes or not job_id or max_job_seconds < 1:
        raise BaoStockError("HISTORY_JOB_INPUT_INVALID")
    request_identity = {
        "job_id": job_id,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "codes_sha256": hashlib.sha256("\n".join(ordered_codes).encode()).hexdigest(),
        "start_date": start_date,
        "end_date": end_date,
        "frequency": "d",
        "adjustflag": ADJUSTFLAG,
    }
    if checkpoint_path.exists():
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise BaoStockError("CHECKPOINT_UNREADABLE_FAIL_CLOSED") from exc
        if checkpoint.get("request_identity") != request_identity:
            raise BaoStockError("CHECKPOINT_IDENTITY_MISMATCH")
    else:
        checkpoint = {"request_identity": request_identity, "completed": {}, "failures": {}}
    completed = checkpoint.setdefault("completed", {})
    failures = checkpoint.setdefault("failures", {})
    started = __import__("time").monotonic()
    for code in ordered_codes:
        if code in completed:
            continue
        if __import__("time").monotonic() - started >= max_job_seconds:
            checkpoint["status"] = "PAUSED_JOB_TIMEOUT"
            _atomic_json(checkpoint_path, checkpoint)
            return checkpoint
        try:
            rows = client.query_daily(code, start_date, end_date)
            if any(row.query_code != code or row.source_code != code or not start_date <= row.trade_date <= end_date for row in rows):
                raise BaoStockError("QUERY_RESPONSE_IDENTITY_OR_DATE_MISMATCH")
            digests = [row.source_digest for row in rows]
            if len(digests) != len(set(digests)):
                raise BaoStockError("DUPLICATE_SOURCE_ROWS")
            strict_rows = [row for row in rows if bind_row(row) == "BOUND_STRICT"]
            persist_bound_rows(code, strict_rows)
            completed[code] = {
                "source_row_count": len(rows),
                "bound_strict_row_count": len(strict_rows),
                "rows_digest": hashlib.sha256("\n".join(digests).encode()).hexdigest(),
            }
            failures.pop(code, None)
            checkpoint["status"] = "RUNNING"
            _atomic_json(checkpoint_path, checkpoint)
        except Exception as exc:
            reason = str(exc) if isinstance(exc, BaoStockError) else "BAOSTOCK_WORKER_FAILURE"
            failures[code] = reason
            checkpoint["status"] = "BLOCKED_WITH_CHECKPOINT"
            _atomic_json(checkpoint_path, checkpoint)
            raise BaoStockError(reason) from None
    checkpoint["status"] = "COMPLETE" if not failures else "BLOCKED_WITH_CHECKPOINT"
    _atomic_json(checkpoint_path, checkpoint)
    return checkpoint
