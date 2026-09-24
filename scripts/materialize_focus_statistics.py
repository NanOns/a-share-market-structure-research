"""Materialize descriptive Focus outcome statistics for one activated run.

Default mode is read-only preview. --apply writes one immutable batch and
atomically moves the run's explicit statistics head.
"""
from __future__ import annotations

import argparse
import hashlib
import json

import psycopg
from psycopg import sql

from scripts.apply_focus_pg_schema_v1 import _dsn

CONTRACT = "FOCUS_STATISTICS_MATERIALIZATION_V1"
MIN_ROWS = 30
MIN_DATES = 5

SOURCE_SQL = """
select e.source_family,e.entity_type,e.selection_contract_family,
       coalesce(seg.source_model_contract_id,'UNKNOWN') as source_model_contract_id,
       coalesce(seg.state_contract_id,ar.state_contract_id) as state_contract_id,
       a.anchor_type,o.horizon,o.evaluation_basis,a.price_basis,
       o.anchor_id,a.trade_date as signal_trade_date,o.target_revision,o.status,
       o.forward_return,o.mfe,o.mdd,o.input_digest
from {schema}.focus_outcome_heads h
join {schema}.focus_episode_outcomes o on o.anchor_id=h.anchor_id and o.horizon=h.horizon
 and o.target_revision=h.accepted_target_revision
join {schema}.focus_episode_anchors a on a.anchor_id=h.anchor_id
join {schema}.focus_episodes e on e.episode_id=a.episode_id
join {schema}.focus_runs ar on ar.focus_run_id=a.focus_run_id
left join lateral (
  select s.source_model_contract_id,s.state_contract_id
  from {schema}.focus_episode_segments s
  where s.episode_id=e.episode_id and s.segment_type='SOURCE_MODEL'
    and s.start_trade_date<=a.trade_date
  order by s.start_trade_date desc,s.source_model_contract_id limit 1
) seg on true
where a.trade_date<=%s and o.target_trade_date<=%s
order by e.source_family,e.entity_type,e.selection_contract_family,
         source_model_contract_id,state_contract_id,a.anchor_type,o.horizon,
         o.evaluation_basis,a.price_basis,a.trade_date,o.anchor_id
"""


