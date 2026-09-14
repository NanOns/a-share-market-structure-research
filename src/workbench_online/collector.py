"""Retired M14 hot-rank capture entry points.

Hot rank is request-time only. Historical capture commands must never persist
raw payloads, normalized rows, or batches, even when called directly.
"""

from __future__ import annotations

from pathlib import Path

from .base import OnlineFetchPolicy


class HotRankCaptureDisabled(RuntimeError):
    pass


def collect_ths_hot_rank(output_root: str | Path, policy: OnlineFetchPolicy | None = None) -> dict:
    raise HotRankCaptureDisabled("HOT_RANK_CAPTURE_DISABLED_REQUEST_TIME_ONLY")


def collect_eastmoney_hot_rank(output_root: str | Path, policy: OnlineFetchPolicy | None = None, *, page: int = 1) -> dict:
    raise HotRankCaptureDisabled("HOT_RANK_CAPTURE_DISABLED_REQUEST_TIME_ONLY")
