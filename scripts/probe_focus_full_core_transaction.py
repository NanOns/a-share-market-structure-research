"""Rollback-only initial Focus core transaction rehearsal."""
from __future__ import annotations

import argparse
from datetime import date

from scripts.run_focus_initial_core_transaction import InjectedCoreFailure, main as run_initial_core


def main(*, inject_after_observations: int | None = None,
         commit: bool = False,
         expected_trade_date: date | None = None,
         expected_manifest_digest: str | None = None) -> int:
    return run_initial_core(inject_after_observations=inject_after_observations,
                            commit=commit, expected_trade_date=expected_trade_date,
                            expected_manifest_digest=expected_manifest_digest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inject-after-observations", type=int)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--expected-trade-date")
    parser.add_argument("--expected-manifest-digest")
    args = parser.parse_args()
    raise SystemExit(main(
        inject_after_observations=args.inject_after_observations,
        commit=args.commit,
        expected_trade_date=(date.fromisoformat(args.expected_trade_date)
                             if args.expected_trade_date else None),
        expected_manifest_digest=args.expected_manifest_digest))
