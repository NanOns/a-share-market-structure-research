"""Rollback-only rehearsal of same-day revisions and ordered downstream replay."""
from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.contracts import SOURCE_AUTHORITY_CONTRACT
from src.focus_tracker.core_activation import activate_core_head
from src.focus_tracker.replay import pending_replay_chain
from src.workbench_db.postgres_repository import PostgresRepository


def _insert_ready_run(cur, *, run_id: str, trade_date: date, revision: int,
                      publication_id: str) -> None:
    marker = (run_id.replace("-", "") * 2)[:64]
    cur.execute("""insert into workbench.focus_runs
        (focus_run_id,trade_date,revision,publication_id,
         source_authority_contract_id,source_family_set,family_capabilities,
         source_identity_digest,calendar_digest,observation_input_digest,
         state_contract_id,parameter_set_id,price_basis,dependency_lock_hash,
         evaluation_basis,core_publication_status)
        values (%s,%s,%s,%s,%s,'[]'::jsonb,'{}'::jsonb,%s,%s,%s,
                'PROBE_STATE_V1','PROBE_PARAMS_V1','TDX_NATIVE_AFFINE_QFQ',%s,
                'HISTORICAL_RECONSTRUCTED','READY')""",
        (run_id, trade_date, revision, publication_id,
         SOURCE_AUTHORITY_CONTRACT, marker, marker, marker, marker))


def run() -> dict[str, object]:
    probe = uuid4().hex
    base = date(2098, 1, 5)
    days = (base, base + timedelta(days=1), base + timedelta(days=2))
    created: list[str] = []
    with PostgresRepository(dsn=_dsn()) as repo:
        con = repo.connection
        if con is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        try:
            with con.cursor() as cur:
                cur.execute("select publication_id from workbench.publication_heads "
                            "order by trade_date desc limit 1")
                accepted = cur.fetchone()
                if accepted is None:
                    raise RuntimeError("ACCEPTED_PUBLICATION_REQUIRED_FOR_PROBE")
                publication_id = str(accepted[0])
                for day_index, day in enumerate(days, start=1):
                    run_id = f"focus-replay-probe-{probe}-{day_index}-r1"
                    _insert_ready_run(cur, run_id=run_id, trade_date=day,
                                      revision=1, publication_id=publication_id)
                    created.append(run_id)
                    activate_core_head(repo, focus_run_id=run_id,
                                       trade_date=day, revision=1)

                # Revising the first day invalidates every later valid head.
                revised_first = f"focus-replay-probe-{probe}-1-r2"
                _insert_ready_run(cur, run_id=revised_first, trade_date=days[0],
                                  revision=2, publication_id=publication_id)
                created.append(revised_first)
                activate_core_head(repo, focus_run_id=revised_first,
                                   trade_date=days[0], revision=2)
                pending = pending_replay_chain(repo)
                if tuple(item.trade_date for item in pending) != days[1:]:
                    raise RuntimeError("downstream heads were not invalidated")

                out_of_order = f"focus-replay-probe-{probe}-3-r2"
                _insert_ready_run(cur, run_id=out_of_order, trade_date=days[2],
                                  revision=2, publication_id=publication_id)
                created.append(out_of_order)
                try:
                    activate_core_head(repo, focus_run_id=out_of_order,
                                       trade_date=days[2], revision=2)
                except ValueError as exc:
                    if "trade-date order" not in str(exc):
                        raise
                else:
                    raise RuntimeError("out-of-order replay was accepted")

                replay_second = f"focus-replay-probe-{probe}-2-r2"
                _insert_ready_run(cur, run_id=replay_second, trade_date=days[1],
                                  revision=2, publication_id=publication_id)
                created.append(replay_second)
                activate_core_head(repo, focus_run_id=replay_second,
                                   trade_date=days[1], revision=2)
                activate_core_head(repo, focus_run_id=out_of_order,
                                   trade_date=days[2], revision=2)
                if pending_replay_chain(repo):
                    raise RuntimeError("ordered replay did not clear pending chain")
            con.rollback()
        except Exception:
            con.rollback()
            raise
    return {"mode": "ROLLBACK_ONLY", "same_day_revision": "r1->r2",
            "invalidated_heads": 2, "out_of_order_replay": "REJECTED",
            "ordered_replay": "CLEARED", "temporary_runs": len(created),
            "persisted_changes": 0}


if __name__ == "__main__":
    print(run())
