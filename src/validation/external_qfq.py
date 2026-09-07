from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import json
import time
from typing import Callable
import urllib.error
import urllib.parse
import urllib.request


CENT = Decimal("0.01")
TOLERANCE = Decimal("0.01")
EASTMONEY_ENDPOINT = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
TENCENT_ENDPOINT = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
TENCENT_RAW_ENDPOINT = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"


@dataclass(frozen=True)
class ExternalBar:
    trade_date: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


def eastmoney_secid(security_id: str) -> str:
    market, code = security_id.split(".", 1)
    if market == "SH":
        return f"1.{code}"
    if market in {"SZ", "BJ"}:
        return f"0.{code}"
    raise ValueError(f"unsupported market: {market}")


def tencent_symbol(security_id: str) -> str:
    market, code = security_id.split(".", 1)
    prefix = {"SH": "sh", "SZ": "sz", "BJ": "bj"}.get(market)
    if prefix is None:
        raise ValueError(f"unsupported market: {market}")
    return prefix + code


def parse_eastmoney_payload(payload: dict) -> dict[int, ExternalBar]:
    data = payload.get("data") or {}
    rows = data.get("klines") or []
    result = {}
    for line in rows:
        fields = line.split(",")
        if len(fields) < 5 or "-" in fields[:5]:
            continue
        trade_date = int(fields[0].replace("-", ""))
        result[trade_date] = ExternalBar(
            trade_date=trade_date,
            open=Decimal(fields[1]),
            close=Decimal(fields[2]),
            high=Decimal(fields[3]),
            low=Decimal(fields[4]),
        )
    return result


def parse_tencent_payload(payload: dict, security_id: str, *, raw_diagnostic: bool = False) -> dict[int, ExternalBar]:
    symbol = tencent_symbol(security_id)
    security = (payload.get("data") or {}).get(symbol) or {}
    rows = security.get("day" if raw_diagnostic else "qfqday") or []
    result = {}
    for fields in rows:
        if len(fields) < 5 or "-" in fields[:5]:
            continue
        trade_date = int(fields[0].replace("-", ""))
        result[trade_date] = ExternalBar(
            trade_date=trade_date,
            open=Decimal(fields[1]),
            close=Decimal(fields[2]),
            high=Decimal(fields[3]),
            low=Decimal(fields[4]),
        )
    return result


class SourceAudit:
    def __init__(self, name: str, endpoint: str, adjustment_mode: str, field_mapping: dict):
        self.value = {
            "source_name": name,
            "source_url_or_endpoint_family": endpoint,
            "request_method": "HTTPS_GET_PUBLIC_NO_LOGIN",
            "query_parameters": {},
            "adjustment_mode": adjustment_mode,
            "field_mapping": field_mapping,
            "usage": "EXTERNAL_REFERENCE_ONLY",
            "request_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "logical_query_count": 0,
            "rate_limit_events": 0,
            "first_success_time": None,
            "last_success_time": None,
            "errors": [],
        }

    def attempt(self) -> None:
        self.value["request_count"] += 1

    def logical_query(self) -> None:
        self.value["logical_query_count"] += 1

    def success(self) -> None:
        now = datetime.now().astimezone().isoformat()
        self.value["success_count"] += 1
        self.value["first_success_time"] = self.value["first_success_time"] or now
        self.value["last_success_time"] = now

    def failure(self, exc: Exception) -> None:
        self.value["failure_count"] += 1
        if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
            self.value["rate_limit_events"] += 1
        if len(self.value["errors"]) < 30:
            self.value["errors"].append(f"{type(exc).__name__}:{exc}")


