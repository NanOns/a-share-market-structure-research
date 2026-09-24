"""Read-only full accepted-day Focus source and shared-fact rehearsal."""
from __future__ import annotations

from src.focus_tracker.daily_manifest import build_daily_manifest


def build_probe_manifest(*, evaluation_basis="HISTORICAL_RECONSTRUCTED",
                         expected_trade_date=None):
    return build_daily_manifest(evaluation_basis=evaluation_basis,
                                expected_trade_date=expected_trade_date)


def main() -> int:
    _, summary = build_probe_manifest()
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
