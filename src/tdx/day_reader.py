from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import math
import struct


DAY_RECORD_LENGTH = 32
DAY_STRUCT = struct.Struct("<IIIIIfII")
PRICE_DIVISOR = 100.0


@dataclass(frozen=True)
class DayRecord:
    trade_date: int
    open: float
    high: float
    low: float
    close: float
    amount: float
    volume: int
    reserved: int


def decode_record(raw: bytes) -> DayRecord:
    if len(raw) != DAY_RECORD_LENGTH:
        raise ValueError(f"expected {DAY_RECORD_LENGTH} bytes, got {len(raw)}")
    trade_date, open_, high, low, close, amount, volume, reserved = DAY_STRUCT.unpack(raw)
    return DayRecord(
        trade_date=trade_date,
        open=open_ / PRICE_DIVISOR,
        high=high / PRICE_DIVISOR,
        low=low / PRICE_DIVISOR,
        close=close / PRICE_DIVISOR,
        amount=float(amount),
        volume=volume,
        reserved=reserved,
    )


def read_edge_records(path: Path) -> tuple[DayRecord, DayRecord]:
    size = path.stat().st_size
    if size == 0 or size % DAY_RECORD_LENGTH:
        raise ValueError(f"invalid .day file length: {size}")
    with path.open("rb") as handle:
        first = decode_record(handle.read(DAY_RECORD_LENGTH))
        handle.seek(-DAY_RECORD_LENGTH, 2)
        last = decode_record(handle.read(DAY_RECORD_LENGTH))
    return first, last


