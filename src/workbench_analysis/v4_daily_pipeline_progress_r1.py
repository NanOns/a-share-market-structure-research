"""Versioned, low-overhead timing/checkpoint decorator for the live V4 executor."""
from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from typing import Any, Callable, Mapping

CONTRACT_ID = "V4_DAILY_PIPELINE_PROGRESS_R1"
CONTRACT_VERSION = "1.0.0"


class InstrumentedProgress:
    """Preserve the caller callback while attaching stage timing and row counts.

    Timing is wall time between adjacent existing executor checkpoints, not a
    claim that the named checkpoint's operation alone consumed that duration.
    Each event remains small and safe for the existing progress store.
    """

    _v4_pipeline_instrumented = True

    def __init__(self, callback: Callable[..., Any], *, clock: Callable[[], float] = monotonic,
                 utc_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.callback = callback
        self.clock = clock
        self.utc_now = utc_now
        self.previous_at: float | None = None
        self.previous_stage: str | None = None
        self.stage_started: dict[str, float] = {}
        self.stage_started_utc: dict[str, str] = {}
        self.counts: dict[str, int] = {}

    def __call__(self, trade_date: str, stage: str, detail: Any = None) -> None:
        now = self.clock()
        if stage not in self.stage_started:
            self.stage_started[stage] = now
            self.stage_started_utc[stage] = self.utc_now().astimezone(timezone.utc).isoformat()
        started = self.stage_started[stage]
        payload = dict(detail) if isinstance(detail, Mapping) else {"detail": detail}
        payload.update({
            "progress_contract_id": CONTRACT_ID,
            "progress_contract_version": CONTRACT_VERSION,
            "stage_started_at": self.stage_started_utc[stage],
            "stage_elapsed_ms": round(max(0.0, now - started) * 1000, 3),
            "since_previous_checkpoint_ms": (
                round(max(0.0, now - self.previous_at) * 1000, 3)
                if self.previous_at is not None else None
            ),
            "previous_checkpoint_stage": self.previous_stage,
            "duration_scope": "CHECKPOINT_INTERVAL_NOT_ISOLATED_STAGE_BENCHMARK",
        })
        for key in ("row_count", "security_count", "processed_count", "total_count", "cache_hits"):
            value = payload.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                self.counts[key] = value
        self.previous_at = now
        self.previous_stage = stage
        self.callback(trade_date, stage, payload)


def instrument_progress(callback: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(callback, "_v4_pipeline_instrumented", False):
        return callback
    return InstrumentedProgress(callback)
