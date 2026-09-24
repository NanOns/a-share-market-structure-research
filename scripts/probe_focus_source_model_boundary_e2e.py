"""Run a committed SOURCE_MODEL_BOUNDARY writer/readback in a disposable PG database."""
from __future__ import annotations

import json
import tempfile
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from scripts.apply_focus_pg_schema_v1 import _dsn
from scripts import (replay_focus_ordered_chain as replay_writer,
                     run_focus_continuation_core_transaction as writer)
from src.focus_tracker.contracts import (SOURCE_AUTHORITY_CONTRACT, SOURCE_MEMBERSHIPS, FocusKey,
                                         digest, source_item_digest)
from src.focus_tracker.daily_plan import build_day_plan
from src.focus_tracker.materialize import PathRequest, StockFact
from src.focus_tracker.previous_reader import read_predecessor
from src.focus_tracker.settlement import due_anchor_plan
from src.focus_tracker.source_reader import SourceRow
from src.workbench_db.postgres_repository import PostgresRepository


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ID = "FOCUS_SOURCE_MODEL_BOUNDARY_WRITER_READBACK_E2E_V1"
FIRST_DATE = date(2026, 9, 23)
TRADE_DATE = date(2026, 9, 24)
STATE_CONTRACT = "FOCUS_PATH_STATE_V1"
EPISODE_ID = "focus-e2e-boundary-episode"
SECURITY_ID = "SH.600001"


def _source_row(key: FocusKey, day: date, contract: str, item_key: str) -> SourceRow:
    facts = {"selection_contract_family": key.selection_contract_family,
             "evidence": {"basis": "synthetic e2e"}}
    return SourceRow(key, day, "CURRENT", item_key,
                     source_item_digest(item_key, contract, facts),
                     contract, 1, "CURRENT", facts)


