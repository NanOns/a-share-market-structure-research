"""Eastmoney hot-rank decoder and normalizer for private research mode.

The public page serves an AES-CBC encoded JavaScript variable. Decoding is
limited to the declared endpoint and does not enable production publication.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from typing import Callable
from urllib.parse import urlencode

from .base import FetchResult, OnlineFetchPolicy, bounded_get


EASTMONEY_HOT_RANK_SOURCE_ID = "EASTMONEY_HOT_RANK"
EASTMONEY_HOT_RANK_PAGE = "https://guba.eastmoney.com/rank/"
EASTMONEY_HOT_RANK_HOST = "https://gbcdn.dfcfw.com/rank/popularityList.js"
DECODER_VERSION = "EASTMONEY_AES_CBC_NODE_CRYPTO_V1"

_NODE_DECODER = r"""
const crypto=require('crypto');
let body='';
process.stdin.setEncoding('utf8');
process.stdin.on('data', x => body += x);
process.stdin.on('end', () => {
  const m=body.match(/popularityList='([^']+)'/);
  if(!m) throw new Error('POPULARITY_LIST_VARIABLE_MISSING');
  const ciphertext=Buffer.from(m[1], 'base64');
  const key=Buffer.from(crypto.createHash('md5').update('getUtilsFromFile').digest('hex'));
  const iv=Buffer.from('getClassFromFile');
  const decipher=crypto.createDecipheriv('aes-256-cbc', key, iv);
  const plain=Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString('utf8');
  process.stdout.write(plain);
});
"""


def decode_eastmoney_payload(body: bytes, *, node_runner: Callable[..., object] = subprocess.run) -> list[dict]:
    try:
        completed = node_runner(
            ["node", "-e", _NODE_DECODER],
            input=body.decode("utf-8"),
            text=True,
            capture_output=True,
            timeout=5,
            check=True,
        )
    except Exception as exc:  # pragma: no cover - subprocess-specific failures
        raise ValueError("EASTMONEY_DECODE_FAILED") from exc
    try:
        decoded = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("EASTMONEY_DECODED_SCHEMA_INVALID") from exc
    if not isinstance(decoded, list) or not decoded:
        raise ValueError("EASTMONEY_EMPTY_RANK_LIST")
    return decoded


def _security_id(row: dict) -> str | None:
    history = row.get("history") or []
    if not isinstance(history, list):
        return None
    current_rank = str(row.get("rankNumber", ""))
    candidates = [
        item
        for item in reversed(history)
        if isinstance(item, dict)
        and re.fullmatch(r"(?:SH|SZ)\d{6}", str(item.get("SRCSECURITYCODE", "")))
    ]
    for item in candidates:
        if str(item.get("RANK", "")) == current_rank:
            source_code = str(item["SRCSECURITYCODE"])
            return f"{source_code[:2]}.{source_code[2:]}"
    return None


def fetch_eastmoney_hot_rank(
    policy: OnlineFetchPolicy | None = None,
    *,
    page: int = 1,
    sort: int = 0,
    market_type: int = 0,
    fetcher: Callable[..., FetchResult] = bounded_get,
    decoder: Callable[[bytes], list[dict]] = decode_eastmoney_payload,
) -> tuple[FetchResult, dict]:
    policy = policy or OnlineFetchPolicy()
    if page < 1 or sort not in (0, 1) or market_type not in (0, 1, 2):
        raise ValueError("INVALID_EASTMONEY_QUERY")
    url = EASTMONEY_HOT_RANK_HOST + "?" + urlencode({"type": market_type, "sort": sort, "page": page, "m": datetime.now().minute})
    result = fetcher(url, policy, referer=EASTMONEY_HOT_RANK_PAGE)
    if result.status_code != 200:
        raise ValueError(f"HTTP_STATUS:{result.status_code}")
    rows = decoder(result.body)
    required = {"code", "rankNumber", "changeNumber", "exactTime"}
    if any(not isinstance(row, dict) or not required.issubset(row) for row in rows):
        raise ValueError("EASTMONEY_RANK_SCHEMA_DRIFT")
    source_times = sorted({str(row["exactTime"]) for row in rows if row.get("exactTime")})
    source_as_of = source_times[0] if len(source_times) == 1 else None
    normalized = []
    for index, row in enumerate(rows, start=1):
        normalized.append(
            {
                "source_code": str(row["code"]),
                "security_id": _security_id(row),
                "platform_rank": int(row["rankNumber"]),
                "rank_change": row.get("changeNumber"),
                "security_name": None,
                "source_row_order": index,
                "source_exact_time": row.get("exactTime"),
            }
        )
    return result, {
        "source_id": EASTMONEY_HOT_RANK_SOURCE_ID,
        "dataset": "HOT_RANKINGS",
        "list_type": "A_STOCK_HOT_RANK",
        "page": page,
        "sort": sort,
        "market_type": market_type,
        "capability_status": "PERSONAL_RESEARCH_ONLY",
        "decoder_version": DECODER_VERSION,
        "source_as_of": source_as_of,
        "time_semantics": "SOURCE_EXACT_TIME" if source_as_of else "MULTIPLE_OR_MISSING_SOURCE_TIMES",
        "rows": normalized,
    }
