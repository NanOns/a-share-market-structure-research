"""Rollback-only PostgreSQL basket insert/read/head-revision rehearsal."""
from __future__ import annotations

from uuid import uuid4

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.basket_store import insert_entry_basket, read_accepted_entry_basket
from src.focus_tracker.contracts import (FocusKey, SOURCE_AUTHORITY_CONTRACT,
                                         digest, episode_id)
from src.focus_tracker.sector_basket import (CONTRACT_ID as BASKET_CONTRACT,
                                             SectorBasket, baskets_from_accepted_publication)
from src.focus_tracker.source_reader import read_accepted_sources
from src.workbench_db.postgres_repository import PostgresRepository


def main() -> int:
    with PostgresRepository(dsn=_dsn()) as repo:
        try:
            with repo.connection.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))",
                            ("FOCUS_BASKET_ROLLBACK_PROBE",))
                cur.execute("select max(trade_date) from workbench.publication_heads")
                day = cur.fetchone()[0]
            sources = read_accepted_sources(repo, day)
            sector = next(row.key.entity_id for row in sources.rows
                          if row.key.entity_type == "SECTOR")
            basket = baskets_from_accepted_publication(repo, sources.publication_id,
                                                       {sector})[0]
            key = FocusKey("V3_SECTOR_TRACK", "SECTOR", sector, "V3_SECTOR")
            eid = episode_id(key, day)
            run_id = "focus-basket-probe-" + uuid4().hex
            with repo.connection.cursor() as cur:
                cur.execute("select 1 from workbench.focus_trade_date_heads "
                            "where trade_date=%s and source_authority_contract_id=%s",
                            (day, SOURCE_AUTHORITY_CONTRACT))
                if cur.fetchone():
                    raise RuntimeError("PROBE_REQUIRES_EMPTY_FOCUS_DATE_HEAD")
                cur.execute("""insert into workbench.focus_runs
                    (focus_run_id,trade_date,revision,publication_id,
                     source_authority_contract_id,source_family_set,family_capabilities,
                     source_identity_digest,calendar_digest,observation_input_digest,
                     state_contract_id,parameter_set_id,price_basis,dependency_lock_hash,
                     evaluation_basis,core_publication_status,activated_at_utc)
                    values (%s,%s,1,%s,%s,'[]'::jsonb,'{}'::jsonb,
                            %s,%s,%s,%s,%s,%s,%s,'REAL_FORWARD','ACTIVATED',now())""",
                    (run_id, day, sources.publication_id, SOURCE_AUTHORITY_CONTRACT,
                     sources.source_identity_digest, "0" * 64, "0" * 64,
                     "PROBE", "PROBE", "TDX_NATIVE_QFQ", "0" * 64))
                cur.execute("""insert into workbench.focus_episodes
                    (episode_id,source_family,entity_type,entity_id,
                     selection_contract_family,first_trade_date,first_focus_run_id)
                    values (%s,%s,%s,%s,%s,%s,%s)""",
                    (eid, key.source_family, key.entity_type, key.entity_id,
                     key.selection_contract_family, day, run_id))
            insert_entry_basket(repo, episode_id=eid, focus_run_id=run_id,
                                publication_id=sources.publication_id, basket=basket)
            insert_entry_basket(repo, episode_id=eid, focus_run_id=run_id,
                                publication_id=sources.publication_id, basket=basket)
            with repo.connection.cursor() as cur:
                cur.execute("""insert into workbench.focus_trade_date_heads
                    (trade_date,source_authority_contract_id,accepted_focus_run_id,
                     accepted_revision,lineage_state,activated_at_utc)
                    values (%s,%s,%s,1,'VALID',now())""",
                    (day, SOURCE_AUTHORITY_CONTRACT, run_id))
            recovered = read_accepted_entry_basket(repo, eid)
            if recovered != basket:
                raise RuntimeError("BASKET_ROUNDTRIP_MISMATCH")
            revised_run = "focus-basket-probe-" + uuid4().hex
            revised_members = basket.security_ids[:-1]
            revised_source = basket.source_identity + ":PROBE_REVISION"
            revised_digest = digest({"contract": BASKET_CONTRACT,
                                     "publication_id": sources.publication_id,
                                     "sector_id": sector,
                                     "source_kind": basket.source_kind,
                                     "source_identity": revised_source,
                                     "members": revised_members})
            revised = SectorBasket(sector, revised_members, basket.source_kind,
                                   revised_source, revised_digest)
            try:
                insert_entry_basket(repo, episode_id=eid, focus_run_id=run_id,
                                    publication_id=sources.publication_id, basket=revised)
            except ValueError as exc:
                if "immutable entry basket conflict" not in str(exc):
                    raise
            else:
                raise RuntimeError("BASKET_CONFLICT_NOT_REJECTED")
            with repo.connection.cursor() as cur:
                cur.execute("""insert into workbench.focus_runs
                    (focus_run_id,trade_date,revision,publication_id,
                     source_authority_contract_id,source_family_set,family_capabilities,
                     source_identity_digest,calendar_digest,observation_input_digest,
                     state_contract_id,parameter_set_id,price_basis,dependency_lock_hash,
                     evaluation_basis,core_publication_status,activated_at_utc)
                    values (%s,%s,2,%s,%s,'[]'::jsonb,'{}'::jsonb,
                            %s,%s,%s,%s,%s,%s,%s,'REAL_FORWARD','ACTIVATED',now())""",
                    (revised_run, day, sources.publication_id, SOURCE_AUTHORITY_CONTRACT,
                     sources.source_identity_digest, "0" * 64, "0" * 64,
                     "PROBE", "PROBE", "TDX_NATIVE_QFQ", "0" * 64))
            insert_entry_basket(repo, episode_id=eid, focus_run_id=revised_run,
                                publication_id=sources.publication_id, basket=revised)
            with repo.connection.cursor() as cur:
                cur.execute("""update workbench.focus_trade_date_heads
                    set accepted_focus_run_id=%s,accepted_revision=2,activated_at_utc=now()
                    where trade_date=%s and source_authority_contract_id=%s""",
                    (revised_run, day, SOURCE_AUTHORITY_CONTRACT))
            if read_accepted_entry_basket(repo, eid) != revised:
                raise RuntimeError("BASKET_ACCEPTED_REVISION_SELECTION_FAILED")
            print({"mode": "ROLLBACK_ONLY", "sector_id": sector,
                   "member_count": len(basket.security_ids),
                   "basket_digest": basket.basket_digest,
                   "roundtrip": "PASS", "accepted_revision_switch": "PASS"})
        finally:
            repo.connection.rollback()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