class PublicQfqClients:
    """Rate-limited validation clients with no persistence or credentials."""

    def __init__(self, *, min_interval_seconds: float = 0.75, timeout_seconds: float = 20.0):
        self.min_interval_seconds = min_interval_seconds
        self.timeout_seconds = timeout_seconds
        self._last_request_at = 0.0
        self.eastmoney_disabled = False
        self.eastmoney_consecutive_failures = 0
        self.request_limit_per_provider = 200
        self._disabled_sources: set[str] = set()
        self.eastmoney = SourceAudit(
            "EASTMONEY",
            EASTMONEY_ENDPOINT,
            "QFQ; klt=101 daily, fqt=1 forward adjusted",
            {"f51": "date", "f52": "open", "f53": "close", "f54": "high", "f55": "low"},
        )
        self.eastmoney.value["query_parameters"] = {
            "klt": 101,
            "fqt": 1,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "lmt": 100000,
        }
        self.tencent = SourceAudit(
            "TENCENT",
            TENCENT_ENDPOINT,
            "QFQ; day interval, qfq forward adjusted",
            {"0": "date", "1": "open", "2": "close", "3": "high", "4": "low"},
        )
        self.tencent.value["query_parameters"] = {
            "interval": "day",
            "adjustment": "qfq",
            "max_rows_per_target_window": 40,
        }
        self.tencent_raw = SourceAudit(
            "TENCENT_RAW_DIAGNOSTIC",
            TENCENT_RAW_ENDPOINT,
            "UNADJUSTED_DAILY; diagnostic only for QFQ mismatches",
            {"0": "date", "1": "open", "2": "close", "3": "high", "4": "low"},
        )
        self.tencent_raw.value["query_parameters"] = {
            "interval": "day",
            "adjustment": "none",
            "use": "RAW_BASIS_DIAGNOSTIC_FOR_QFQ_MISMATCH_ONLY",
        }

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)

    def _json_get(self, url: str, audit: SourceAudit) -> dict:
        self._throttle()
        audit.attempt()
        self._last_request_at = time.monotonic()
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
                "Accept": "application/json,text/plain,*/*",
                "Connection": "close",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read())

    def _retry(self, operation: Callable[[], dict], audit: SourceAudit, attempts: int = 3) -> dict | None:
        name = audit.value["source_name"]
        if name in self._disabled_sources:
            return None
        audit.logical_query()
        last: Exception | None = None
        for attempt in range(attempts):
            provider_count = sum(
                source["request_count"] for source in self.audits()
                if source["source_name"].split("_")[0] == name.split("_")[0]
            )
            if provider_count >= self.request_limit_per_provider:
                self._disabled_sources.add(name)
                audit.value["stop_reason"] = "PROVIDER_REQUEST_BUDGET_EXHAUSTED"
                return None
            try:
                payload = operation()
                audit.success()
                return payload
            except Exception as exc:  # the audit records bounded network failures
                last = exc
                audit.failure(exc)
                if isinstance(exc, urllib.error.HTTPError) and exc.code in {400, 401, 403, 404, 429, 501}:
                    self._disabled_sources.add(name)
                    audit.value["stop_reason"] = f"HTTP_{exc.code}_CIRCUIT_OPEN"
                    return None
                if attempt + 1 < attempts:
                    time.sleep(1.5 * (attempt + 1))
        if last is not None:
            self._disabled_sources.add(name)
            audit.value["stop_reason"] = "THREE_ATTEMPTS_FAILED_CIRCUIT_OPEN"
            return None
        return None

    def fetch_eastmoney(self, security_id: str, begin: int, end: int) -> dict[int, ExternalBar] | None:
        if self.eastmoney_disabled:
            return None
        params = {
            "secid": eastmoney_secid(security_id),
            "klt": "101",
            "fqt": "1",
            "beg": str(begin),
            "end": str(end),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "lmt": "100000",
        }
        url = EASTMONEY_ENDPOINT + "?" + urllib.parse.urlencode(params)
        payload = self._retry(lambda: self._json_get(url, self.eastmoney), self.eastmoney)
        if payload is None or payload.get("rc") != 0 or not payload.get("data"):
            self.eastmoney_consecutive_failures += 1
            if self.eastmoney_consecutive_failures >= 1:
                # One logical query already consumed the allowed three attempts.
                self.eastmoney_disabled = True
            return None
        self.eastmoney_consecutive_failures = 0
        return parse_eastmoney_payload(payload)

    def fetch_tencent_window(self, security_id: str, target_date: int) -> dict[int, ExternalBar] | None:
        symbol = tencent_symbol(security_id)
        text = str(target_date)
        year, month, day = int(text[:4]), int(text[4:6]), int(text[6:])
        # A bounded calendar window handles weekends and nearby suspension days.
        from datetime import date, timedelta

        center = date(year, month, day)
        begin = (center - timedelta(days=12)).isoformat()
        end = (center + timedelta(days=12)).isoformat()
        params = {"param": f"{symbol},day,{begin},{end},40,qfq"}
        url = TENCENT_ENDPOINT + "?" + urllib.parse.urlencode(params)
        payload = self._retry(lambda: self._json_get(url, self.tencent), self.tencent)
        if payload is None or payload.get("code") != 0:
            return None
        return parse_tencent_payload(payload, security_id)

    def fetch_tencent_raw_window(self, security_id: str, target_date: int) -> dict[int, ExternalBar] | None:
        symbol = tencent_symbol(security_id)
        text = str(target_date)
        year, month, day = int(text[:4]), int(text[4:6]), int(text[6:])
        from datetime import date, timedelta

        center = date(year, month, day)
        begin = (center - timedelta(days=12)).isoformat()
        end = (center + timedelta(days=12)).isoformat()
        params = {"param": f"{symbol},day,{begin},{end},40"}
        url = TENCENT_RAW_ENDPOINT + "?" + urllib.parse.urlencode(params)
        payload = self._retry(lambda: self._json_get(url, self.tencent_raw), self.tencent_raw)
        if payload is None or payload.get("code") != 0:
            return None
        return parse_tencent_payload(payload, security_id, raw_diagnostic=True)

    def audits(self) -> list[dict]:
        return [self.eastmoney.value, self.tencent.value, self.tencent_raw.value]