def _seed_database(dsn: str) -> None:
    with psycopg.connect(dsn) as con:
        with con.cursor() as cur:
            cur.execute("create schema workbench")
            cur.execute("create schema workbench_meta")
            cur.execute("""create table workbench.publications (
                publication_id varchar primary key, trade_date date not null,
                revision integer not null, status varchar not null,
                source_identity_sha256 char(64),
                source_path varchar not null, imported_at_utc timestamptz not null,
                unique(trade_date,revision))""")
            cur.execute("""create table workbench.publication_heads (
                trade_date date primary key,
                publication_id varchar not null references workbench.publications(publication_id))""")
            cur.execute("""create table workbench_meta.artifact_catalog (
                artifact_id text, sha256 char(64), availability text,
                relative_path text, discovered_at timestamptz)""")
            cur.execute((ROOT / "src/workbench_db/focus_schema_v1.sql").read_text("utf-8"))
            cur.execute((ROOT / "src/workbench_db/focus_source_model_segments_v2.sql").read_text("utf-8"))
            cur.execute((ROOT / "src/workbench_db/focus_publication_identity_migrations_v1.sql").read_text("utf-8"))
            cur.execute("""insert into workbench.publications
                (publication_id,trade_date,revision,status,source_path,imported_at_utc)
                values ('pub-prev',%s,1,'SUCCESS','synthetic',now()),
                       ('pub-today',%s,1,'SUCCESS','synthetic',now()),
                       ('pub-25',%s,1,'SUCCESS','synthetic',now()),
                       ('pub-26',%s,1,'SUCCESS','synthetic',now())""",
                (FIRST_DATE, TRADE_DATE, date(2026, 9, 25), date(2026, 9, 28)))
            cur.execute("""insert into workbench.publication_heads values
                (%s,'pub-prev'),(%s,'pub-today'),(%s,'pub-25'),(%s,'pub-26')""",
                (FIRST_DATE, TRADE_DATE, date(2026, 9, 25), date(2026, 9, 28)))
            cur.execute("""insert into workbench.focus_runs
                (focus_run_id,trade_date,revision,publication_id,
                 source_authority_contract_id,source_family_set,family_capabilities,
                 source_identity_digest,calendar_digest,observation_input_digest,
                 state_contract_id,parameter_set_id,price_basis,dependency_lock_hash,
                 evaluation_basis,core_publication_status,activated_at_utc)
                values ('focus-prev',%s,1,'pub-prev',%s,'[]','{}',%s,%s,%s,%s,%s,%s,%s,
                        'REAL_FORWARD','ACTIVATED',now())""",
                (FIRST_DATE, SOURCE_AUTHORITY_CONTRACT, "a" * 64, "b" * 64,
                 "c" * 64, STATE_CONTRACT, "params-v1", "TDX_NATIVE_AFFINE_QFQ",
                 "d" * 64))
            cur.execute("""insert into workbench.focus_trade_date_heads
                (trade_date,source_authority_contract_id,accepted_focus_run_id,
                 accepted_revision,predecessor_focus_run_id,lineage_state,activated_at_utc)
                values (%s,%s,'focus-prev',1,null,'VALID',now())""",
                (FIRST_DATE, SOURCE_AUTHORITY_CONTRACT))
            cur.execute("""insert into workbench.focus_episodes
                (episode_id,source_family,entity_type,entity_id,selection_contract_family,
                 first_trade_date,first_focus_run_id,parent_episode_id)
                values (%s,'V3_SHORTLIST_STOCK','STOCK',%s,'V3_SHORTLIST_FAMILY_V1',%s,
                        'focus-prev',null)""", (EPISODE_ID, SECURITY_ID, FIRST_DATE))
            cur.execute("""insert into workbench.focus_episode_segments
                (segment_id,episode_id,segment_type,start_trade_date,source_model_contract_id,
                 selection_contract_family,state_contract_id,parameter_set_id,boundary_reason,focus_run_id)
                values ('segment-prev',%s,'SOURCE_MODEL',%s,'SOURCE_CONTRACT_V1',%s,%s,
                        'params-v1','FIRST_FOCUS','focus-prev')""",
                (EPISODE_ID, FIRST_DATE, "V3_SHORTLIST_FAMILY_V1", STATE_CONTRACT))
            first_key = FocusKey("V3_SHORTLIST_STOCK", "STOCK", SECURITY_ID,
                                 "V3_SHORTLIST_FAMILY_V1")
            first_row = _source_row(first_key, FIRST_DATE, "SOURCE_CONTRACT_V1", "prev-item")
            cur.execute("""insert into workbench.focus_daily_items
                (focus_run_id,source_family,entity_type,entity_id,selection_contract_family,
                 source_item_key,source_item_digest,source_contract_id,source_membership_state,
                 source_focus_class,source_rank,source_quality,source_facts)
                values ('focus-prev',%s,'STOCK',%s,%s,%s,%s,%s,'CURRENT','CURRENT',1,'READY',%s)""",
                (first_key.source_family, SECURITY_ID, first_key.selection_contract_family,
                 first_row.source_item_key, first_row.source_item_digest,
                 first_row.source_contract_id, Jsonb(first_row.source_facts)))
            cur.execute("""insert into workbench.focus_episode_observations
                (episode_id,focus_run_id,trade_date,source_revision,evaluation_mode,
                 state_contract_id,source_membership_state,membership_phase,validity_state,
                 followup_state,current_path_state,lifetime_path_tags,continuity_quality,
                 close_price,quality_status,fact_digest,facts)
                values (%s,'focus-prev',%s,1,'AS_RECORDED',%s,'CURRENT','NEW','VALID',
                        'ACTIVE_FOCUS','TREND_CONTINUE','[]','CONTINUOUS',10,'READY',%s,'{}')""",
                (EPISODE_ID, FIRST_DATE, STATE_CONTRACT, "e" * 64))


