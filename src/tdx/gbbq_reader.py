from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from hashlib import sha256
import math
from pathlib import Path
import re
import struct
from typing import Iterator

from ._gbbq_key import GBBQ_KEY_BYTES


GBBQ_HEADER = struct.Struct("<I")
GBBQ_RECORD_LENGTH = 29
GBBQ_MAP_RECORD_LENGTH = 15
FLOAT4 = struct.Struct("<ffff")
UINT32 = struct.Struct("<I")
MARKET_BY_BYTE = {0: "SZ", 1: "SH", 2: "BJ"}
KNOWN_CATEGORIES = frozenset(range(1, 15))
CATEGORY_NAMES = {
    1: "XRXD",
    2: "LISTED_BONUS_OR_RIGHTS_SHARES",
    3: "NON_TRADABLE_SHARES_LISTED",
    4: "UNKNOWN_EQUITY_CHANGE",
    5: "EQUITY_CHANGE",
    6: "PRIVATE_PLACEMENT",
    7: "SHARE_REPURCHASE",
    8: "PRIVATE_PLACEMENT_SHARES_LISTED",
    9: "TRANSFERRED_RIGHTS_SHARES_LISTED",
    10: "CONVERTIBLE_BOND_LISTED",
    11: "SHARE_CONSOLIDATION_OR_SPLIT",
    12: "NON_TRADABLE_SHARE_CONSOLIDATION",
    13: "CALL_WARRANT_DISTRIBUTION",
    14: "PUT_WARRANT_DISTRIBUTION",
}
DECODER_VERSION = "tdx-local-gbbq-v0.2"
REFERENCE_COMMIT = "7ec113c38bf62e8d04aabd8be04df09b9c94ac65"


@dataclass(frozen=True)
class GbbqMapEntry:
    code: str
    token: str
    raw_text: str


@dataclass(frozen=True)
class GbbqRecord:
    security_id: str
    raw_code: str
    event_date: int
    category: int
    c1: float
    c2: float
    c3: float
    c4: float
    source: str
    source_record_index: int
    market_byte: int

    @property
    def category_name(self) -> str:
        return CATEGORY_NAMES.get(self.category, "UNKNOWN_CATEGORY")

    @property
    def is_xrxd(self) -> bool:
        return self.category == 1

    def xrxd_fields(self) -> dict[str, float]:
        if not self.is_xrxd:
            raise ValueError("explicit XRXD fields are defined only for category=1")
        return {
            "cash_dividend_per_10": self.c1,
            "rights_price": self.c2,
            "bonus_transfer_per_10": self.c3,
            "rights_ratio_per_10": self.c4,
        }

    def as_dict(self, *, explicit_xrxd: bool = True) -> dict:
        value = asdict(self)
        value["category_name"] = self.category_name
        if explicit_xrxd and self.is_xrxd:
            value.update(self.xrxd_fields())
        return value


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_map(path: Path) -> tuple[list[GbbqMapEntry], dict]:
    raw = path.read_bytes()
    errors: list[str] = []
    if len(raw) % GBBQ_MAP_RECORD_LENGTH:
        errors.append("MAP_FILE_SIZE_NOT_DIVISIBLE_BY_15")
    entries: list[GbbqMapEntry] = []
    limit = len(raw) - (len(raw) % GBBQ_MAP_RECORD_LENGTH)
    for offset in range(0, limit, GBBQ_MAP_RECORD_LENGTH):
        record = raw[offset : offset + GBBQ_MAP_RECORD_LENGTH]
        text = record.decode("ascii", errors="replace")
        normalized = text.replace("\r", "").replace("\n", "").rstrip()
        code = normalized[:6]
        token = normalized[6:10]
        if not (code.isdigit() and len(code) == 6 and token.isdigit() and len(token) == 4):
            errors.append(f"INVALID_MAP_RECORD_AT:{offset}")
            continue
        entries.append(GbbqMapEntry(code=code, token=token, raw_text=text))
    return entries, {
        "record_length": GBBQ_MAP_RECORD_LENGTH,
        "record_count": len(entries),
        "parse_error_count": len(errors),
        "errors": errors[:50],
        "token_distribution": dict(Counter(entry.token for entry in entries).most_common(20)),
    }


_KEY_WORDS = struct.unpack(f"<{len(GBBQ_KEY_BYTES) // 4}I", GBBQ_KEY_BYTES)


