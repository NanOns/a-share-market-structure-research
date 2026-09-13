"""Read-only V3 P08 research queries.

This module deliberately consumes only a resolved COMPLETE run.  It does not
construct a run, read legacy candidate/association rankings, or mutate the
database while serving a GET request.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
import json
from pathlib import Path
from typing import Any, Callable, Iterator

import duckdb

from .research_context import ResearchContextError, ResearchContextReader
from .research_signal_evaluation import CONTRACT_ID as SIGNAL_EVALUATION_CONTRACT_ID, build_equal_size_baselines, sample_gate


ROOT = Path(__file__).resolve().parents[2]


def _json(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def _codes(value: Any) -> list[str]:
    parsed = _json(value, [])
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _reasons(value: Any, as_of: str, *, root: Path = ROOT) -> list[dict[str, Any]]:
    try:
        catalog = json.loads((root / "config/research_v3_reasons.yaml").read_text(encoding="utf-8"))
        labels = {str(item["code"]): item for item in catalog.get("reasons", [])}
    except (OSError, ValueError, TypeError, KeyError):
        labels = {}
    result = []
    for code in _codes(value):
        item = labels.get(code, {})
        result.append({
            "code": code,
            "label": item.get("label", code),
            "observed": None,
            "operator": None,
            "threshold": None,
            "unit": item.get("default_unit"),
            "as_of": as_of,
        })
    return result


class ResearchQueryError(ValueError):
    pass


class ResearchQueries:
    def __init__(self, connection_provider: Callable[[], Any] | None = None, *, root: str | Path | None = None):
        self.connection_provider = connection_provider
        self.root = Path(root).resolve() if root else ROOT
        self.contexts = ResearchContextReader(connection_provider)

    @contextmanager
    def _connection(self, connection: duckdb.DuckDBPyConnection | None = None) -> Iterator[duckdb.DuckDBPyConnection]:
        if connection is not None:
            yield connection
            return
        if self.connection_provider is None:
            raise ResearchQueryError("RESEARCH_CONNECTION_REQUIRED")
        with self.connection_provider() as provided:
            yield provided

    @staticmethod
    def _page(page: Any, page_size: Any) -> tuple[int, int]:
        try:
            page = int(page)
            page_size = 20 if page_size in (None, "") else int(page_size)
        except (TypeError, ValueError) as exc:
            raise ResearchQueryError("PAGINATION_INVALID") from exc
        if page < 1 or page_size < 1 or page_size > 50:
            raise ResearchQueryError("PAGINATION_INVALID")
        return page, page_size

    @staticmethod
    def _envelope(*, context: dict[str, Any], items: list[Any], total: int, page: int, page_size: int, display_limit: int | None = None) -> dict[str, Any]:
        status = "READY" if items else "EMPTY"
        result = {
            "status": status,
            "total_eligible": int(total),
            "eligible_total": int(total),
            "returned_count": len(items),
            "total": int(total),
            "page": page,
            "page_size": page_size,
            "has_more": page * page_size < total,
            "items": items,
            "context": context,
        }
        if display_limit is not None:
            result["display_limit"] = int(display_limit)
        return result

    def _context(self, context_id: str, connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
        return self.contexts.resolve_id(context_id, connection)

    @staticmethod
    def _sector_metadata(connection: duckdb.DuckDBPyConnection, publication_id: str, sector_id: str) -> tuple[str, str]:
        try:
            row = connection.execute("SELECT sector_name,sector_type FROM sector_daily WHERE publication_id=? AND sector_id=?", [publication_id, sector_id]).fetchone()
        except duckdb.CatalogException:
            row = None
        return (str(row[0] or sector_id), str(row[1] or "LOCAL")) if row else (sector_id, "LOCAL")

    @staticmethod
    def _stock_name(connection: duckdb.DuckDBPyConnection, publication_id: str, security_id: str) -> str:
        try:
            row = connection.execute("SELECT security_name FROM stock_daily WHERE publication_id=? AND security_id=?", [publication_id, security_id]).fetchone()
        except duckdb.CatalogException:
            row = None
        return str(row[0] or security_id) if row else security_id

    def _member(self, connection: duckdb.DuckDBPyConnection, context: dict[str, Any], row: tuple[Any, ...], *, total_members: int) -> dict[str, Any]:
        run_id, sector_id, security_id, role, role_rank, today_rank, reason_codes, evidence = row
        security_id = str(security_id)
        evidence_obj = _json(evidence, {})
        if not isinstance(evidence_obj, dict):
            evidence_obj = {}
        return {
            "security_id": security_id,
            "name": self._stock_name(connection, context["publication_id"], security_id),
            "price": evidence_obj.get("price"),
            "ret1": evidence_obj.get("ret1"),
            "amount": evidence_obj.get("amount"),
            "quote_as_of": evidence_obj.get("quote_as_of"),
            "quote_source": evidence_obj.get("quote_source"),
            "role": str(role),
            "role_rank": int(role_rank),
            "today_rank": int(today_rank) if today_rank is not None else None,
            "rank_denominator": int(total_members) if total_members is not None else None,
            "total_member_count": int(total_members),
            "rps20": evidence_obj.get("rps20"),
            "bias20": evidence_obj.get("bias20"),
            "risk_codes": _codes(evidence_obj.get("risk_codes", [])),
            "selection_reason": _reasons(reason_codes, context["local_date"], root=self.root),
            "waiting_for": [],
            "invalid_if": [],
            "primary_sector": str(sector_id),
            "other_sector_count": 0,
        }

    def _sector_card(self, connection: duckdb.DuckDBPyConnection, context: dict[str, Any], row: tuple[Any, ...], track: str, preview_limit: int = 3) -> dict[str, Any]:
        (run_id, sector_id, current, potential, branch, branches, current_rank, potential_rank, m1, b1, rel1, p1,
         q5, q20, dq5_3, b_delta3, ma20_width, ma20_delta3, early_width, amount_a, top1_share, member_count,
         quote_valid, feature_valid, early_count, positive_count, quote_coverage, feature_coverage, risk_coverage,
         quality, reason_codes, evidence, input_hash, rank_hash) = row
        sector_id = str(sector_id)
        name, sector_type = self._sector_metadata(connection, context["publication_id"], sector_id)
        if track == "CURRENT":
            lifecycle, active = None, bool(current)
        elif track == "POTENTIAL":
            lifecycle, active = ("QUALIFIED" if potential else None), bool(potential)
        else:
            lifecycle, active = None, True
        # Preview members are intentionally capped and come only from the
        # stored role rows, never from legacy candidate rankings.
        try:
            member_rows = connection.execute(
                """SELECT run_id,sector_id,security_id,role,role_rank,today_rank,role_reason_codes,evidence
                   FROM research_sector_member_roles WHERE run_id=? AND sector_id=?
                   ORDER BY role_rank,security_id LIMIT ?""", [context["run_id"], sector_id, preview_limit]
            ).fetchall()
        except duckdb.CatalogException:
            member_rows = []
        try:
            role_counts = {
                str(role): int(count)
                for role, count in connection.execute(
                    "SELECT role,count(*) FROM research_sector_member_roles WHERE run_id=? AND sector_id=? GROUP BY role",
                    [context["run_id"], sector_id],
                ).fetchall()
            }
        except duckdb.CatalogException:
            role_counts = {}
        preview = [self._member(connection, context, member, total_members=int(member_count or 0)) for member in member_rows]
        return {
            "sector_id": sector_id,
            "name": name,
            "type": sector_type,
            "track": track,
            "branch": str(branch) if branch else None,
            "lifecycle": lifecycle,
            "signal_date": context["local_date"],
            "m1": m1,
            "b1": b1,
            "rel1": rel1,
            "amount_sum": None,
            "amount_coverage": None,
            "amount_A": amount_a,
            "quote_coverage": quote_coverage,
            "member_count": int(member_count or 0),
            "today_leader_count": role_counts.get("TODAY_LEADER", 0),
            "early_watch_count": role_counts.get("EARLY_WATCH", int(early_count or 0)),
            "reasons": _reasons(reason_codes, context["local_date"], root=self.root),
            "waiting_for": [],
            "invalid_if": [],
            "preview_members": preview,
            "quote_as_of": None,
            "local_as_of": context["local_date"],
            "_active": active,
            "_current_rank": current_rank,
            "_potential_rank": potential_rank,
            "_quality": quality,
            "_evidence": _json(evidence, {}),
        }

    def list_sectors(self, context_id: str, *, track: str = "ALL", sector_type: str = "", q: str = "", page: Any = 1, page_size: Any = 20, connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        track = str(track or "ALL").upper()
        if track not in {"CURRENT", "POTENTIAL", "WEAK", "ALL"}:
            raise ResearchQueryError("TRACK_UNSUPPORTED")
        page, page_size = self._page(page, page_size)
        with self._connection(connection) as current:
            context = self._context(context_id, current)
            where = ["run_id=?"]
            args: list[Any] = [context["run_id"]]
            if track == "CURRENT":
                where.append("current_eligible IS TRUE")
            elif track == "POTENTIAL":
                where.append("potential_eligible IS TRUE")
            elif track == "WEAK":
                where.append("coalesce(current_eligible,FALSE) IS FALSE AND coalesce(potential_eligible,FALSE) IS FALSE")
            if q:
                where.append("sector_id ILIKE ?")
                args.append(f"%{str(q)}%")
            clause = " AND ".join(where)
            try:
                if sector_type:
                    # Type/name metadata lives in the publication-bound legacy
                    # table, so filter it after the state rows are mapped. Do
                    # not paginate before filtering: total must be the full
                    # eligible count, never the current page length.
                    total = int(current.execute(f"SELECT count(*) FROM research_sector_states WHERE {clause}", args).fetchone()[0])
                    rows = current.execute(
                        f"""SELECT run_id,sector_id,current_eligible,potential_eligible,potential_branch,potential_branches,
                                   current_rank,potential_rank,m1,b1,rel1,p1,q5,q20,dq5_3,b_delta3,ma20_width,ma20_delta3,
                                   early_width,amount_a,top1_positive_share,member_count,quote_valid_count,feature_valid_count,
                                   early_count,positive_count,quote_coverage,feature_coverage,risk_coverage,quality,reason_codes,
                                   evidence,input_members_hash,rank_universe_hash
                            FROM research_sector_states WHERE {clause}
                            ORDER BY coalesce(current_rank,potential_rank,999999),sector_id""", args
                    ).fetchall()
                else:
                    total = int(current.execute(f"SELECT count(*) FROM research_sector_states WHERE {clause}", args).fetchone()[0])
                    rows = current.execute(
                        f"""SELECT run_id,sector_id,current_eligible,potential_eligible,potential_branch,potential_branches,
                                   current_rank,potential_rank,m1,b1,rel1,p1,q5,q20,dq5_3,b_delta3,ma20_width,ma20_delta3,
                                   early_width,amount_a,top1_positive_share,member_count,quote_valid_count,feature_valid_count,
                                   early_count,positive_count,quote_coverage,feature_coverage,risk_coverage,quality,reason_codes,
                                   evidence,input_members_hash,rank_universe_hash
                            FROM research_sector_states WHERE {clause}
                            ORDER BY coalesce(current_rank,potential_rank,999999),sector_id LIMIT ? OFFSET ?""",
                        [*args, page_size, (page - 1) * page_size]
                    ).fetchall()
            except duckdb.CatalogException:
                total, rows = 0, []
            items = [self._sector_card(current, context, row, track) for row in rows]
            if sector_type:
                items = [item for item in items if item["type"] == sector_type]
                total = len(items)
                items = items[(page - 1) * page_size:page * page_size]
            for item in items:
                item.pop("_active", None); item.pop("_current_rank", None); item.pop("_potential_rank", None); item.pop("_quality", None); item.pop("_evidence", None)
            return self._envelope(context=context, items=items, total=total, page=page, page_size=page_size)

    def sector_detail(self, context_id: str, sector_id: str, connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        with self._connection(connection) as current:
            context = self._context(context_id, current)
            try:
                row = current.execute(
                    """SELECT run_id,sector_id,current_eligible,potential_eligible,potential_branch,potential_branches,
                              current_rank,potential_rank,m1,b1,rel1,p1,q5,q20,dq5_3,b_delta3,ma20_width,ma20_delta3,
                              early_width,amount_a,top1_positive_share,member_count,quote_valid_count,feature_valid_count,
                              early_count,positive_count,quote_coverage,feature_coverage,risk_coverage,quality,reason_codes,
                              evidence,input_members_hash,rank_universe_hash
                       FROM research_sector_states WHERE run_id=? AND sector_id=?""", [context["run_id"], str(sector_id)]
                ).fetchone()
            except duckdb.CatalogException:
                row = None
            if not row:
                raise ResearchQueryError("SECTOR_NOT_FOUND")
            card = self._sector_card(current, context, row, "ALL", preview_limit=5)
            card.pop("_active", None); card.pop("_current_rank", None); card.pop("_potential_rank", None); card.pop("_quality", None); card.pop("_evidence", None)
            return {"status": "READY", "context": context, "sector": card, "member_counts": {"total": card["member_count"], "today_leader": card["today_leader_count"], "early_watch": card["early_watch_count"]}}

    def sector_members(self, context_id: str, sector_id: str, *, role: str = "ALL_MEMBERS", q: str = "", page: Any = 1, page_size: Any = 20, sort: str = "ROLE", connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        role = str(role or "ALL_MEMBERS").upper()
        if role not in {"TODAY_LEADER", "CURRENT_RESEARCH", "EARLY_WATCH", "ALL_MEMBERS"}:
            raise ResearchQueryError("ROLE_UNSUPPORTED")
        sort = str(sort or "ROLE").upper()
        if sort not in {"ROLE", "RET1", "RET20", "AMOUNT"}:
            raise ResearchQueryError("SORT_UNSUPPORTED")
        page, page_size = self._page(page, page_size)
        with self._connection(connection) as current:
            context = self._context(context_id, current)
            try:
                state = current.execute("SELECT member_count FROM research_sector_states WHERE run_id=? AND sector_id=?", [context["run_id"], str(sector_id)]).fetchone()
                if not state:
                    raise ResearchQueryError("SECTOR_NOT_FOUND")
                where = ["run_id=?", "sector_id=?"]
                args: list[Any] = [context["run_id"], str(sector_id)]
                if role != "ALL_MEMBERS":
                    where.append("role=?"); args.append(role)
                if q:
                    where.append("security_id ILIKE ?"); args.append(f"%{str(q)}%")
                clause = " AND ".join(where)
                if role == "ALL_MEMBERS":
                    # The denominator is the bound membership snapshot. The
                    # role table intentionally stores only the three research
                    # roles, so ALL_MEMBERS must come from the immutable
                    # publication membership relation.
                    membership_snapshot = current.execute("SELECT membership_snapshot_id FROM research_runs WHERE run_id=?", [context["run_id"]]).fetchone()
                    member_rows = []
                    if membership_snapshot:
                        try:
                            member_rows = current.execute("SELECT security_id,payload_json FROM membership_entries WHERE membership_snapshot_id=? AND sector_id=? ORDER BY security_id", [membership_snapshot[0], str(sector_id)]).fetchall()
                        except duckdb.CatalogException:
                            member_rows = []
                    if q:
                        member_rows = [item for item in member_rows if str(q).lower() in str(item[0]).lower()]
                    def sort_value(item: tuple[Any, Any]) -> tuple[Any, str]:
                        data = _json(item[1], {})
                        if not isinstance(data, dict):
                            data = {}
                        key = {"RET1": "ret1", "RET20": "ret20", "AMOUNT": "amount"}.get(sort)
                        value = data.get(key) if key else None
                        return (-(float(value)) if isinstance(value, (int, float)) else float("inf"), str(item[0]))
                    member_rows.sort(key=sort_value)
                    total = len(member_rows)
                    rows = [(context["run_id"], str(sector_id), str(item[0]), "ALL_MEMBERS", index + 1, None, "[]", item[1] or "{}") for index, item in enumerate(member_rows[(page - 1) * page_size:page * page_size])]
                else:
                    total = int(current.execute(f"SELECT count(*) FROM research_sector_member_roles WHERE {clause}", args).fetchone()[0])
                    order = "role_rank,security_id" if sort == "ROLE" else "security_id"
                    rows = current.execute(
                        f"""SELECT run_id,sector_id,security_id,role,role_rank,today_rank,role_reason_codes,evidence
                            FROM research_sector_member_roles WHERE {clause}
                            ORDER BY {order} LIMIT ? OFFSET ?""", [*args, page_size, (page - 1) * page_size]
                    ).fetchall()
            except duckdb.CatalogException:
                total, rows, state = 0, [], (0,)
            items = [self._member(current, context, row, total_members=int(state[0] or 0)) for row in rows]
            return self._envelope(context=context, items=items, total=total, page=page, page_size=page_size)

    def shortlist(self, context_id: str, *, list_type: str = "CURRENT_FOCUS", page: Any = 1, page_size: Any = 20, connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        list_type = str(list_type or "CURRENT_FOCUS").upper()
        if list_type not in {"CURRENT_FOCUS", "EARLY_FOCUS", "INDIVIDUAL"}:
            raise ResearchQueryError("LIST_TYPE_UNSUPPORTED")
        page, page_size = self._page(page, page_size)
        with self._connection(connection) as current:
            context = self._context(context_id, current)
            try:
                total = int(current.execute("SELECT count(*) FROM research_shortlist WHERE run_id=? AND list_type=?", [context["run_id"], list_type]).fetchone()[0])
                rows = current.execute(
                    """SELECT list_type,security_id,rank,primary_sector_id,alternative_sector_ids,selection_reason,waiting_for,invalid_if,previous_state,change_reason
                       FROM research_shortlist WHERE run_id=? AND list_type=? ORDER BY rank,security_id LIMIT ? OFFSET ?""",
                    [context["run_id"], list_type, page_size, (page - 1) * page_size],
                ).fetchall()
            except duckdb.CatalogException:
                total, rows = 0, []
            items = [{"list_type": str(row[0]), "security_id": str(row[1]), "name": self._stock_name(current, context["publication_id"], str(row[1])), "rank": int(row[2]), "primary_sector_id": row[3], "alternative_sector_ids": _json(row[4], []), "selection_reason": _reasons(row[5], context["local_date"], root=self.root), "waiting_for": _json(row[6], []), "invalid_if": _json(row[7], []), "previous_state": row[8], "change_reason": row[9]} for row in rows]
            return self._envelope(context=context, items=items, total=total, page=page, page_size=page_size)

    def home(self, context_id: str, connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        current = self.list_sectors(context_id, track="CURRENT", page=1, page_size=6, connection=connection)
        potential = self.list_sectors(context_id, track="POTENTIAL", page=1, page_size=6, connection=connection)
        focus = self.shortlist(context_id, list_type="CURRENT_FOCUS", page=1, page_size=10, connection=connection)
        early = self.shortlist(context_id, list_type="EARLY_FOCUS", page=1, page_size=10, connection=connection)
        return {"status": "READY", "context": current["context"], "market": {"status": "UNAVAILABLE", "reason": "MARKET_SUMMARY_NOT_BOUND"}, "current_sectors": current["items"], "potential_sectors": potential["items"], "current_focus": focus["items"], "early_focus": early["items"]}

    def stock_detail(self, context_id: str, security_id: str, connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        with self._connection(connection) as current:
            context = self._context(context_id, current)
            try:
                row = current.execute("SELECT security_id,setup,breakout,recovery,trend_background,structure_break,quality,bias20,sigma20,extension_z20,dist_high20,range5,range20,rps5_delta3,liquidity20_amount,risk_codes,reason_codes,evidence FROM research_stock_states WHERE run_id=? AND security_id=?", [context["run_id"], str(security_id)]).fetchone()
            except duckdb.CatalogException:
                row = None
            if not row:
                raise ResearchQueryError("STOCK_NOT_FOUND")
            try:
                role_rows = current.execute("SELECT sector_id,role,role_rank,today_rank,role_reason_codes FROM research_sector_member_roles WHERE run_id=? AND security_id=? ORDER BY role_rank,sector_id", [context["run_id"], str(security_id)]).fetchall()
            except duckdb.CatalogException:
                role_rows = []
            try:
                shortlist_rows = current.execute("SELECT list_type,rank,primary_sector_id,alternative_sector_ids,selection_reason,waiting_for,invalid_if,previous_state,change_reason FROM research_shortlist WHERE run_id=? AND security_id=? ORDER BY list_type,rank", [context["run_id"], str(security_id)]).fetchall()
            except duckdb.CatalogException:
                shortlist_rows = []
            stock = {"security_id": str(row[0]), "name": self._stock_name(current, context["publication_id"], str(row[0])), "signals": {"setup": row[1], "breakout": row[2], "recovery": row[3], "trend_background": row[4], "structure_break": row[5]}, "quality": row[6], "features": {"bias20": row[7], "sigma20": row[8], "extension_z20": row[9], "dist_high20": row[10], "range5": row[11], "range20": row[12], "rps5_delta3": row[13], "liquidity20_amount": row[14]}, "risk_codes": _codes(row[15]), "reasons": _reasons(row[16], context["local_date"], root=self.root), "evidence": _json(row[17], {})}
            stock["sector_roles"] = [{"sector_id": str(item[0]), "role": str(item[1]), "role_rank": int(item[2]), "today_rank": item[3], "reasons": _reasons(item[4], context["local_date"], root=self.root)} for item in role_rows]
            stock["shortlists"] = [{"list_type": str(item[0]), "rank": int(item[1]), "primary_sector_id": item[2], "alternative_sector_ids": _json(item[3], []), "selection_reason": _reasons(item[4], context["local_date"], root=self.root), "waiting_for": _json(item[5], []), "invalid_if": _json(item[6], []), "previous_state": item[7], "change_reason": item[8]} for item in shortlist_rows]
            return {"status": "READY", "context": context, "stock": stock}

    def stock_evidence(self, context_id: str, security_id: str, section: str = "selection", connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        if str(section) not in {"selection", "risk", "sectors", "technical"}:
            raise ResearchQueryError("EVIDENCE_SECTION_UNSUPPORTED")
        detail = self.stock_detail(context_id, security_id, connection=connection)
        evidence = detail["stock"].get("evidence", {})
        if isinstance(evidence, dict) and section in evidence:
            evidence = evidence[section]
        return {"status": "READY", "context": detail["context"], "security_id": str(security_id), "section": str(section), "evidence": evidence}

    def sector_signals(self, context_id: str, sector_id: str, days: Any = 10, connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        try:
            days = int(days)
        except (TypeError, ValueError) as exc:
            raise ResearchQueryError("DAYS_INVALID") from exc
        if days not in {5, 10, 20, 30}:
            raise ResearchQueryError("DAYS_INVALID")
        with self._connection(connection) as current:
            context = self._context(context_id, current)
            try:
                row = current.execute(
                    """SELECT s.current_eligible,s.potential_eligible,s.potential_branch,
                              e.lifecycle,e.first_seen_date,e.last_qualified_date,e.end_date,e.end_reason,e.history_complete
                         FROM research_sector_states s
                         LEFT JOIN research_sector_signal_state e USING(run_id,sector_id)
                        WHERE s.run_id=? AND s.sector_id=?""",
                    [context["run_id"], str(sector_id)],
                ).fetchone()
            except duckdb.CatalogException:
                row = None
            if not row:
                raise ResearchQueryError("SECTOR_NOT_FOUND")
            return {"status": "READY", "context": context, "sector_id": str(sector_id), "days": days, "items": [{"trade_date": context["local_date"], "current_eligible": row[0], "potential_eligible": row[1], "potential_branch": row[2], "lifecycle": row[3], "first_seen_date": row[4], "last_qualified_date": row[5], "end_date": row[6], "end_reason": row[7], "history_complete": row[8], "data_status": "READY" if row[8] else "PARTIAL"}]}

    def signal_evaluation(self, context_id: str, connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        """Read P10-03 outcomes and descriptive baselines without building data."""
        with self._connection(connection) as current:
            context = self._context(context_id, current)
            signal_rows = []
            try:
                rows = current.execute(
                    """SELECT s.sector_id,e.episode_id,e.first_seen_date,s.current_eligible,s.potential_eligible,
                              s.potential_branch,r.run_id,r.algorithm_version,r.parameter_hash,r.snapshot_id,
                              r.membership_snapshot_id
                         FROM research_sector_states s
                         JOIN research_sector_signal_state e USING(run_id,sector_id)
                         JOIN research_runs r USING(run_id)
                        WHERE r.run_id=? AND e.episode_id IS NOT NULL""", [context["run_id"]]
                ).fetchall()
                signal_rows = []
                for row in rows:
                    item = dict(zip(("sector_id", "episode_id", "signal_date", "current_eligible", "potential_eligible", "potential_branch", "run_id", "algorithm_version", "parameter_hash", "snapshot_id", "membership_snapshot_id"), row))
                    item["sector_type"] = self._sector_metadata(current, context["publication_id"], str(item["sector_id"]))[1]
                    signal_rows.append(item)
            except duckdb.CatalogException:
                signal_rows = []
            outcomes = []
            try:
                outcome_rows = current.execute(
                    """SELECT signal_run_id,sector_id,horizon,eval_version,episode_id,due_date,evaluated_at,status,
                              confirmed_date,confirmed_within_h,lead_sessions,member_forward_median,
                              member_forward_coverage,evaluation_basis,evidence
                         FROM research_signal_outcomes
                        WHERE signal_run_id=? ORDER BY sector_id,horizon""", [context["run_id"]]
                ).fetchall()
                names = ("signal_run_id", "sector_id", "horizon", "eval_version", "episode_id", "due_date", "evaluated_at", "status", "confirmed_date", "confirmed_within_h", "lead_sessions", "member_forward_median", "member_forward_coverage", "evaluation_basis", "evidence")
                for row in outcome_rows:
                    item = dict(zip(names, row))
                    item["evidence"] = _json(item["evidence"], {})
                    outcomes.append(item)
            except duckdb.CatalogException:
                outcomes = []
            universe_rows = []
            try:
                state_rows = current.execute(
                    """SELECT sector_id,current_eligible,potential_eligible,q20,dq5_3
                         FROM research_sector_states WHERE run_id=?""", [context["run_id"]]
                ).fetchall()
                for sector_id, current_eligible, potential_eligible, q20, dq5_3 in state_rows:
                    sector_name, sector_type = self._sector_metadata(current, context["publication_id"], str(sector_id))
                    universe_rows.append({"sector_id": str(sector_id), "trade_date": context["local_date"], "sector_type": sector_type, "current_eligible": current_eligible, "potential_eligible": potential_eligible, "q20": q20, "dq5_3": dq5_3, "qualified": potential_eligible})
            except duckdb.CatalogException:
                universe_rows = []
            baselines = build_equal_size_baselines(signal_rows, universe_rows)
            gate = sample_gate(signal_rows, outcomes)
            return {
                "status": "READY" if outcomes else "PENDING",
                "api_contract": SIGNAL_EVALUATION_CONTRACT_ID,
                "context": context,
                "sample_gate": gate,
                "outcome_summary": {"total": len(outcomes), "by_status": {status: sum(1 for row in outcomes if row["status"] == status) for status in ("PENDING", "OBSERVED", "DATA_GAP")}, "by_horizon": {str(horizon): sum(1 for row in outcomes if int(row["horizon"]) == horizon) for horizon in (3, 5)}},
                "baseline_summary": {name: {"count": len(items), "status": "READY" if items else "EMPTY", "items": items[:20]} for name, items in baselines.items()},
                "items": outcomes,
                "next_action": "继续按到期日刷新；样本少于20个信号日或50个独立episode时只显示规则观察，不声称效果通过。",
            }

    def search(self, context_id: str, q: str, entity_type: str = "ALL", connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        q = str(q or "")
        if len(q) < 2 or len(q) > 40:
            raise ResearchQueryError("SEARCH_QUERY_INVALID")
        entity_type = str(entity_type or "ALL").upper()
        if entity_type not in {"ALL", "SECTOR", "STOCK"}:
            raise ResearchQueryError("ENTITY_TYPE_UNSUPPORTED")
        with self._connection(connection) as current:
            context = self._context(context_id, current)
            items: list[dict[str, Any]] = []
            if entity_type in {"ALL", "SECTOR"}:
                try:
                    rows = current.execute("SELECT DISTINCT sector_id FROM research_sector_states WHERE run_id=? AND sector_id ILIKE ? ORDER BY sector_id LIMIT 10", [context["run_id"], f"%{q}%"]).fetchall()
                except duckdb.CatalogException:
                    rows = []
                items.extend({"entity_type": "SECTOR", "id": str(row[0]), "name": self._sector_metadata(current, context["publication_id"], str(row[0]))[0]} for row in rows)
            if entity_type in {"ALL", "STOCK"}:
                try:
                    rows = current.execute("SELECT DISTINCT security_id FROM research_stock_states WHERE run_id=? AND security_id ILIKE ? ORDER BY security_id LIMIT ?", [context["run_id"], f"%{q}%", max(0, 10 - len(items))]).fetchall()
                except duckdb.CatalogException:
                    rows = []
                items.extend({"entity_type": "STOCK", "id": str(row[0]), "name": self._stock_name(current, context["publication_id"], str(row[0]))} for row in rows)
            return {"status": "READY" if items else "EMPTY", "context": context, "items": items[:10]}


__all__ = ["ResearchQueryError", "ResearchQueries"]