def run_probe() -> dict[str, object]:
    original_dsn = _dsn()
    database_name = "focus_acceptance_" + uuid.uuid4().hex[:16]
    admin = psycopg.connect(original_dsn, autocommit=True)
    try:
        exists = admin.execute("select 1 from pg_database where datname=%s",
                               (database_name,)).fetchone()
        if exists:
            raise RuntimeError("DISPOSABLE_ACCEPTANCE_DATABASE_NAME_COLLISION")
        admin.execute(sql.SQL("create database {}").format(sql.Identifier(database_name)))
    finally:
        admin.close()
    try:
        params = psycopg.conninfo.conninfo_to_dict(original_dsn)
        params["dbname"] = database_name
        isolated_dsn = psycopg.conninfo.make_conninfo(**params)
        _seed_database(isolated_dsn)

        old_key = FocusKey("V3_SHORTLIST_STOCK", "STOCK", SECURITY_ID,
                           "V3_SHORTLIST_FAMILY_V1")
        active_key = FocusKey("V3_SHORTLIST_STOCK", "STOCK", SECURITY_ID,
                              "V3_SHORTLIST_FAMILY_V2")
        batch: dict[str, object] = {}
        writer._dsn = lambda: isolated_dsn
        def prepare_day(day: date, version: str, publication_id: str):
            selection = "V3_SHORTLIST_FAMILY_V1" if version == "SOURCE_CONTRACT_V1" else "V3_SHORTLIST_FAMILY_V2"
            key = FocusKey("V3_SHORTLIST_STOCK", "STOCK", SECURITY_ID, selection)
            suffix = uuid.uuid4().hex[:8]
            item_key = day.isoformat() + "-" + suffix
            current = _source_row(key, day, version, item_key)
            capabilities = {family: "UNAVAILABLE" for family in SOURCE_MEMBERSHIPS}
            capabilities["V3_SHORTLIST_STOCK"] = "COMPLETE"
            sources = NS(trade_date=day, publication_id=publication_id, rows=(current,),
                         capabilities=capabilities,
                         source_identity_digest=digest({"date": day, "item": item_key}),
                         v3_run_id=None, bundle_digest=None)
            with PostgresRepository(dsn=isolated_dsn) as repository:
                predecessor = read_predecessor(repository, day)
                repository.connection.rollback()
            plan = build_day_plan(sources=sources, previous=predecessor.previous,
                                  pending_followup=set(), due_outcomes=set())
            observations = tuple(NS(
                key=decision.key,
                observation=NS(
                    episode_id=decision.episode_id,
                    source_membership_state=decision.membership,
                    membership_phase=decision.phase, validity_state="VALID",
                    followup_state="ACTIVE_FOCUS", current_path_state="TREND_CONTINUE",
                    lifetime_path_tags=(), quality_status="READY",
                    fact_digest=digest({"date": day, "item": item_key,
                                        "episode": decision.episode_id}),
                    evidence={"path_predicates": {}, "predicate_facts": {}}))
                for decision in (plan.episode_tracking or plan.decisions))
            stock_facts = tuple(StockFact(
                SECURITY_ID, day, request.start_trade_date, "READY", None,
                "11", "0.1", "0.15", "-0.02", "-0.02", "-0.03",
                "qfq-v1", digest({"day": day, "item": item_key}))
                for request in plan.stock_path_requests)
            payload = {"state_contract_id": STATE_CONTRACT,
                       "parameter_set_id": "params-v2",
                       "dependency_lock_hash": "2" * 64,
                       "calendar_digest": digest({"day": day, "calendar": "synthetic"}),
                       "normalized_artifact_sha256": "4" * 64}
            closure = NS(input_digest=digest({"date": day, "source": sources.source_identity_digest,
                                               "plan": plan.plan_digest}))
            manifest = NS(sha256=digest({"contract": CONTRACT_ID, "day": day,
                                         "source": sources.source_identity_digest,
                                         "closure": closure.input_digest}), payload=payload)
            batch.update(manifest=manifest, sources=sources, plan=plan,
                         stock_facts=stock_facts, observations=observations,
                         closure=closure)
            return batch

        writer.build_focus_daily_batch = lambda **_: tuple(
            batch[name] for name in ("manifest", "sources", "plan", "stock_facts",
                                     "observations")) + ((), batch["closure"])
        writer.read_accepted_sources = lambda *_: batch["sources"]
        writer.require_core_publication_ready = lambda **_: None
        def publish(day: date, version: str, publication_id: str):
            prepared = prepare_day(day, version, publication_id)
            return writer.publish_next_day(trade_date=day,
                                           expected_manifest_digest=prepared["manifest"].sha256,
                                           commit=True)

        first_result = publish(TRADE_DATE, "SOURCE_CONTRACT_V2", "pub-today")
        second_result = publish(TRADE_DATE, "SOURCE_CONTRACT_V2", "pub-today")
        date_25, date_28 = date(2026, 9, 25), date(2026, 9, 28)
        result_25 = publish(date_25, "SOURCE_CONTRACT_V2", "pub-25")
        result_28 = publish(date_28, "SOURCE_CONTRACT_V2", "pub-26")

        # Reprocessing D2 invalidates D3 and D4. The ordered replay writer
        # must rebuild D3 first, then D4 from the newly accepted D3 head.
        revised_d2 = publish(TRADE_DATE, "SOURCE_CONTRACT_V2", "pub-today")
        with PostgresRepository(dsn=isolated_dsn) as repository:
            for revision, run_id in ((1, first_result["focus_run_id"]),
                                     (2, second_result["focus_run_id"]),
                                     (3, revised_d2["focus_run_id"])):
                with repository.connection.cursor() as cur:
                    cur.execute("""insert into workbench.focus_episode_anchors
                        (anchor_id,episode_id,anchor_type,trade_date,focus_run_id,source_revision,
                         reference_price,price_basis,quality_status,source_fact_digest)
                        values (%s,%s,'INVALIDATION',%s,%s,%s,10,
                                'TDX_NATIVE_AFFINE_QFQ','READY',%s)""",
                        (f"anchor-revision-{revision}", EPISODE_ID, TRADE_DATE,
                         run_id, revision, digest({"revision": revision, "episode": EPISODE_ID})))
            due = due_anchor_plan(repository,
                                  calendar=(FIRST_DATE, TRADE_DATE, date_25, date_28),
                                  as_of_date=date_28)
            accepted_revision_anchors = sorted({item.anchor_id for item in due})
            accepted_due_horizons = sorted(item.horizon for item in due)
            repository.connection.rollback()
        with PostgresRepository(dsn=isolated_dsn) as repository:
            replay_dates = [item.trade_date.isoformat()
                            for item in __import__("src.focus_tracker.replay", fromlist=["pending_replay_chain"])
                            .pending_replay_chain(repository)]
            repository.connection.rollback()
            try:
                from src.focus_tracker.daily_head_plan import read_daily_head_plan
                read_daily_head_plan(repository, trade_date=date_28)
                out_of_order_blocked = False
            except ValueError as exc:
                out_of_order_blocked = "REPLAY_REQUIRED" in str(exc)
            repository.connection.rollback()
        with tempfile.TemporaryDirectory(prefix="focus-replay-e2e-") as replay_artifacts:
            replay_writer._dsn = lambda: isolated_dsn
            replay_writer.ROOT = Path(replay_artifacts)
            replay_writer.run_daily = lambda *, trade_date, apply: {
                "core_status": "ACTIVATED", "trade_date": trade_date.isoformat(),
                "planned_revision": publish(
                    trade_date, "SOURCE_CONTRACT_V2",
                    "pub-25" if trade_date == date_25 else "pub-26")["revision"]}
            replay_result = replay_writer.replay_chain(apply=True, max_days=5)
        with psycopg.connect(isolated_dsn) as con:
            row = con.execute("""select h.accepted_focus_run_id,h.lineage_state,
                o.membership_phase,e.selection_contract_family,
                (select count(*) from workbench.focus_episode_segments s
                 where s.episode_id=e.episode_id)
                from workbench.focus_trade_date_heads h
                join workbench.focus_episode_observations o
                  on o.focus_run_id=h.accepted_focus_run_id and o.trade_date=h.trade_date
                join workbench.focus_episodes e using(episode_id)
                where h.trade_date=%s""", (TRADE_DATE,)).fetchone()
            source_contracts = con.execute("""select source_model_contract_id
                from workbench.focus_episode_segments s
                join workbench.focus_trade_date_heads h on h.accepted_focus_run_id=s.focus_run_id
                  and h.lineage_state='VALID'
                where s.episode_id=%s order by s.start_trade_date""",
                (EPISODE_ID,)).fetchall()
            revisions = con.execute("""select source_revision,count(*)
                from workbench.focus_episode_observations where episode_id=%s and trade_date=%s
                group by source_revision order by source_revision""",
                (EPISODE_ID, TRADE_DATE)).fetchall()
            replay_heads = con.execute("""select trade_date,accepted_revision,lineage_state
                from workbench.focus_trade_date_heads where trade_date=any(%s) order by trade_date""",
                ([date_25, date_28],)).fetchall()
            replay_phases = con.execute("""select trade_date,membership_phase,source_revision
                from workbench.focus_episode_observations where episode_id=%s and trade_date=any(%s)
                and source_revision=2 order by trade_date""",
                (EPISODE_ID, [date_25, date_28])).fetchall()
            projection = con.execute("""select active_episode_id,latest_trade_date
                from workbench.focus_current_projection where entity_id=%s""",
                (SECURITY_ID,)).fetchone()
        checks = {"activated_revision_head": bool(row and row[0] == revised_d2["focus_run_id"]
                                                  and row[1] == "VALID"),
                  "source_model_boundary_observed": bool(row and row[2] == "SOURCE_MODEL_BOUNDARY"),
                  "episode_selection_contract_preserved": bool(row and row[3] == "V3_SHORTLIST_FAMILY_V1"),
                  "both_source_contract_segments_read_back":
                      [str(item[0]) for item in source_contracts] ==
                      ["SOURCE_CONTRACT_V1", "SOURCE_CONTRACT_V2"],
                  "same_day_revision_activated": bool(
                      first_result["revision"] == 1 and second_result["revision"] == 2 and
                      revised_d2["revision"] == 3 and row and
                      row[0] == revised_d2["focus_run_id"]),
                  "superseded_revision_anchors_hidden_from_due_settlement":
                      accepted_revision_anchors == ["anchor-revision-3"] and
                      accepted_due_horizons == [1],
                  "both_same_day_observation_revisions_preserved":
                      [(int(revision), int(count)) for revision, count in revisions] ==
                      [(1, 1), (2, 1), (3, 1)],
                  "boundary_does_not_repeat_on_next_session": bool(
                      result_25["revision"] == 1 and result_28["revision"] == 1 and
                      replay_phases[:1] == [(date_25, "PERSISTENT", 2)]),
                  "out_of_order_replay_is_blocked": out_of_order_blocked,
                  "ordered_replay_rebuilt_oldest_first": bool(
                      replay_result["status"] == "PASS" and replay_result["write_count"] == 2 and
                      replay_result["trade_dates"] == [date_25.isoformat(), date_28.isoformat()]),
                  "replay_heads_advanced_in_order":
                      [(day, revision, state) for day, revision, state in replay_heads] ==
                      [(date_25, 2, "VALID"), (date_28, 2, "VALID")],
                  "current_projection_tracks_same_episode": bool(projection and
                      projection[0] == EPISODE_ID and projection[1] == date_28)}
        if not all(checks.values()):
            raise RuntimeError("SOURCE_MODEL_BOUNDARY_E2E_READBACK_FAILED:" +
                               json.dumps({"checks": checks, "head_row": row,
                                           "source_contracts": source_contracts,
                                           "revisions": revisions,
                                           "accepted_revision_anchors": accepted_revision_anchors,
                                           "accepted_due_horizons": accepted_due_horizons,
                                           "replay_heads": replay_heads,
                                           "replay_result": replay_result,
                                           "projection": projection}, default=str))
        return {"contract_id": CONTRACT_ID, "status": "PASS", "checks": checks,
                "focus_run_id": revised_d2["focus_run_id"],
                "superseded_focus_run_id": first_result["focus_run_id"],
                "episode_id": EPISODE_ID,
                "trade_date": TRADE_DATE.isoformat(), "revision": revised_d2["revision"],
                "source_contracts": [str(item[0]) for item in source_contracts],
                "ordered_replay": replay_result,
                "database_is_disposable": True,
                "completed_at_utc": datetime.now(timezone.utc).isoformat()}
    finally:
        with psycopg.connect(original_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("drop database if exists {} with (force)")
                          .format(sql.Identifier(database_name)))


def main() -> int:
    result = run_probe()
    receipt = ROOT / "docs/evidence/FOCUS_SOURCE_MODEL_BOUNDARY_E2E_20260924.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    temp = receipt.with_name(receipt.name + "." + uuid.uuid4().hex + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True,
                               indent=2) + "\n", encoding="utf-8")
    temp.replace(receipt)
    result["receipt_path"] = str(receipt)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