def compare_ohlc(local: dict, external: ExternalBar | None, tolerance: Decimal = TOLERANCE) -> dict:
    if external is None:
        return {
            "external_open": None,
            "external_high": None,
            "external_low": None,
            "external_close": None,
            "diff_open": None,
            "diff_high": None,
            "diff_low": None,
            "diff_close": None,
            "within_tolerance": False,
            "status": "UNVERIFIABLE_EXTERNAL",
        }
    if external.trade_date != local.get("date", external.trade_date) or any(
        not getattr(external, field).is_finite() for field in ("open", "high", "low", "close")
    ):
        return compare_ohlc(local, None, tolerance)
    result = {}
    within = True
    for field in ("open", "high", "low", "close"):
        local_value = Decimal(str(local[f"local_{field}"]))
        external_value = getattr(external, field)
        diff = local_value - external_value
        result[f"external_{field}"] = float(external_value)
        result[f"diff_{field}"] = float(diff)
        within = within and abs(diff) <= tolerance
    result["within_tolerance"] = within
    result["status"] = "LOCAL_MATCHES_EXTERNAL" if within else "LOCAL_MISMATCH_REQUIRES_REVIEW"
    return result


def decide_phase0_2a_gate(
    *,
    fixed_passed: int,
    fixed_failed: int,
    fixed_unverifiable: int,
    security_count: int,
    verified_points: int,
    match_ratio: float,
    complex_types_pass: bool,
    systematic_mismatch: bool,
    external_disagreement_count: int,
) -> str:
    if fixed_failed or systematic_mismatch:
        return "BLOCKED_FOR_FORMAL_ADJUSTMENT"
    if (
        fixed_passed == 5
        and fixed_failed == 0
        and fixed_unverifiable == 0
        and security_count >= 20
        and verified_points >= 50
        and match_ratio >= 0.95
        and complex_types_pass
        and not systematic_mismatch
        and external_disagreement_count == 0
    ):
        return "FULL_PASS"
    return "DEGRADED_PASS"