def decrypt_block(encrypted: bytes) -> bytes:
    """Decrypt one 8-byte GBBQ block using the audited TDX key schedule."""
    if len(encrypted) != 8:
        raise ValueError(f"expected 8 encrypted bytes, got {len(encrypted)}")
    words = _KEY_WORDS
    left, right = struct.unpack("<II", encrypted)
    current = words[17] ^ left
    previous = right
    for round_index in range(16, 0, -1):
        value = words[274 + ((current >> 16) & 0xFF)]
        value = (value + words[18 + ((current >> 24) & 0xFF)]) & 0xFFFFFFFF
        value ^= words[530 + ((current >> 8) & 0xFF)]
        value = (value + words[786 + (current & 0xFF)]) & 0xFFFFFFFF
        value ^= words[round_index]
        current, previous = (previous ^ value) & 0xFFFFFFFF, current
    previous ^= words[0]
    return struct.pack("<II", previous, current)


def _valid_date(value: int) -> bool:
    try:
        parsed = date(value // 10000, (value // 100) % 100, value % 100)
    except ValueError:
        return False
    return 1990 <= parsed.year <= 2100


def decode_record(encrypted_record: bytes, *, source: str, record_index: int) -> GbbqRecord:
    if len(encrypted_record) != GBBQ_RECORD_LENGTH:
        raise ValueError(f"expected a 29-byte GBBQ record, got {len(encrypted_record)}")
    clear = (
        decrypt_block(encrypted_record[0:8])
        + decrypt_block(encrypted_record[8:16])
        + decrypt_block(encrypted_record[16:24])
        + encrypted_record[24:29]
    )
    market_byte = clear[0]
    raw_code = clear[1:8].rstrip(b"\x00").decode("ascii", errors="replace")
    market = MARKET_BY_BYTE.get(market_byte, f"UNKNOWN_{market_byte}")
    c1, c2, c3, c4 = FLOAT4.unpack_from(clear, 13)
    return GbbqRecord(
        security_id=f"{market}.{raw_code}",
        raw_code=raw_code,
        event_date=UINT32.unpack_from(clear, 8)[0],
        category=clear[12],
        c1=c1,
        c2=c2,
        c3=c3,
        c4=c4,
        source=source,
        source_record_index=record_index,
        market_byte=market_byte,
    )


def decode_gbbq_bytes(content: bytes, *, source: str = "<bytes>") -> list[GbbqRecord]:
    if len(content) < GBBQ_HEADER.size:
        raise ValueError("gbbq is shorter than its 4-byte header")
    declared_count = GBBQ_HEADER.unpack_from(content, 0)[0]
    expected_size = GBBQ_HEADER.size + declared_count * GBBQ_RECORD_LENGTH
    if len(content) != expected_size:
        raise ValueError(
            f"gbbq size mismatch: declared={declared_count}, expected={expected_size}, actual={len(content)}"
        )
    payload = memoryview(content)[GBBQ_HEADER.size :]
    return [
        decode_record(
            bytes(payload[index * GBBQ_RECORD_LENGTH : (index + 1) * GBBQ_RECORD_LENGTH]),
            source=source,
            record_index=index,
        )
        for index in range(declared_count)
    ]


def read_gbbq(path: Path) -> list[GbbqRecord]:
    return decode_gbbq_bytes(path.read_bytes(), source=str(path))


def iter_xrxd(records: list[GbbqRecord], security_id: str | None = None) -> Iterator[GbbqRecord]:
    for record in records:
        if record.is_xrxd and (security_id is None or record.security_id == security_id):
            yield record


def audit_gbbq(
    path: Path, map_path: Path, *, decoded_records: list[GbbqRecord] | None = None
) -> dict:
    raw = path.read_bytes()
    map_entries, map_audit = read_map(map_path)
    declared_count = GBBQ_HEADER.unpack_from(raw, 0)[0] if len(raw) >= 4 else 0
    expected_size = GBBQ_HEADER.size + declared_count * GBBQ_RECORD_LENGTH
    errors: list[str] = []
    warnings: list[str] = []
    if len(raw) != expected_size:
        errors.append(f"FILE_SIZE_MISMATCH:{len(raw)}!={expected_size}")
        records: list[GbbqRecord] = []
    else:
        records = decoded_records if decoded_records is not None else decode_gbbq_bytes(raw, source=str(path))
        if len(records) != declared_count:
            errors.append(f"DECODED_RECORD_COUNT_MISMATCH:{len(records)}!={declared_count}")

    valid_code = [r for r in records if re.fullmatch(r"\d{6}", r.raw_code)]
    valid_dates = [r for r in records if _valid_date(r.event_date)]
    finite_records = [r for r in records if all(math.isfinite(x) for x in (r.c1, r.c2, r.c3, r.c4))]
    invalid_markets = [r for r in records if r.market_byte not in MARKET_BY_BYTE]
    invalid_codes = len(records) - len(valid_code)
    invalid_dates = len(records) - len(valid_dates)
    invalid_parameters = len(records) - len(finite_records)
    categories = Counter(r.category for r in records)
    markets = Counter(MARKET_BY_BYTE.get(r.market_byte, str(r.market_byte)) for r in records)
    unknown_categories = sum(count for category, count in categories.items() if category not in KNOWN_CATEGORIES)
    xrxd_count = categories.get(1, 0)
    xrxd_records = [r for r in records if r.category == 1]
    invalid_xrxd_semantics = [
        r
        for r in xrxd_records
        if any(value < 0 for value in (r.c1, r.c2, r.c3, r.c4)) or 10 + r.c3 + r.c4 <= 0
    ]
    xrxd_parameter_stats = {
        name: {
            "min": min((getattr(r, name) for r in xrxd_records), default=None),
            "max": max((getattr(r, name) for r in xrxd_records), default=None),
        }
        for name in ("c1", "c2", "c3", "c4")
    }
    decode_ok = (
        len(records) == declared_count
        and not invalid_codes
        and not invalid_dates
        and not invalid_parameters
        and not invalid_markets
        and not invalid_xrxd_semantics
    )
    if invalid_codes:
        errors.append(f"INVALID_CODE:{invalid_codes}")
    if invalid_dates:
        errors.append(f"INVALID_DATE:{invalid_dates}")
    if invalid_parameters:
        errors.append(f"INVALID_FLOAT:{invalid_parameters}")
    if invalid_markets:
        errors.append(f"INVALID_MARKET:{len(invalid_markets)}")
    if unknown_categories:
        warnings.append(f"UNKNOWN_CATEGORY_RETAINED:{unknown_categories}")
    if invalid_xrxd_semantics:
        errors.append(f"INVALID_XRXD_SEMANTICS:{len(invalid_xrxd_semantics)}")

    stat = path.stat()
    map_stat = map_path.stat()
    sample_records = [record.as_dict() for record in records[:10]]
    return {
        "schema_version": "gbbq-decode-audit-v0.2",
        "gbbq_file": str(path),
        "gbbq_map_file": str(map_path),
        "gbbq_path": str(path),
        "gbbq_map_path": str(map_path),
        "file_size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": file_sha256(path),
        "map_file_size": map_stat.st_size,
        "map_mtime_ns": map_stat.st_mtime_ns,
        "map_sha256": file_sha256(map_path),
        "declared_count": declared_count,
        "declared_record_count": declared_count,
        "expected_file_size": expected_size,
        "parsed_count": len(records),
        "record_count": len(records),
        "record_layout": {
            "header": "little-endian uint32 record count",
            "header_length": GBBQ_HEADER.size,
            "record_length": GBBQ_RECORD_LENGTH,
            "record_body": "3 x encrypted 8-byte blocks + 5 plaintext bytes",
            "decoded_fields": "market byte, 7-byte NUL-terminated code, uint32 YYYYMMDD, uint8 category, 4 x float32",
        },
        "map_entry_count": len(map_entries),
        "map_audit": map_audit,
        "valid_code_count": len(valid_code),
        "invalid_code_count": invalid_codes,
        "valid_date_count": len(valid_dates),
        "invalid_date_count": invalid_dates,
        "market_distribution": dict(sorted(markets.items())),
        "invalid_market_count": len(invalid_markets),
        "category_distribution": {str(k): v for k, v in sorted(categories.items())},
        "unknown_category_count": unknown_categories,
        "unknown_category_ratio": unknown_categories / len(records) if records else 0.0,
        "xrxr_event_count": xrxd_count,
        "xrxd_event_count": xrxd_count,
        "xrxd_parameter_stats": xrxd_parameter_stats,
        "invalid_xrxd_semantics_count": len(invalid_xrxd_semantics),
        "finite_parameter_count": len(finite_records),
        "finite_parameter_value_count": len(finite_records) * 4,
        "invalid_parameter_count": invalid_parameters,
        "decoder_version": DECODER_VERSION,
        "reference_commit": REFERENCE_COMMIT,
        "sample_records": sample_records,
        "gbbq_parse_status": "PASS" if decode_ok else "FAIL",
        "semantic_status": (
            "PASS_FOR_CATEGORY_1_UNKNOWN_CATEGORIES_RETAINED"
            if decode_ok and unknown_categories
            else "PASS" if decode_ok else "FAIL"
        ),
        "errors": errors + map_audit["errors"],
        "warnings": warnings,
        "evidence": [
            f"actual_file_size == 4 + declared_count * 29: {stat.st_size == expected_size}",
            f"parsed_count == declared_count: {len(records) == declared_count}",
            f"all decoded codes are six digits: {invalid_codes == 0}",
            f"all decoded dates are valid YYYYMMDD: {invalid_dates == 0}",
            f"all decoded parameters are finite float32: {invalid_parameters == 0}",
        ],
    }
