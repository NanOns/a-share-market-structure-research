"""FOCUS-05 read-only API over one PostgreSQL snapshot per request."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import psycopg
from psycopg import sql

from workbench_db.postgres_repository import PostgresRepository
from .contracts import SOURCE_AUTHORITY_CONTRACT


API_CONTRACT = "FOCUS_READ_API_V1"
UI_CONTRACT = "FOCUS_TRACKER_UI_V1"
MAX_PAGE_SIZE = 100
STATISTICS_MIN_ROWS = 30
STATISTICS_MIN_SIGNAL_DATES = 5


def _json(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value


def _rows(cur) -> list[dict[str, Any]]:
    names = [column.name for column in cur.description]
    return [{name: _json(value) for name, value in zip(names, row)}
            for row in cur.fetchall()]


class FocusTrackerReadAPI:
    """Resolve a run once, then use its identity for every query in a request."""

    def __init__(self, *, dsn: str | None = None, env_file: str | Path | None = None,
                 schema: str = "workbench", repository_factory=PostgresRepository):
        self.dsn = dsn or os.environ.get("WORKBENCH_PG_DSN")
        if not self.dsn and env_file and Path(env_file).is_file():
            for line in Path(env_file).read_text("utf-8").splitlines():
                key, sep, value = line.partition("=")
                if sep and key.strip() == "WORKBENCH_PG_DSN":
                    self.dsn = value.strip().strip('"').strip("'")
                    break
        self.schema = schema
        self.repository_factory = repository_factory

    def handle(self, path: str, params: dict[str, str]) -> tuple[int, dict[str, Any]]:
        try:
            fixed_routes = {"/api/v3/focus-tracker/summary", "/api/v3/focus-tracker/items",
                            "/api/v3/focus-tracker/transitions", "/api/v3/focus-tracker/runs",
                            "/api/v3/focus-tracker/statistics",
                            "/api/v3/focus-tracker/sectors/catalog"}
            dynamic_routes = ("/api/v3/focus-tracker/episodes/",
                              "/api/v3/focus-tracker/stocks/",
                              "/api/v3/focus-tracker/sectors/")
            if path not in fixed_routes and not any(
                    path.startswith(prefix) and path[len(prefix):].strip("/")
                    for prefix in dynamic_routes):
                return 404, {"api_contract": API_CONTRACT, "status": "NOT_FOUND",
                             "data_status": "UNAVAILABLE"}
            if not self.dsn:
                return 503, {"api_contract": API_CONTRACT, "status": "PG_UNAVAILABLE",
                             "data_status": "UNAVAILABLE", "retryable": True,
                             "message": "PostgreSQL DSN 未配置；未尝试其他数据源。"}
            if params.get("trade_date"):
                date.fromisoformat(params["trade_date"])
            with self.repository_factory(dsn=self.dsn, schema=self.schema,
                                         statement_timeout_ms=5000) as repository:
                conn = repository.connection
                if conn is None:
                    raise psycopg.OperationalError("connection not open")
                with conn.cursor() as cur:
                    cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    run = self._resolve_run(cur, params.get("focus_run_id"),
                                            params.get("trade_date"))
                    if run is None:
                        cur.execute(sql.SQL(
                            "select exists(select 1 from {}.focus_trade_date_heads "
                            "where source_authority_contract_id=%s "
                            "and lineage_state='REPLAY_REQUIRED')").format(sql.Identifier(self.schema)),
                            (SOURCE_AUTHORITY_CONTRACT,))
                        replay_pending = bool(cur.fetchone()[0])
                        conn.rollback()
                        return 200, self._no_run(replay_pending=replay_pending)
                    if run.get("lineage_state") == "REPLAY_REQUIRED":
                        conn.rollback()
                        return 409, {**self._meta(run), "status": "REPLAY_REQUIRED",
                                     "items": [], "data_status": "UNAVAILABLE"}
                    payload = self._dispatch(cur, path, params, run)
                conn.rollback()
                return (404 if payload.get("status") == "NOT_FOUND" else 200), payload
        except ValueError as exc:
            return 400, {"api_contract": API_CONTRACT,
                         "status": "INVALID_REQUEST", "code": str(exc),
                         "retryable": False}
        except psycopg.Error:
            return 503, {"api_contract": API_CONTRACT, "status": "PG_UNAVAILABLE",
                         "data_status": "UNAVAILABLE", "retryable": True,
                         "message": "PostgreSQL 暂不可用；未切换到其他数据源。"}

    def _resolve_run(self, cur, requested_run_id: str | None,
                     requested_trade_date: str | None = None) -> dict[str, Any] | None:
        schema = sql.Identifier(self.schema)
        if requested_run_id:
            cur.execute(sql.SQL(
                "select r.focus_run_id,r.trade_date,r.revision,r.publication_id,"
                "r.source_authority_contract_id,r.source_family_set,r.family_capabilities,"
                "r.state_contract_id,r.parameter_set_id,r.evaluation_basis,"
                "r.core_publication_status,r.outcome_settlement_status,r.activated_at_utc,"
                "coalesce(h.lineage_state,'HISTORICAL') as lineage_state,"
                "exists(select 1 from {}.focus_trade_date_heads vh "
                "where vh.accepted_focus_run_id=r.focus_run_id "
                "and vh.source_authority_contract_id=r.source_authority_contract_id "
                "and vh.lineage_state='VALID') as is_current_head "
                "from {}.focus_runs r left join {}.focus_trade_date_heads h "
                "on h.accepted_focus_run_id=r.focus_run_id "
                "and h.source_authority_contract_id=r.source_authority_contract_id "
                "where r.focus_run_id=%s and r.core_publication_status='ACTIVATED' "
                "and (coalesce(%s::text,'')='' or r.trade_date=%s::date) "
                "order by (h.lineage_state='REPLAY_REQUIRED') desc limit 1").format(
                    schema, schema, schema),
                (requested_run_id, requested_trade_date, requested_trade_date))
        else:
            cur.execute(sql.SQL(
                "select r.focus_run_id,r.trade_date,r.revision,r.publication_id,"
                "r.source_authority_contract_id,r.source_family_set,r.family_capabilities,"
                "r.state_contract_id,r.parameter_set_id,r.evaluation_basis,"
                "r.core_publication_status,r.outcome_settlement_status,r.activated_at_utc,"
                "h.lineage_state,true as is_current_head "
                "from {}.focus_trade_date_heads h join {}.focus_runs r "
                "on r.focus_run_id=h.accepted_focus_run_id "
                "where h.source_authority_contract_id=%s and h.lineage_state='VALID' "
                "and r.core_publication_status='ACTIVATED' "
                "and (coalesce(%s::text,'')='' or h.trade_date=%s::date) "
                "and not exists(select 1 from {}.focus_trade_date_heads rh "
                "where rh.source_authority_contract_id=h.source_authority_contract_id "
                "and rh.lineage_state='REPLAY_REQUIRED') "
                "order by h.trade_date desc limit 1").format(schema, schema, schema),
                (SOURCE_AUTHORITY_CONTRACT, requested_trade_date, requested_trade_date))
        row = cur.fetchone()
        if row is None:
            return None
        keys = ("focus_run_id", "trade_date", "revision", "publication_id",
                "source_authority_contract_id", "source_family_set", "family_capabilities",
                "state_contract_id", "parameter_set_id", "evaluation_basis",
                "core_publication_status", "outcome_settlement_status", "activated_at_utc",
                "lineage_state", "is_current_head")
        result = dict(zip(keys, row))
        if result["source_authority_contract_id"] != SOURCE_AUTHORITY_CONTRACT:
            return None
        if requested_trade_date and str(result["trade_date"]) != requested_trade_date:
            return None
        return {key: _json(value) for key, value in result.items()}

    def _meta(self, run: dict[str, Any]) -> dict[str, Any]:
        return {"api_contract": API_CONTRACT, "focus_run_id": run["focus_run_id"],
                "trade_date": run["trade_date"], "revision": run["revision"],
                "publication_id": run["publication_id"],
                "source_authority_contract_id": run["source_authority_contract_id"],
                "source_family_set": run["source_family_set"],
                "family_capabilities": run["family_capabilities"],
                "state_contract_id": run["state_contract_id"],
                "parameter_set_id": run["parameter_set_id"],
                "evaluation_basis": run["evaluation_basis"],
                "lineage_state": run["lineage_state"],
                "is_current_head": run["is_current_head"],
                "data_status": "AVAILABLE"}

    def _no_run(self, *, replay_pending: bool = False) -> dict[str, Any]:
        return {"api_contract": API_CONTRACT,
                "status": "REPLAY_REQUIRED" if replay_pending else "NO_ACCEPTED_RUN",
                "focus_run_id": None, "trade_date": None, "revision": None,
                "source_authority_contract_id": SOURCE_AUTHORITY_CONTRACT, "groups": [],
                "data_status": "UNAVAILABLE", "items": [], "total": 0,
                "message": "存在待重放交易日，当前 head 不可展示。" if replay_pending
                else "当前没有有效且已激活的 Focus run。"}

    def _dispatch(self, cur, path: str, params: dict[str, str],
                  run: dict[str, Any]) -> dict[str, Any]:
        if path == "/api/v3/focus-tracker/summary":
            return self._summary(cur, run)
        if path == "/api/v3/focus-tracker/items":
            return self._items(cur, params, run)
        if path == "/api/v3/focus-tracker/transitions":
            return self._transitions(cur, params, run)
        if path == "/api/v3/focus-tracker/runs":
            return self._runs(cur, params, run)
        if path == "/api/v3/focus-tracker/statistics":
            return self._statistics(cur, run)
        prefix = "/api/v3/focus-tracker/episodes/"
        if path.startswith(prefix):
            return self._episode(cur, unquote(path[len(prefix):]).strip("/"), run)
        members_prefix = "/api/v3/focus-tracker/sectors/"
        if path.startswith(members_prefix) and path.endswith("/members"):
            sector_id = unquote(path[len(members_prefix):-len("/members")].strip("/"))
            return self._sector_members(cur, sector_id, params, run)
        if path == "/api/v3/focus-tracker/sectors/catalog":
            return self._sector_catalog(cur, run)
        for entity_type, route in (("STOCK", "/api/v3/focus-tracker/stocks/"),
                                   ("SECTOR", "/api/v3/focus-tracker/sectors/")):
            if path.startswith(route):
                return self._entity(cur, entity_type,
                                    unquote(path[len(route):]).strip("/"), run)
        return {**self._meta(run), "status": "NOT_FOUND", "items": []}

    def _sector_catalog(self, cur, run: dict[str, Any]) -> dict[str, Any]:
        schema = sql.Identifier(self.schema)
        cur.execute(sql.SQL(
            "with sector_ids as (select entity_id as sector_id from {}.focus_daily_items "
            "where focus_run_id=%s and entity_type='SECTOR' union select sector_id "
            "from {}.focus_stock_sector_links where focus_run_id=%s union "
            "select source_facts->>'primary_sector_id' from {}.focus_daily_items "
            "where focus_run_id=%s and nullif(source_facts->>'primary_sector_id','') is not null union "
            "select jsonb_array_elements_text(coalesce(source_facts->'alternative_sector_ids','[]'::jsonb)) "
            "from {}.focus_daily_items where focus_run_id=%s) "
            "select distinct s.sector_id,a.name,a.type from sector_ids s "
            "left join {}.relation_publication_bindings b on b.publication_id=%s "
            "left join {}.sector_attribute_revisions r on r.source_scope=b.source_scope "
            "and substring(r.attribute_set_hash,1,24)=replace(b.attribute_version_id,'attrset-','') "
            "left join {}.sector_attribute_revision_bindings ab on ab.source_scope=b.source_scope "
            "and ab.sector_id=s.sector_id and ab.from_attribute_revision<=r.attribute_revision "
            "and (ab.to_attribute_revision is null or r.attribute_revision<ab.to_attribute_revision) "
            "left join {}.sector_attribute_versions a on a.source_scope=ab.source_scope "
            "and a.attribute_version_id=ab.attribute_version_id "
            "order by s.sector_id").format(schema, schema, schema, schema, schema, schema, schema, schema),
            (run["focus_run_id"], run["focus_run_id"], run["focus_run_id"],
             run["focus_run_id"], run["publication_id"]))
        return {**self._meta(run), "status": "AVAILABLE", "items": _rows(cur)}

    def _sector_members(self, cur, sector_id: str, params: dict[str, str],
                        run: dict[str, Any]) -> dict[str, Any]:
        schema = sql.Identifier(self.schema)
        page, size = self._page(params)
        cur.execute(sql.SQL(
            "select b.episode_id,b.member_ids,b.basket_digest from {}.focus_episode_baskets b "
            "join {}.focus_episodes e on e.episode_id=b.episode_id "
            "where b.focus_run_id=%s and e.entity_type='SECTOR' and e.entity_id=%s "
            "order by e.first_trade_date desc limit 1").format(schema, schema),
            (run["focus_run_id"], sector_id))
        basket = cur.fetchone()
        if not basket:
            return {**self._meta(run), "status": "AVAILABLE", "sector_id": sector_id,
                    "items": [], "total": 0, "page": page, "page_size": size,
                    "has_more": False}
        sector_episode_id, raw_member_ids, basket_digest = basket
        member_ids = [str(value) for value in raw_member_ids]
        total = len(member_ids)
        cur.execute(sql.SQL(
            "select o.facts#>>array['predicate_facts','strength_fact_digest'] "
            "from {}.focus_episode_observations o where o.episode_id=%s and o.focus_run_id=%s "
            "and o.evaluation_mode='AS_RECORDED' limit 1").format(schema),
            (sector_episode_id, run["focus_run_id"]))
        digest_row = cur.fetchone()
        expected_strength_digest = str(digest_row[0]) if digest_row and digest_row[0] else None
        strength_by_security: dict[str, bool | None] = {}
        if expected_strength_digest:
            cur.execute(sql.SQL(
                "select h.snapshot_id,h.domain,e.slice_id,ro.result_object_id,ro.value_hash,"
                "ro.semantic_contract,r.security_id,r.strong_state "
                "from {}.analysis_snapshot_heads h "
                "join {}.analysis_snapshots s on s.snapshot_id=h.snapshot_id and s.status='SUCCESS' "
                "and s.cutoff_date=h.trade_date "
                "join {}.analysis_snapshot_entries e on e.snapshot_id=h.snapshot_id "
                "and e.domain='member_state' and e.trade_date=h.trade_date "
                "join {}.analysis_slice_result_bindings rb on rb.slice_id=e.slice_id "
                "join {}.analysis_result_objects ro on ro.result_object_id=rb.result_object_id "
                "and ro.domain='member_state' and ro.semantic_contract='MEMBER_STATE_RESULT_V3' "
                "join {}.member_state_result_rows r on r.result_object_id=ro.result_object_id "
                "and r.trade_date=e.trade_date and r.sector_id=%s and r.member_present "
                "and r.contract_id='SECTOR_MEMBER_STATE_V1_2_EXCLUDE_DIAGNOSTIC' "
                "where h.trade_date=%s and h.publication_id=%s and r.security_id=any(%s) "
                "order by h.domain,r.security_id").format(
                    schema, schema, schema, schema, schema, schema),
                (sector_id, run["trade_date"], run["publication_id"], member_ids))
            candidate_rows = _rows(cur)
            grouped: dict[tuple[str, str, str, str, str, str], dict[str, bool | None]] = {}
            for row in candidate_rows:
                identity = (row["snapshot_id"], row["domain"], row["slice_id"],
                            row["result_object_id"], row["value_hash"], row["semantic_contract"])
                grouped.setdefault(identity, {})[row["security_id"]] = row["strong_state"]
            from .member_strength import CONTRACT_ID, SOURCE_MEMBER_CONTRACT
            from .contracts import digest
            for (snapshot_id, _domain, slice_id, result_id, value_hash, semantic), states in grouped.items():
                if set(states) != set(member_ids):
                    continue
                evidence = {"contract": CONTRACT_ID, "trade_date": run["trade_date"],
                            "publication_id": run["publication_id"], "snapshot_id": str(snapshot_id),
                            "slice_id": str(slice_id), "result_object_id": str(result_id),
                            "result_value_hash": str(value_hash),
                            "result_semantic_contract": str(semantic),
                            "member_contract": SOURCE_MEMBER_CONTRACT, "sector_id": sector_id,
                            "basket_digest": str(basket_digest),
                            "member_states": [(security, states[security]) for security in sorted(states)]}
                if digest(evidence) == expected_strength_digest:
                    strength_by_security = states
                    break
        ordered_ids = sorted(member_ids, key=lambda security: (
            0 if strength_by_security.get(security) is True else
            1 if strength_by_security.get(security) is False else 2, security))
        page_ids = ordered_ids[(page - 1) * size:page * size]
        items: list[dict[str, Any]] = []
        if page_ids:
            cur.execute(sql.SQL(
                "with members as (select value as security_id,ord from unnest(%s::text[]) "
                "with ordinality x(value,ord)) "
                "select m.security_id,coalesce(stock.source_facts->>'security_name',first_item.source_facts->>'security_name',"
                "sd.security_name) as security_name,stock.source_membership_state,obs.episode_id,"
                "obs.membership_phase,obs.validity_state,obs.current_path_state,obs.followup_state,"
                "obs.continuity_quality,obs.close_price,obs.return_since_first,obs.quality_status "
                "from members m left join lateral (select d.* from {}.focus_daily_items d "
                "where d.focus_run_id=%s and d.entity_type='STOCK' and d.entity_id=m.security_id "
                "order by case d.source_family when 'V3_SHORTLIST_STOCK' then 0 when 'V3_SHORTLIST_INDIVIDUAL' then 1 else 2 end, "
                "d.source_rank nulls last limit 1) stock on true "
                "left join lateral (select d.source_facts from {}.focus_episodes e "
                "join {}.focus_daily_items d on d.focus_run_id=e.first_focus_run_id and d.source_family=e.source_family "
                "and d.entity_type=e.entity_type and d.entity_id=e.entity_id where e.entity_type='STOCK' "
                "and e.entity_id=m.security_id order by e.first_trade_date desc limit 1) first_item on true "
                "left join {}.focus_episode_observations obs on obs.episode_id=(select e.episode_id "
                "from {}.focus_episodes e join {}.focus_episode_observations o on o.episode_id=e.episode_id "
                "and o.focus_run_id=%s and o.evaluation_mode='AS_RECORDED' where e.entity_type='STOCK' "
                "and e.entity_id=m.security_id order by e.first_trade_date desc limit 1) "
                "and obs.focus_run_id=%s and obs.evaluation_mode='AS_RECORDED' "
                "left join {}.stock_daily sd on sd.publication_id=%s and sd.security_id=m.security_id "
                "order by m.ord").format(schema, schema, schema, schema, schema, schema, schema),
                (page_ids, run["focus_run_id"], run["focus_run_id"], run["focus_run_id"],
                 run["publication_id"]))
            items = _rows(cur)
            for item in items:
                item["strong_state"] = strength_by_security.get(item["security_id"])
                item["strength_status"] = "KNOWN" if item["security_id"] in strength_by_security else "UNKNOWN"
        return {**self._meta(run), "status": "AVAILABLE", "sector_id": sector_id,
                "items": items, "total": total, "page": page, "page_size": size,
                "has_more": page * size < total}

    def _summary(self, cur, run: dict[str, Any]) -> dict[str, Any]:
        schema = sql.Identifier(self.schema)
        cur.execute(sql.SQL(
            "select source_family, count(*)::int as item_count "
            "from {}.focus_daily_items where focus_run_id=%s "
            "group by source_family order by source_family").format(schema),
            (run["focus_run_id"],))
        families = _rows(cur)
        cur.execute(sql.SQL(
            "select o.validity_state,o.current_path_state,o.followup_state,count(*)::int count "
            "from {}.focus_episode_observations o where o.focus_run_id=%s "
            "and o.evaluation_mode='AS_RECORDED' group by 1,2,3 order by 1,2,3").format(schema),
            (run["focus_run_id"],))
        state_counts = _rows(cur)
        return {**self._meta(run), "status": "AVAILABLE", "focus_type_counts": families,
                "state_counts": state_counts,
                "total_items": sum(row["item_count"] for row in families)}

    @staticmethod
    def _page(params: dict[str, str]) -> tuple[int, int]:
        try:
            page = max(1, int(params.get("page", "1")))
            page_size = min(MAX_PAGE_SIZE, max(1, int(params.get("page_size", "25"))))
        except (TypeError, ValueError):
            raise ValueError("INVALID_PAGINATION")
        return page, page_size

    def _items(self, cur, params: dict[str, str], run: dict[str, Any]) -> dict[str, Any]:
        schema = sql.Identifier(self.schema)
        page, size = self._page(params)
        conditions = [sql.SQL("i.focus_run_id=%s")]
        values: list[Any] = [run["focus_run_id"]]
        allowed = {"source_family": "i.source_family",
                   "membership": "i.source_membership_state",
                   "validity": "i.validity_state", "path": "i.current_path_state",
                   "quality": "i.source_quality", "entity_type": "i.entity_type"}
        for key, column in allowed.items():
            if params.get(key):
                conditions.append(sql.SQL("{}=%s").format(sql.SQL(column)))
                values.append(params[key])
        if params.get("scenario"):
            conditions.append(sql.SQL(
                "coalesce(i.source_facts->>'scenario',i.source_facts->>'scenario_id',"
                "i.source_facts->>'primary_category',i.source_facts->>'source_focus_class')=%s"))
            values.append(params["scenario"])
        if params.get("sector_id"):
            sector_filter = params["sector_id"]
            if sector_filter == "__SUPPORT_CONFIRMED__":
                conditions.append(sql.SQL("i.source_facts->>'sector_support_status'='CONFIRMED'"))
            elif sector_filter == "__SUPPORT_UNCONFIRMED__":
                conditions.append(sql.SQL("i.source_facts->>'sector_support_status'='NOT_CONFIRMED'"))
            else:
                conditions.append(sql.SQL(
                    "(exists(select 1 from {}.focus_stock_sector_links l "
                    "where l.focus_run_id=i.focus_run_id and l.security_id=i.entity_id "
                    "and l.sector_id=%s) or i.source_facts->>'primary_sector_id'=%s "
                    "or coalesce(i.source_facts->'alternative_sector_ids','[]'::jsonb) "
                    "@> jsonb_build_array(%s::text))").format(schema))
                values.extend((sector_filter, sector_filter, sector_filter))
        where = sql.SQL(" and ").join(conditions)
        cte = sql.SQL(
            "with current_items as ("
            "select d.source_family,d.entity_type,d.entity_id,d.selection_contract_family,"
            "d.source_item_key,d.source_item_digest,d.source_contract_id,d.source_membership_state,"
            "d.source_focus_class,d.source_rank,d.source_quality,d.source_facts,ep.episode_id,"
            "false as is_followup,o.membership_phase,o.validity_state,o.followup_state,"
            "o.current_path_state,o.lifetime_path_tags,o.continuity_quality,o.comparison_gap_sessions,"
            "o.entry_primary_sector_id,o.current_primary_sector_id,o.close_price,o.return_since_first,"
            "o.drawdown_from_peak,o.quality_status,d.focus_run_id,ep.first_trade_date,"
            "o.first_supported_anchor_id "
            "from {}.focus_daily_items d "
            "left join lateral (select e.episode_id,e.first_trade_date from {}.focus_episodes e "
            "join {}.focus_episode_observations oo on oo.episode_id=e.episode_id "
            "and oo.focus_run_id=d.focus_run_id and oo.evaluation_mode='AS_RECORDED' "
            "where e.source_family=d.source_family and e.entity_type=d.entity_type "
            "and e.entity_id=d.entity_id order by e.first_trade_date desc,e.episode_id limit 1) ep on true "
            "left join {}.focus_episode_observations o on o.episode_id=ep.episode_id "
            "and o.focus_run_id=d.focus_run_id and o.evaluation_mode='AS_RECORDED' "
            "where d.focus_run_id=%s), followups as ("
            "select e.source_family,e.entity_type,e.entity_id,e.selection_contract_family,"
            "null::text as source_item_key,null::char(64) as source_item_digest,null::text as source_contract_id,"
            "o.source_membership_state,null::text as source_focus_class,null::integer as source_rank,"
            "o.quality_status as source_quality,coalesce(src.source_facts,o.facts) as source_facts,"
            "e.episode_id,true as is_followup,"
            "o.membership_phase,o.validity_state,o.followup_state,o.current_path_state,o.lifetime_path_tags,"
            "o.continuity_quality,o.comparison_gap_sessions,o.entry_primary_sector_id,"
            "o.current_primary_sector_id,o.close_price,o.return_since_first,o.drawdown_from_peak,"
            "o.quality_status,o.focus_run_id,e.first_trade_date,o.first_supported_anchor_id "
            "from {}.focus_episode_observations o "
            "join {}.focus_episodes e on e.episode_id=o.episode_id "
            "left join lateral (select d.source_facts from {}.focus_daily_items d "
            "where d.focus_run_id=e.first_focus_run_id and d.source_family=e.source_family "
            "and d.entity_type=e.entity_type and d.entity_id=e.entity_id "
            "order by d.source_item_key limit 1) src on true "
            "where o.focus_run_id=%s and o.evaluation_mode='AS_RECORDED' "
            "and o.followup_state='ACTIVE_FOCUS' and not exists(select 1 from current_items c "
            "where c.episode_id=e.episode_id)), items as ("
            "select * from current_items union all select * from followups) ").format(
                schema, schema, schema, schema, schema, schema, schema)
        cte_values = [run["focus_run_id"], run["focus_run_id"]]
        cur.execute(cte + sql.SQL("select count(*)::int from items i where ") + where,
                    cte_values + values)
        total = int(cur.fetchone()[0])
        query = cte + sql.SQL(
            "select i.source_family,i.entity_type,i.entity_id,i.selection_contract_family,"
            "i.source_item_key,i.source_item_digest,i.source_contract_id,i.source_membership_state,"
            "i.source_focus_class,i.source_rank,i.source_quality,i.source_facts,"
            "coalesce(i.source_facts->>'security_name',(select sd.security_name from {}.stock_daily sd "
            "where sd.publication_id=%s and sd.security_id=i.entity_id limit 1)) as security_name,i.episode_id,"
            "i.is_followup,i.membership_phase,i.validity_state,i.followup_state,i.current_path_state,"
            "i.lifetime_path_tags,i.continuity_quality,i.comparison_gap_sessions,"
            "i.entry_primary_sector_id,i.current_primary_sector_id,i.close_price,"
            "i.return_since_first,i.drawdown_from_peak,i.quality_status,i.first_trade_date,"
            "case when i.episode_id is null then null else (select count(distinct so.trade_date)::int "
            "from {}.focus_episode_observations so where so.episode_id=i.episode_id "
            "and so.trade_date<=%s and so.evaluation_mode='AS_RECORDED') end as observed_session_count,"
            "i.first_supported_anchor_id "
            "from items i where ").format(schema, schema) + where + sql.SQL(
                " order by i.source_family,i.source_rank nulls last,i.entity_type,i.entity_id,i.episode_id "
                "limit %s offset %s")
        query_values = cte_values + [run["publication_id"], run["trade_date"]] + values
        cur.execute(query, query_values + [size, (page - 1) * size])
        items = _rows(cur)
        return {**self._meta(run), "status": "AVAILABLE", "items": items,
                "page": page, "page_size": size, "total": total,
                "returned_count": len(items), "has_more": page * size < total}

    def _episode(self, cur, episode_id: str, run: dict[str, Any]) -> dict[str, Any]:
        schema = sql.Identifier(self.schema)
        cur.execute(sql.SQL(
            "select e.episode_id,e.source_family,e.entity_type,e.entity_id,"
            "e.selection_contract_family,e.first_trade_date,e.first_focus_run_id,e.parent_episode_id,"
            "(select sd.security_name from {}.stock_daily sd join {}.focus_runs first_run "
            "on first_run.publication_id=sd.publication_id where first_run.focus_run_id=e.first_focus_run_id "
            "and sd.security_id=e.entity_id limit 1) as security_name "
            "from {}.focus_episodes e where e.episode_id=%s and e.first_trade_date<=%s")
            .format(schema, schema, schema), (episode_id, run["trade_date"]))
        episode_rows = _rows(cur)
        if not episode_rows:
            return {**self._meta(run), "status": "NOT_FOUND", "code": "EPISODE_NOT_FOUND"}
        cur.execute(sql.SQL(
            "select t.focus_run_id,t.source_revision,t.transition_trade_date,t.transition_type,"
            "t.from_membership,t.to_membership,t.reason_codes "
            "from {}.focus_episode_transitions t join {}.focus_runs r "
            "on r.focus_run_id=t.focus_run_id left join {}.focus_trade_date_heads h "
            "on h.accepted_focus_run_id=r.focus_run_id and h.lineage_state='VALID' "
            "where t.episode_id=%s and r.source_authority_contract_id=%s "
            "and (r.focus_run_id=%s or (r.trade_date<%s and h.accepted_focus_run_id is not null)) "
            "order by t.transition_trade_date,r.revision,t.transition_type").format(schema, schema, schema),
            (episode_id, SOURCE_AUTHORITY_CONTRACT, run["focus_run_id"], run["trade_date"]))
        transitions = _rows(cur)
        cur.execute(sql.SQL(
            "select a.anchor_id,a.anchor_type,a.trade_date,a.focus_run_id,a.source_revision,"
            "a.reference_price,a.price_basis,a.quality_status "
            "from {}.focus_episode_anchors a join {}.focus_runs r on r.focus_run_id=a.focus_run_id "
            "left join {}.focus_trade_date_heads h on h.accepted_focus_run_id=r.focus_run_id "
            "and h.lineage_state='VALID' where a.episode_id=%s "
            "and r.source_authority_contract_id=%s "
            "and (r.focus_run_id=%s or (r.trade_date<%s and h.accepted_focus_run_id is not null)) "
            "order by a.trade_date,r.revision,a.anchor_type,a.anchor_id").format(schema, schema, schema),
            (episode_id, SOURCE_AUTHORITY_CONTRACT, run["focus_run_id"], run["trade_date"]))
        anchors = _rows(cur)
        cur.execute(sql.SQL(
            "select o.trade_date,o.source_revision,o.evaluation_mode,o.state_contract_id,"
            "o.source_membership_state,o.membership_phase,o.validity_state,o.followup_state,"
            "o.current_path_state,o.lifetime_path_tags,o.continuity_quality,o.comparison_gap_sessions,"
            "o.entry_primary_sector_id,o.current_primary_sector_id,o.close_price,o.return_since_first,"
            "o.drawdown_from_peak,o.adjustment_source_hash,o.quality_status,o.fact_digest,o.facts "
            "from {}.focus_episode_observations o join {}.focus_runs r "
            "on r.focus_run_id=o.focus_run_id left join {}.focus_trade_date_heads h "
            "on h.accepted_focus_run_id=r.focus_run_id and h.lineage_state='VALID' "
            "where o.episode_id=%s and o.evaluation_mode='AS_RECORDED' "
            "and r.source_authority_contract_id=%s "
            "and (r.focus_run_id=%s or (r.trade_date<%s and h.accepted_focus_run_id is not null)) "
            "order by o.trade_date,o.source_revision,o.state_contract_id").format(schema, schema, schema),
            (episode_id, SOURCE_AUTHORITY_CONTRACT, run["focus_run_id"], run["trade_date"]))
        observations = _rows(cur)
        cur.execute(sql.SQL(
            "select o.anchor_id,o.horizon,o.accepted_target_revision,r.target_trade_date,"
            "r.status,r.evaluation_basis,r.forward_return,r.mfe,r.mae,r.mdd,r.reason_codes,r.evidence "
            "from {}.focus_outcome_heads o join {}.focus_episode_outcomes r "
            "on r.anchor_id=o.anchor_id and r.horizon=o.horizon "
            "and r.target_revision=o.accepted_target_revision "
            "join {}.focus_episode_anchors a on a.anchor_id=o.anchor_id "
            "join {}.focus_runs ar on ar.focus_run_id=a.focus_run_id "
            "where a.episode_id=%s and a.trade_date<=%s and r.target_trade_date<=%s "
            "and ar.source_authority_contract_id=%s "
            "and (ar.focus_run_id=%s or (ar.trade_date<%s and exists "
            "(select 1 from {}.focus_trade_date_heads h where h.accepted_focus_run_id=ar.focus_run_id "
            "and h.lineage_state='VALID'))) "
            "order by a.trade_date,o.horizon").format(
                schema, schema, schema, schema, schema),
            (episode_id, run["trade_date"], run["trade_date"], SOURCE_AUTHORITY_CONTRACT,
             run["focus_run_id"], run["trade_date"]))
        outcomes = _rows(cur)
        return {**self._meta(run), "status": "AVAILABLE", "episode": episode_rows[0],
                "transitions": transitions, "anchors": anchors,
                "observations": observations, "outcomes": outcomes}

    def _entity(self, cur, entity_type: str, entity_id: str,
                run: dict[str, Any]) -> dict[str, Any]:
        schema = sql.Identifier(self.schema)
        cur.execute(sql.SQL(
            "select e.episode_id,e.source_family,e.entity_type,e.entity_id,"
            "e.selection_contract_family,e.first_trade_date,e.first_focus_run_id,e.parent_episode_id "
            "from {}.focus_episodes e where e.entity_type=%s and e.entity_id=%s "
            "and e.first_trade_date<=%s order by e.first_trade_date desc,e.episode_id limit 51")
            .format(schema), (entity_type, entity_id, run["trade_date"]))
        episode_rows = _rows(cur)
        truncated = len(episode_rows) > 50
        episode_rows = episode_rows[:50]
        episode_ids = [episode["episode_id"] for episode in episode_rows]
        if not episode_ids:
            return {**self._meta(run), "status": "NOT_FOUND", "entity_type": entity_type,
                    "entity_id": entity_id, "episodes": [], "episodes_truncated": False}

        def grouped(query, params, key="episode_id"):
            cur.execute(query, params)
            result: dict[str, list[dict[str, Any]]] = {episode_id: [] for episode_id in episode_ids}
            for row in _rows(cur):
                result[row.pop(key)].append(row)
            return result

        transitions = grouped(sql.SQL(
            "select t.episode_id,t.focus_run_id,t.source_revision,t.transition_trade_date,"
            "t.transition_type,t.from_membership,t.to_membership,t.reason_codes "
            "from {}.focus_episode_transitions t join {}.focus_runs r "
            "on r.focus_run_id=t.focus_run_id where t.episode_id=any(%s) "
            "and r.source_authority_contract_id=%s "
            "and (r.focus_run_id=%s or (r.trade_date<%s and exists "
            "(select 1 from {}.focus_trade_date_heads h where h.accepted_focus_run_id=r.focus_run_id "
            "and h.lineage_state='VALID'))) "
            "order by t.episode_id,t.transition_trade_date,r.revision,t.transition_type")
            .format(schema, schema, schema),
            (episode_ids, SOURCE_AUTHORITY_CONTRACT, run["focus_run_id"], run["trade_date"]))
        anchors = grouped(sql.SQL(
            "select a.episode_id,a.anchor_id,a.anchor_type,a.trade_date,a.focus_run_id,"
            "a.source_revision,a.reference_price,a.price_basis,a.quality_status "
            "from {}.focus_episode_anchors a join {}.focus_runs r on r.focus_run_id=a.focus_run_id "
            "where a.episode_id=any(%s) and a.trade_date<=%s "
            "and r.source_authority_contract_id=%s "
            "and (r.focus_run_id=%s or (r.trade_date<%s and exists "
            "(select 1 from {}.focus_trade_date_heads h where h.accepted_focus_run_id=r.focus_run_id "
            "and h.lineage_state='VALID'))) "
            "order by a.episode_id,a.trade_date,r.revision,a.anchor_type,a.anchor_id")
            .format(schema, schema, schema),
            (episode_ids, run["trade_date"], SOURCE_AUTHORITY_CONTRACT,
             run["focus_run_id"], run["trade_date"]))
        observations = grouped(sql.SQL(
            "select o.episode_id,o.trade_date,o.source_revision,o.evaluation_mode,o.state_contract_id,"
            "o.source_membership_state,o.membership_phase,o.validity_state,o.followup_state,o.current_path_state,"
            "o.lifetime_path_tags,o.continuity_quality,o.comparison_gap_sessions,o.entry_primary_sector_id,"
            "o.current_primary_sector_id,o.first_supported_anchor_id,o.close_price,o.return_since_first,"
            "o.drawdown_from_peak,o.adjustment_source_hash,o.quality_status,o.fact_digest,o.facts "
            "from {}.focus_episode_observations o join {}.focus_runs r on r.focus_run_id=o.focus_run_id "
            "where o.episode_id=any(%s) and o.evaluation_mode='AS_RECORDED' "
            "and r.source_authority_contract_id=%s "
            "and (r.focus_run_id=%s or (r.trade_date<%s and exists "
            "(select 1 from {}.focus_trade_date_heads h where h.accepted_focus_run_id=r.focus_run_id "
            "and h.lineage_state='VALID'))) "
            "order by o.episode_id,o.trade_date,o.source_revision,o.state_contract_id")
            .format(schema, schema, schema),
            (episode_ids, SOURCE_AUTHORITY_CONTRACT, run["focus_run_id"], run["trade_date"]))
        outcomes = grouped(sql.SQL(
            "select a.episode_id,o.anchor_id,o.horizon,o.accepted_target_revision,r.target_trade_date,"
            "r.status,r.evaluation_basis,r.forward_return,r.mfe,r.mae,r.mdd,r.reason_codes,r.evidence "
            "from {}.focus_outcome_heads o join {}.focus_episode_outcomes r "
            "on r.anchor_id=o.anchor_id and r.horizon=o.horizon "
            "and r.target_revision=o.accepted_target_revision "
            "join {}.focus_episode_anchors a on a.anchor_id=o.anchor_id "
            "join {}.focus_runs ar on ar.focus_run_id=a.focus_run_id "
            "where a.episode_id=any(%s) and a.trade_date<=%s and r.target_trade_date<=%s "
            "and ar.source_authority_contract_id=%s "
            "and (ar.focus_run_id=%s or (ar.trade_date<%s and exists "
            "(select 1 from {}.focus_trade_date_heads h where h.accepted_focus_run_id=ar.focus_run_id "
            "and h.lineage_state='VALID'))) "
            "order by a.episode_id,a.trade_date,o.horizon")
            .format(schema, schema, schema, schema, schema),
            (episode_ids, run["trade_date"], run["trade_date"], SOURCE_AUTHORITY_CONTRACT,
             run["focus_run_id"], run["trade_date"]))
        episodes = []
        for episode in episode_rows:
            episode_id = episode["episode_id"]
            episodes.append(episode | {"observations": observations[episode_id],
                                       "transitions": transitions[episode_id],
                                       "anchors": anchors[episode_id],
                                       "outcomes": outcomes[episode_id]})
        return {**self._meta(run), "status": "AVAILABLE", "entity_type": entity_type,
                "entity_id": entity_id, "episodes": episodes,
                "episodes_truncated": truncated}

    def _transitions(self, cur, params: dict[str, str], run: dict[str, Any]) -> dict[str, Any]:
        schema = sql.Identifier(self.schema)
        page, size = self._page(params)
        conditions = [sql.SQL("t.focus_run_id=%s")]
        values: list[Any] = [run["focus_run_id"]]
        for key, column in (("source_family", "e.source_family"),
                            ("transition_type", "t.transition_type")):
            if params.get(key):
                conditions.append(sql.SQL("{}=%s").format(sql.SQL(column)))
                values.append(params[key])
        where = sql.SQL(" and ").join(conditions)
        base = sql.SQL("from {}.focus_episode_transitions t join {}.focus_episodes e "
                       "on e.episode_id=t.episode_id where ").format(schema, schema) + where
        cur.execute(sql.SQL("select count(*)::int ") + base, values)
        total = int(cur.fetchone()[0])
        cur.execute(sql.SQL(
            "select t.episode_id,e.source_family,e.entity_type,e.entity_id,"
            "t.transition_trade_date,t.transition_type,t.from_membership,t.to_membership,t.reason_codes ")
            + base + sql.SQL(" order by t.transition_trade_date,e.source_family,e.entity_id,t.transition_type "
                              "limit %s offset %s"), values + [size, (page - 1) * size])
        items = _rows(cur)
        return {**self._meta(run), "status": "AVAILABLE", "items": items,
                "page": page, "page_size": size, "total": total,
                "returned_count": len(items), "has_more": page * size < total}

    def _runs(self, cur, params: dict[str, str], run: dict[str, Any]) -> dict[str, Any]:
        schema = sql.Identifier(self.schema)
        page, size = self._page(params)
        cur.execute(sql.SQL(
            "select count(*)::int from {}.focus_runs r where r.source_authority_contract_id=%s "
            "and r.core_publication_status='ACTIVATED'").format(schema),
            (SOURCE_AUTHORITY_CONTRACT,))
        total = int(cur.fetchone()[0])
        cur.execute(sql.SQL(
            "select r.focus_run_id,r.trade_date,r.revision,r.publication_id,"
            "r.source_family_set,r.family_capabilities,r.state_contract_id,r.parameter_set_id,"
            "r.evaluation_basis,r.core_publication_status,r.outcome_settlement_status,"
            "coalesce(h.lineage_state,'HISTORICAL') as lineage_state,r.activated_at_utc "
            "from {}.focus_runs r left join {}.focus_trade_date_heads h "
            "on h.accepted_focus_run_id=r.focus_run_id "
            "and h.source_authority_contract_id=r.source_authority_contract_id "
            "where r.source_authority_contract_id=%s and r.core_publication_status='ACTIVATED' "
            "order by r.trade_date desc,r.revision desc limit %s offset %s").format(schema, schema),
            (SOURCE_AUTHORITY_CONTRACT, size, (page - 1) * size))
        items = _rows(cur)
        return {**self._meta(run), "status": "AVAILABLE", "items": items,
                "page": page, "page_size": size, "total": total,
                "returned_count": len(items), "has_more": page * size < total}

    def _statistics(self, cur, run: dict[str, Any]) -> dict[str, Any]:
        schema = sql.Identifier(self.schema)
        cur.execute("select to_regclass(%s),to_regclass(%s),to_regclass(%s)",
                    (f"{self.schema}.focus_statistics_heads",
                     f"{self.schema}.focus_statistics_batches",
                     f"{self.schema}.focus_statistics_rows"))
        if any(value is None for value in cur.fetchone()):
            return {**self._meta(run), "status": "STATISTICS_SCHEMA_UNAVAILABLE",
                    "data_status": "UNAVAILABLE", "minimum_complete_rows": STATISTICS_MIN_ROWS,
                    "minimum_signal_trade_dates": STATISTICS_MIN_SIGNAL_DATES,
                    "interpretation": "DESCRIPTIVE_ONLY_NO_PROBABILITY_CLAIMS", "groups": [],
                    "message": "统计物化表尚未安装；本请求未扫描 outcome 历史。"}
        cur.execute(sql.SQL(
            "select b.statistics_batch_id,b.statistics_contract_id,b.as_of_trade_date,"
            "b.input_digest,b.group_count,b.outcome_count,b.created_at_utc "
            "from {}.focus_statistics_heads h join {}.focus_statistics_batches b "
            "on b.statistics_batch_id=h.statistics_batch_id and b.focus_run_id=h.focus_run_id "
            "where h.focus_run_id=%s").format(schema, schema), (run["focus_run_id"],))
        batch = _rows(cur)
        if not batch:
            return {**self._meta(run), "status": "STATISTICS_NOT_MATERIALIZED",
                    "data_status": "UNAVAILABLE", "minimum_complete_rows": STATISTICS_MIN_ROWS,
                    "minimum_signal_trade_dates": STATISTICS_MIN_SIGNAL_DATES,
                    "interpretation": "DESCRIPTIVE_ONLY_NO_PROBABILITY_CLAIMS", "groups": [],
                    "message": "当前 Focus run 尚无统计物化批次；本请求未扫描 outcome 历史。"}
        cur.execute(sql.SQL(
            "select source_family,entity_type,selection_contract_family,source_model_contract_id,"
            "state_contract_id,anchor_type,horizon,evaluation_basis,price_basis,sample_count,"
            "signal_date_count,incomplete_count,gate_status,p25_return,median_return,p75_return,"
            "max_mfe,worst_mdd from {}.focus_statistics_rows where statistics_batch_id=%s "
            "order by source_family,entity_type,selection_contract_family,source_model_contract_id,"
            "state_contract_id,anchor_type,horizon,evaluation_basis,price_basis").format(schema),
            (batch[0]["statistics_batch_id"],))
        return {**self._meta(run), "status": "AVAILABLE", "data_status": "AVAILABLE",
                "minimum_complete_rows": STATISTICS_MIN_ROWS,
                "minimum_signal_trade_dates": STATISTICS_MIN_SIGNAL_DATES,
                "interpretation": "DESCRIPTIVE_ONLY_NO_PROBABILITY_CLAIMS",
                "statistics_batch": batch[0], "groups": _rows(cur)}
