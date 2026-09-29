"""Freeze deterministic V4-05 sample selection before replay evaluation."""

from __future__ import annotations

from datetime import date
import gzip
import json
import os
from pathlib import Path
import tempfile

import duckdb

from src.v4.replay_inputs import resolve


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_05/V4_05_REPLAY_DATE_MATRIX_R1.json"


def main() -> None:
    inputs, authority = resolve(ROOT)
    daily = str(inputs["daily"].path).replace("'", "''")
    db = duckdb.connect()
    cutoff = authority["source_cutoff"]
    dates = [f"{r[0]:08d}" for r in db.execute(
        f"SELECT DISTINCT trade_date FROM read_parquet('{daily}') WHERE trade_date <= ? ORDER BY trade_date",
        [int(cutoff.replace("-", ""))],
    ).fetchall()]
    recent = dates[-1]
    monday = next(d for d in reversed(dates) if date.fromisoformat(f"{d[:4]}-{d[4:6]}-{d[6:]}").weekday() == 0)
    midmonth = next(d for d in reversed(dates) if 12 <= int(d[6:]) <= 18)
    boards = db.execute(
        f"SELECT board_scope, min(canonical_security_id) FROM read_parquet('{daily}') "
        "WHERE trade_date = ? GROUP BY board_scope ORDER BY board_scope", [int(recent)]
    ).fetchall()
    short = db.execute(
        f"SELECT canonical_security_id, board_scope, min(trade_date) AS first_trade "
        f"FROM read_parquet('{daily}') GROUP BY 1, 2 "
        "HAVING min(trade_date) >= 20260801 AND max(trade_date) = ? "
        "ORDER BY first_trade DESC, canonical_security_id LIMIT 1", [int(recent)]
    ).fetchone()
    adjusted = db.execute(
        f"SELECT canonical_security_id, board_scope, trade_date FROM read_parquet('{daily}') "
        "WHERE trade_date = ? AND (qfq_mul <> 1 OR qfq_add <> 0) "
        "ORDER BY canonical_security_id LIMIT 1", [int(midmonth)]
    ).fetchone()
    # The accepted status publication is scanned in file order. Sorting makes the
    # chosen suspension/resumption independent of gzip row order.
    recent_status: dict[str, list[tuple[str, str]]] = {}
    floor = f"{dates[max(0, len(dates) - 70)][:4]}-{dates[max(0, len(dates) - 70)][4:6]}-{dates[max(0, len(dates) - 70)][6:]}"
    with gzip.open(inputs["trading_status"].path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if floor <= row["trade_date"] <= cutoff:
                recent_status.setdefault(row["security_id"], []).append((row["trade_date"], row["status"]))
    resumptions = []
    for sid, rows in recent_status.items():
        for prior, current in zip(sorted(rows), sorted(rows)[1:]):
            if prior[1] != "ACTUAL_TRADED" and current[1] == "ACTUAL_TRADED":
                resumptions.append((current[0], sid, prior[0], prior[1]))
    resumption = min(resumptions) if resumptions else None
    matrix = {
        "contract_id": "V4_05_REPLAY_DATE_MATRIX_R1",
        "status": "FROZEN_BEFORE_REPLAY_OUTPUT",
        "authority": authority,
        "input_hashes": {k: v.sha256 for k, v in sorted(inputs.items())},
        "selection_rules": {
            "recent": "latest accepted daily trade date <= accepted source cutoff",
            "monday": "latest accepted daily Monday <= cutoff",
            "midmonth": "latest accepted daily date with calendar day 12..18 <= cutoff",
            "board": "lexicographically smallest security id per board on recent date",
            "short_history": "latest first-trade date >= 2026-08-01 with trade on recent date; security id tie-break",
            "adjustment": "lexicographically smallest security id at midmonth with qfq_mul != 1 or qfq_add != 0",
            "resumption": "earliest recent status transition from non-ACTUAL_TRADED to ACTUAL_TRADED in last 70 accepted daily sessions; security id tie-break",
            "code_change": "unique required-board accepted identity-map interval transition, earliest such transition",
        },
        "cases": {
            "recent": {"trade_date": recent},
            "monday_weekly_asof": {"trade_date": monday},
            "midmonth_monthly_asof": {"trade_date": midmonth},
            "board_coverage": [{"board_scope": b, "security_id": sid, "trade_date": recent} for b, sid in boards],
            "short_history": {"security_id": short[0], "board_scope": short[1], "first_trade_date": str(short[2]), "trade_date": recent} if short else None,
            "adjustment_sensitive": {"security_id": adjusted[0], "board_scope": adjusted[1], "trade_date": str(adjusted[2])} if adjusted else None,
            "suspension_resumption": {"security_id": resumption[1], "suspended_date": resumption[2], "suspended_status": resumption[3], "resumed_date": resumption[0]} if resumption else None,
            "code_change": {"security_id": "SEC-EDEDE35FE66896ACCA0AC85EEB2F133B", "predecessor_key": "SZ.300114", "successor_key": "SZ.302132", "transition_date": "2025-02-17"},
        },
        "status_scan": {"entities": len(recent_status), "resumption_candidates": len(resumptions)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=OUT.parent, delete=False) as stream:
        json.dump(matrix, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        temp = Path(stream.name)
    os.replace(temp, OUT)
    print(OUT)


if __name__ == "__main__":
    main()