def _valid_yyyymmdd(value: int) -> bool:
    try:
        date(value // 10000, (value // 100) % 100, value % 100)
        return True
    except ValueError:
        return False


def _validate_with_struct(raw: bytes) -> dict:
    previous_date = None
    first_date = None
    last_date = None
    duplicate_dates = 0
    non_increasing_dates = 0
    invalid_dates = 0
    invalid_ohlc = 0
    invalid_amount = 0
    zero_price_records = 0
    turnover_price_check_count = 0
    turnover_price_plausible_count = 0

    for record in DAY_STRUCT.iter_unpack(raw):
        trade_date, open_, high, low, close, amount, volume, _reserved = record
        if first_date is None:
            first_date = trade_date
        last_date = trade_date
        if not _valid_yyyymmdd(trade_date):
            invalid_dates += 1
        if previous_date is not None:
            if trade_date == previous_date:
                duplicate_dates += 1
            elif trade_date < previous_date:
                non_increasing_dates += 1
        previous_date = trade_date
        if open_ == high == low == close == 0:
            zero_price_records += 1
        elif high < max(open_, low, close) or low > min(open_, high, close):
            invalid_ohlc += 1
        if not math.isfinite(amount) or amount < 0:
            invalid_amount += 1
        if amount > 0 and volume > 0 and low > 0 and high > 0:
            turnover_price_check_count += 1
            implied_price = amount / volume
            if (low / PRICE_DIVISOR) * 0.95 <= implied_price <= (high / PRICE_DIVISOR) * 1.05:
                turnover_price_plausible_count += 1

    return {
        "first_date": first_date,
        "last_date": last_date,
        "duplicate_dates": duplicate_dates,
        "non_increasing_dates": non_increasing_dates,
        "invalid_dates": invalid_dates,
        "invalid_ohlc": invalid_ohlc,
        "invalid_amount": invalid_amount,
        "zero_price_records": zero_price_records,
        "turnover_price_check_count": turnover_price_check_count,
        "turnover_price_plausible_count": turnover_price_plausible_count,
    }


def _validate_with_numpy(raw: bytes) -> dict:
    import numpy as np

    dtype = np.dtype(
        [
            ("date", "<u4"),
            ("open", "<u4"),
            ("high", "<u4"),
            ("low", "<u4"),
            ("close", "<u4"),
            ("amount", "<f4"),
            ("volume", "<u4"),
            ("reserved", "<u4"),
        ]
    )
    data = np.frombuffer(raw, dtype=dtype)
    dates = data["date"].astype(np.int64)
    years = dates // 10000
    months = (dates // 100) % 100
    days = dates % 100
    leap = ((years % 4 == 0) & (years % 100 != 0)) | (years % 400 == 0)
    month_days = np.array([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
    safe_months = np.clip(months, 0, 12)
    max_days = month_days[safe_months] + ((months == 2) & leap)
    valid_dates = (
        (years >= 1990)
        & (years <= 2100)
        & (months >= 1)
        & (months <= 12)
        & (days >= 1)
        & (days <= max_days)
    )
    diffs = np.diff(dates)
    open_ = data["open"]
    high = data["high"]
    low = data["low"]
    close = data["close"]
    all_zero = (open_ == 0) & (high == 0) & (low == 0) & (close == 0)
    invalid_ohlc = (~all_zero) & (
        (high < open_) | (high < low) | (high < close) | (low > open_) | (low > high) | (low > close)
    )
    amount = data["amount"]
    invalid_amount = (~np.isfinite(amount)) | (amount < 0)
    volume = data["volume"].astype(np.float64)
    turnover_mask = (amount > 0) & (volume > 0) & (low > 0) & (high > 0)
    implied_price = np.zeros(len(data), dtype=np.float64)
    np.divide(amount, volume, out=implied_price, where=turnover_mask)
    turnover_plausible = turnover_mask & (
        (implied_price >= (low.astype(np.float64) / PRICE_DIVISOR) * 0.95)
        & (implied_price <= (high.astype(np.float64) / PRICE_DIVISOR) * 1.05)
    )
    return {
        "first_date": int(dates[0]),
        "last_date": int(dates[-1]),
        "duplicate_dates": int(np.count_nonzero(diffs == 0)),
        "non_increasing_dates": int(np.count_nonzero(diffs < 0)),
        "invalid_dates": int(np.count_nonzero(~valid_dates)),
        "invalid_ohlc": int(np.count_nonzero(invalid_ohlc)),
        "invalid_amount": int(np.count_nonzero(invalid_amount)),
        "zero_price_records": int(np.count_nonzero(all_zero)),
        "turnover_price_check_count": int(np.count_nonzero(turnover_mask)),
        "turnover_price_plausible_count": int(np.count_nonzero(turnover_plausible)),
    }


def validate_day_file(path: Path, market: str) -> dict:
    size = path.stat().st_size
    result = {
        "path": str(path),
        "market": market.upper(),
        "code": path.stem[2:],
        "security_id": f"{market.upper()}.{path.stem[2:]}",
        "size": size,
        "record_count": size // DAY_RECORD_LENGTH,
        "valid": False,
        "errors": [],
    }
    if size == 0:
        result["errors"].append("EMPTY_FILE")
        return result
    if size % DAY_RECORD_LENGTH:
        result["errors"].append("INCOMPLETE_TAIL_RECORD")
        return result
    raw = path.read_bytes()
    try:
        try:
            details = _validate_with_numpy(raw)
        except ImportError:
            details = _validate_with_struct(raw)
    except Exception as exc:  # keep an audit trail for corrupt sources
        result["errors"].append(f"PARSE_ERROR:{type(exc).__name__}:{exc}")
        return result
    result.update(details)
    for key, code in (
        ("invalid_dates", "INVALID_DATE"),
        ("duplicate_dates", "DUPLICATE_DATE"),
        ("non_increasing_dates", "NON_INCREASING_DATE"),
        ("invalid_ohlc", "INVALID_OHLC"),
        ("invalid_amount", "INVALID_AMOUNT"),
    ):
        if result[key]:
            result["errors"].append(f"{code}:{result[key]}")
    result["valid"] = not result["errors"]
    return result


def record_as_dict(record: DayRecord) -> dict:
    return asdict(record)
