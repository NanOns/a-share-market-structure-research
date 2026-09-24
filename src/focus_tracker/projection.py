"""Rebuild the mutable Focus current projection from one accepted core run."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from psycopg import sql

from .contracts import SOURCE_AUTHORITY_CONTRACT, digest


CONTRACT_ID = "FOCUS_CURRENT_PROJECTION_REBUILD_V1"
COMPLETED = frozenset({"FOLLOW_UP_COMPLETED"})


@dataclass(frozen=True)
class ProjectionRow:
    source_family: str
    entity_type: str
    entity_id: str
    active_episode_id: str | None
    last_episode_id: str
    latest_trade_date: date
    latest_focus_run_id: str
    source_membership_state: str
    membership_phase: str
    validity_state: str
    followup_state: str
    current_path_state: str
    projection_digest: str


def projection_rows_for_run(repository, focus_run_id: str) -> tuple[ProjectionRow, ...]:
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select h.trade_date,r.core_publication_status,h.lineage_state "
            "from {}.focus_trade_date_heads h join {}.focus_runs r "
            "on r.focus_run_id=h.accepted_focus_run_id "
            "where h.accepted_focus_run_id=%s "
            "and h.source_authority_contract_id=%s").format(schema, schema),
            (focus_run_id, SOURCE_AUTHORITY_CONTRACT))
        heads = cur.fetchall()
        if len(heads) != 1 or heads[0][1] != "ACTIVATED" or heads[0][2] != "VALID":
            raise ValueError("projection source is not a valid accepted run")
        trade_date = heads[0][0]
        cur.execute(sql.SQL(
            "select accepted_focus_run_id,lineage_state from {}.focus_trade_date_heads "
            "where source_authority_contract_id=%s and lineage_state='VALID' "
            "order by trade_date desc limit 1"
        ).format(schema), (SOURCE_AUTHORITY_CONTRACT,))
        latest = cur.fetchone()
        if latest != (focus_run_id, "VALID"):
            raise ValueError("projection rebuild requires the latest valid head")
        cur.execute(sql.SQL(
            "select e.source_family,e.entity_type,e.entity_id,e.episode_id,"
            "o.source_membership_state,o.membership_phase,o.validity_state,"
            "o.followup_state,o.current_path_state,o.source_revision,"
            "o.state_contract_id,o.fact_digest "
            "from {}.focus_episode_observations o "
            "join {}.focus_episodes e using(episode_id) "
            "where o.focus_run_id=%s and o.trade_date=%s "
            "and o.evaluation_mode='AS_RECORDED' "
            "order by e.source_family,e.entity_type,e.entity_id").format(schema, schema),
            (focus_run_id, trade_date))
        observations = cur.fetchall()
    seen: set[tuple[str, str, str]] = set()
    result = []
    for (family, entity_type, entity_id, episode, membership, phase, validity,
         followup, path, revision, state_contract, fact_digest) in observations:
        identity = (str(family), str(entity_type), str(entity_id))
        if identity in seen:
            raise ValueError("duplicate projection source observation")
        seen.add(identity)
        active_episode = str(episode) if str(membership) not in {"NONE", "UNKNOWN"} else None
        evidence = {"contract_id": CONTRACT_ID, "run_id": focus_run_id,
                    "trade_date": trade_date, "identity": identity,
                    "episode_id": str(episode), "source_revision": int(revision),
                    "state_contract_id": str(state_contract),
                    "fact_digest": str(fact_digest), "membership": str(membership),
                    "phase": str(phase), "validity": str(validity),
                    "followup": str(followup), "path": str(path)}
        result.append(ProjectionRow(*identity, active_episode, str(episode),
                                    trade_date, focus_run_id, str(membership),
                                    str(phase), str(validity), str(followup),
                                    str(path), digest(evidence)))
    if not result:
        raise ValueError("accepted run contains no observation projection rows")
    return tuple(result)


def rebuild_current_projection(repository, *, focus_run_id: str) -> tuple[ProjectionRow, ...]:
    """Replace projection atomically from immutable AS_RECORDED observations."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    rows = projection_rows_for_run(repository, focus_run_id)
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("delete from {}.focus_current_projection").format(schema))
        for row in rows:
            cur.execute(sql.SQL(
                "insert into {}.focus_current_projection "
                "(source_family,entity_type,entity_id,active_episode_id,last_episode_id,"
                "latest_trade_date,latest_focus_run_id,source_membership_state,"
                "membership_phase,validity_state,followup_state,current_path_state,"
                "projection_digest) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            ).format(schema),
                (row.source_family, row.entity_type, row.entity_id,
                 row.active_episode_id, row.last_episode_id,
                 row.latest_trade_date, row.latest_focus_run_id,
                 row.source_membership_state, row.membership_phase,
                 row.validity_state, row.followup_state,
                 row.current_path_state, row.projection_digest))
        cur.execute(sql.SQL("select count(*) from {}.focus_current_projection "
                            "where latest_focus_run_id=%s").format(schema),
                    (focus_run_id,))
        if int(cur.fetchone()[0]) != len(rows):
            raise ValueError("projection rebuild row count mismatch")
    return rows


def verify_current_projection(repository, *, focus_run_id: str) -> bool:
    expected = projection_rows_for_run(repository, focus_run_id)
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select source_family,entity_type,entity_id,active_episode_id,last_episode_id,"
            "latest_trade_date,latest_focus_run_id,source_membership_state,membership_phase,"
            "validity_state,followup_state,current_path_state,projection_digest "
            "from {}.focus_current_projection "
            "order by source_family,entity_type,entity_id").format(schema))
        actual = tuple(cur.fetchall())
    expected_tuples = tuple((row.source_family, row.entity_type, row.entity_id,
                             row.active_episode_id, row.last_episode_id,
                             row.latest_trade_date, row.latest_focus_run_id,
                             row.source_membership_state, row.membership_phase,
                             row.validity_state, row.followup_state,
                             row.current_path_state, row.projection_digest)
                            for row in expected)
    return actual == expected_tuples