def _digest_rows(rows: list[tuple]) -> str:
    canonical = json.dumps(rows, default=str, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def materialize_in_transaction(cur, *, focus_run_id: str | None, apply: bool,
                               schema_name: str = "workbench") -> dict[str, object]:
    schema = sql.Identifier(schema_name)
    if focus_run_id:
        cur.execute(sql.SQL("select focus_run_id,trade_date,evaluation_basis,core_publication_status "
                            "from {}.focus_runs where focus_run_id=%s").format(schema), (focus_run_id,))
    else:
        cur.execute(sql.SQL("select focus_run_id,trade_date,evaluation_basis,core_publication_status "
                            "from {}.focus_runs where core_publication_status='ACTIVATED' "
                            "order by trade_date desc,revision desc limit 1").format(schema))
    run = cur.fetchone()
    if not run:
        return {"statistics_contract_id": CONTRACT, "status": "NO_ACTIVATED_FOCUS_RUN",
                "mode": "APPLY" if apply else "PREVIEW", "batches_written": 0}
    if run[3] != "ACTIVATED":
        return {"statistics_contract_id": CONTRACT, "status": "RUN_NOT_ACTIVATED",
                "focus_run_id": run[0], "mode": "APPLY" if apply else "PREVIEW",
                "batches_written": 0}
    run_id, as_of, _basis, _ = run
    cur.execute(sql.SQL(SOURCE_SQL).format(schema=schema), (as_of, as_of))
    columns = [d.name for d in cur.description]
    records = [dict(zip(columns, row)) for row in cur.fetchall()]
    digest_records = [tuple(row[k] for k in columns) for row in records]
    input_digest = _digest_rows(digest_records)
    batch_id = "focus-stats-" + hashlib.sha256(
        f"{run_id}|{CONTRACT}|{input_digest}".encode()).hexdigest()[:32]

    group_keys = ("source_family", "entity_type", "selection_contract_family",
                  "source_model_contract_id", "state_contract_id", "anchor_type",
                  "horizon", "evaluation_basis", "price_basis")
    grouped: dict[tuple, list[dict]] = {}
    for row in records:
        grouped.setdefault(tuple(row[k] for k in group_keys), []).append(row)
    output = []
    for key, group in sorted(grouped.items(), key=lambda pair: tuple(map(str, pair[0]))):
        observed = [r for r in group if r["status"] == "OBSERVED" and
                    r["forward_return"] is not None and r["mfe"] is not None and r["mdd"] is not None]
        dates = {r["signal_trade_date"] for r in observed}
        ready = len(observed) >= MIN_ROWS and len(dates) >= MIN_DATES
        row = dict(zip(group_keys, key))
        row.update(sample_count=len(observed), signal_date_count=len(dates),
                   incomplete_count=len(group)-len(observed),
                   gate_status="READY" if ready else "INSUFFICIENT_SAMPLES",
                   p25_return=None, median_return=None, p75_return=None,
                   max_mfe=None, worst_mdd=None)
        if ready:
            cur.execute("select percentile_disc(0.25) within group (order by x),"
                        "percentile_disc(0.5) within group (order by x),"
                        "percentile_disc(0.75) within group (order by x) "
                        "from unnest(%s::numeric[]) x", ([r["forward_return"] for r in observed],))
            row["p25_return"], row["median_return"], row["p75_return"] = cur.fetchone()
            row["max_mfe"] = max(r["mfe"] for r in observed)
            row["worst_mdd"] = min(r["mdd"] for r in observed)
        output.append(row)

    receipt = {"statistics_contract_id": CONTRACT, "focus_run_id": run_id,
               "as_of_trade_date": as_of.isoformat(), "statistics_batch_id": batch_id,
               "input_digest": input_digest, "outcome_count": len(records),
               "group_count": len(output), "groups": output,
               "mode": "APPLY" if apply else "PREVIEW"}
    if apply:
        cur.execute(sql.SQL("insert into {}.focus_statistics_batches "
                            "(statistics_batch_id,focus_run_id,as_of_trade_date,statistics_contract_id,"
                            "input_digest,group_count,outcome_count) values (%s,%s,%s,%s,%s,%s,%s) "
                            "on conflict (focus_run_id,statistics_contract_id,input_digest) do nothing").format(schema),
                    (batch_id, run_id, as_of, CONTRACT, input_digest, len(output), len(records)))
        for row in output:
            cur.execute(sql.SQL("insert into {}.focus_statistics_rows "
                                "(statistics_batch_id,source_family,entity_type,selection_contract_family,"
                                "source_model_contract_id,state_contract_id,anchor_type,horizon,evaluation_basis,"
                                "price_basis,sample_count,signal_date_count,incomplete_count,gate_status,"
                                "p25_return,median_return,p75_return,max_mfe,worst_mdd) "
                                "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                                "on conflict do nothing").format(schema),
                        (batch_id, *(row[k] for k in group_keys), row["sample_count"],
                         row["signal_date_count"], row["incomplete_count"], row["gate_status"],
                         row["p25_return"], row["median_return"], row["p75_return"],
                         row["max_mfe"], row["worst_mdd"]))
        cur.execute(sql.SQL("insert into {}.focus_statistics_heads "
                            "(focus_run_id,statistics_batch_id) values (%s,%s) "
                            "on conflict (focus_run_id) do update set statistics_batch_id=excluded.statistics_batch_id,"
                            "activated_at_utc=clock_timestamp()").format(schema), (run_id, batch_id))
    return receipt


def materialize(*, focus_run_id: str | None, apply: bool) -> dict[str, object]:
    with psycopg.connect(_dsn()) as pg:
        try:
            with pg.cursor() as cur:
                cur.execute("set transaction isolation level repeatable read")
                cur.execute("set transaction read write" if apply else "set transaction read only")
                receipt = materialize_in_transaction(cur, focus_run_id=focus_run_id, apply=apply)
            if apply:
                pg.commit()
            else:
                pg.rollback()
            return receipt
        except Exception:
            pg.rollback()
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--focus-run-id")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(materialize(focus_run_id=args.focus_run_id, apply=args.apply),
                     ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
