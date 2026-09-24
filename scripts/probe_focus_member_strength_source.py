"""Read-only accepted analysis snapshot/member-state availability probe."""
from __future__ import annotations

import psycopg

from scripts.apply_focus_pg_schema_v1 import _dsn


def main() -> int:
    with psycopg.connect(_dsn()) as pg:
        with pg.transaction():
            pg.execute("set transaction read only")
            day, publication = pg.execute(
                "select trade_date,publication_id from workbench.publication_heads "
                "order by trade_date desc limit 1").fetchone()
            heads = pg.execute("""select h.domain,h.snapshot_id,s.status,s.cutoff_date
                from workbench.analysis_snapshot_heads h
                join workbench.analysis_snapshots s using(snapshot_id)
                where h.trade_date=%s and h.publication_id=%s order by h.domain""",
                (day, publication)).fetchall()
            entries = pg.execute("""select h.domain,e.slice_id,
                    (select count(*) from workbench.member_state_result_rows r
                     join workbench.analysis_slice_result_bindings b
                       on b.result_object_id=r.result_object_id
                     where b.slice_id=e.slice_id and r.trade_date=%s) as result_rows,
                    (select count(*) from workbench.sector_member_state_daily m
                     where m.slice_id=e.slice_id and m.trade_date=%s) as legacy_rows
                from workbench.analysis_snapshot_heads h
                join workbench.analysis_snapshot_entries e
                  on e.snapshot_id=h.snapshot_id and e.domain='member_state'
                 and e.trade_date=%s
                where h.trade_date=%s and h.publication_id=%s
                order by h.domain""", (day, day, day, day, publication)).fetchall()
            contracts = pg.execute("""select distinct r.contract_id,r.history_basis
                from workbench.analysis_snapshot_heads h
                join workbench.analysis_snapshot_entries e
                  on e.snapshot_id=h.snapshot_id and e.domain='member_state'
                 and e.trade_date=%s
                join workbench.analysis_slice_result_bindings b on b.slice_id=e.slice_id
                join workbench.member_state_result_rows r
                  on r.result_object_id=b.result_object_id and r.trade_date=%s
                where h.trade_date=%s and h.publication_id=%s""",
                (day, day, day, publication)).fetchall()
            result_identity = pg.execute("""select distinct o.semantic_contract,o.schema_version
                from workbench.analysis_snapshot_heads h
                join workbench.analysis_snapshot_entries e
                  on e.snapshot_id=h.snapshot_id and e.domain='member_state'
                 and e.trade_date=%s
                join workbench.analysis_slice_result_bindings b on b.slice_id=e.slice_id
                join workbench.analysis_result_objects o
                  on o.result_object_id=b.result_object_id
                where h.trade_date=%s and h.publication_id=%s""",
                (day, day, publication)).fetchall()
            bases = pg.execute("""select e.slice_id,b.membership_snapshot_id,b.price_basis
                from workbench.analysis_snapshot_heads h
                join workbench.analysis_snapshot_entries e
                  on e.snapshot_id=h.snapshot_id and e.domain='member_state'
                 and e.trade_date=%s
                join workbench.analysis_daily_basis b on b.slice_id=e.slice_id
                where h.trade_date=%s and h.publication_id=%s""",
                (day, day, publication)).fetchall()
            relation = pg.execute("""select e.sector_id,e.security_id
                from workbench.relation_publication_bindings b
                join workbench.relation_edge_intervals e on e.source_scope=b.source_scope
                  and e.from_revision<=b.revision_no
                  and (e.to_revision is null or b.revision_no<e.to_revision)
                where b.publication_id=%s""", (publication,)).fetchall()
            strength = pg.execute("""select r.sector_id,r.security_id,r.member_present,
                       r.strong_state
                from workbench.analysis_snapshot_heads h
                join workbench.analysis_snapshot_entries e
                  on e.snapshot_id=h.snapshot_id and e.domain='member_state'
                 and e.trade_date=%s
                join workbench.analysis_slice_result_bindings b on b.slice_id=e.slice_id
                join workbench.member_state_result_rows r
                  on r.result_object_id=b.result_object_id and r.trade_date=%s
                where h.trade_date=%s and h.publication_id=%s""",
                (day, day, day, publication)).fetchall()
            relation_pairs = {(a, b) for a, b in relation}
            strength_pairs = {(a, b) for a, b, present, _ in strength if present}
    print({"trade_date": str(day), "publication_id": publication,
           "heads": [(domain, snapshot, status, str(cutoff))
                     for domain, snapshot, status, cutoff in heads],
           "member_state_entries": [(domain, slice_id, result_rows, legacy_rows)
                                    for domain, slice_id, result_rows, legacy_rows in entries],
           "contracts": contracts, "result_identity": result_identity,
           "basis": bases,
           "relation_present_count": len(relation_pairs),
           "strength_present_count": len(strength_pairs),
           "relation_missing_from_strength": len(relation_pairs - strength_pairs),
           "strength_extra_to_relation": len(strength_pairs - relation_pairs)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
