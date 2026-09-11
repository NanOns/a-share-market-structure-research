"""Shared bounded HTTP and batch identity primitives for M14."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib.request import Request, urlopen


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class OnlineFetchPolicy:
    timeout_seconds: float = 15.0
    max_response_bytes: int = 1_000_000
    retries: int = 0
    cache_ttl_seconds: int = 900
    personal_research_only: bool = True

    def validate(self) -> None:
        if self.timeout_seconds <= 0 or self.timeout_seconds > 30:
            raise ValueError("INVALID_TIMEOUT_BUDGET")
        if self.max_response_bytes <= 0 or self.max_response_bytes > 2_000_000:
            raise ValueError("INVALID_RESPONSE_BUDGET")
        if self.retries != 0:
            raise ValueError("M14_02_RETRIES_MUST_BE_ZERO")
        if not self.personal_research_only:
            raise ValueError("PERSONAL_RESEARCH_ONLY_REQUIRED")


@dataclass(frozen=True)
class FetchResult:
    requested_at_utc: str
    received_at_utc: str
    status_code: int
    content_type: str
    body: bytes
    url: str

    @property
    def raw_sha256(self) -> str:
        return sha256_bytes(self.body)

    @property
    def byte_count(self) -> int:
        return len(self.body)


def bounded_get(
    url: str,
    policy: OnlineFetchPolicy,
    *,
    referer: str | None = None,
    opener: Callable[..., object] = urlopen,
) -> FetchResult:
    policy.validate()
    requested = datetime.now(timezone.utc)
    headers = {"User-Agent": "M14-02-personal-research/1.0", "Accept": "application/json"}
    if referer:
        headers["Referer"] = referer
    request = Request(url, headers=headers, method="GET")
    with opener(request, timeout=policy.timeout_seconds) as response:
        body = response.read(policy.max_response_bytes + 1)
        if len(body) > policy.max_response_bytes:
            raise ValueError("RESPONSE_SIZE_LIMIT_EXCEEDED")
        received = datetime.now(timezone.utc)
        return FetchResult(
            requested_at_utc=requested.isoformat(),
            received_at_utc=received.isoformat(),
            status_code=int(response.status),
            content_type=response.headers.get("Content-Type", ""),
            body=body,
            url=url,
        )


def json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
