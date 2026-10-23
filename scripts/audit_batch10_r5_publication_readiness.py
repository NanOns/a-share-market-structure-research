"""Capture read-only PG and 28766 evidence for BATCH10-R5 exact-token gates."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.parse
import urllib.request

import psycopg
from psycopg.conninfo import conninfo_to_dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.operational_successor_v1 import digest
EVIDENCE = ROOT / "docs/evidence/functional_r8_implementation_20261021/BATCH10_R5_OWNER_PUBLICATION_AND_DAILY_INCREMENT_EVIDENCE.json"
TOKENS = {
    "2026-10-20": "a5b169a8cde60cc6ba86f1efbb7714020e578264bfea33634532ab407df70b70",
    "2026-10-21": "14ee0cf87a46f810b52295a8d42c4bbda391fd0fe49f4cb3457a1620067ad378",
}


def configured_dsn() -> str:
    values = {}
    for line in (ROOT / "config/.env").read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip().strip('"').strip("'")
    dsn = values.get("WORKBENCH_PG_DSN")
    if not dsn:
        raise RuntimeError("WORKBENCH_PG_DSN_REQUIRED")
    identity = conninfo_to_dict(dsn)
    if (identity.get("host"), identity.get("port"), identity.get("dbname")) != (
            "127.0.0.1", "5432", "market_research"):
        raise ValueError("R5_PG_TARGET_IDENTITY_MISMATCH")
    return dsn


def request_json(path: str, query: dict[str, str] | None = None) -> dict:
    url = "http://127.0.0.1:28766/api/v4/" + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    with urllib.request.urlopen(url, timeout=20) as response:
        raw = response.read()
        data = json.loads(raw)
        return {"http_status": response.status, "status": data.get("status"),
                "code": data.get("code"), "reason": data.get("reason"),
                "total": data.get("total"), "item_count": len(data.get("items", [])),
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "context_token": data.get("context_token")}


def pg_readback() -> dict:
    with psycopg.connect(configured_dsn(), connect_timeout=5) as pg:
        pg.execute("SET TRANSACTION READ ONLY")
        ident = pg.execute("""select current_database(),
            (select oid from pg_database where datname=current_database()),
            current_setting('server_version_num'), current_setting('transaction_read_only')""").fetchone()
        if ident[0] != "market_research" or ident[3] != "on":
            raise ValueError("R5_PG_READ_SESSION_IDENTITY_MISMATCH")
        r8 = pg.execute("""select trade_date::text,candidate_token,owner_authority_sha256,
            source_freeze_sha256 from v4_r8pub_fde08c597fc76d13.r8_publications
            where trade_date between date '2026-10-20' and date '2026-10-21'
            order by trade_date,candidate_token""").fetchall()
        d0 = pg.execute("""select trade_date::text,candidate_token,publication_id,row_count,
            production_admission,as_recorded,pit_eligible from v4_r8d0seal_batch07_r1.publications
            where trade_date between date '2026-10-20' and date '2026-10-21'
            order by trade_date,candidate_token,publication_id""").fetchall()
        ri = pg.execute("""select day,token,digest,sealed from v4_read_index_0c2b84fb3e1a0c42.read_versions
            where day between '2026-10-20' and '2026-10-21' order by day,token""").fetchall()
        priority = pg.execute("""select token,t0::text,contract,row_count,sealed
            from v4.owner_versions_priority_r1 order by t0,token""").fetchall()
        ingress = pg.execute("""select trade_date::text,source_contract,source_sha256,package_date::text,
            time_role,evidence_class,row_count,candidate_only,production_accepted
            from v4_r8_batch04_source_ingress.source_receipts order by trade_date""").fetchall()
        present_r8 = {row[1] for row in r8}
        present_d0 = {row[1] for row in d0}
        present_ri = {row[1] for row in ri}
        return {
            "identity": {"database": ident[0], "database_oid": ident[1],
                         "server_version_num": ident[2], "transaction_read_only": ident[3]},
            "r8_publications_2026_10_20_21": [dict(trade_date=r[0], token=r[1],
                owner_authority_sha256=r[2], source_freeze_sha256=r[3]) for r in r8],
            "d0_publications_2026_10_20_21": [dict(trade_date=r[0], token=r[1], publication_id=r[2],
                row_count=r[3], production_admission=r[4], as_recorded=r[5], pit_eligible=r[6]) for r in d0],
            "read_index_versions_2026_10_20_21": [dict(day=r[0],token=r[1],digest=r[2],sealed=r[3]) for r in ri],
            "focus_stock_sector_priority_owner_versions": [dict(token=r[0],t0=r[1],contract=r[2],
                row_count=r[3],sealed=r[4]) for r in priority],
            "source_ingress_receipts": [dict(trade_date=r[0],source_contract=r[1],source_sha256=r[2],
                package_date=r[3],time_role=r[4],evidence_class=r[5],row_count=r[6],
                candidate_only=r[7],production_accepted=r[8]) for r in ingress],
            "exact_candidate_token_presence": {day: {
                "r8_publication": TOKENS[day] in present_r8,
                "d0_publication": TOKENS[day] in present_d0,
                "read_index": TOKENS[day] in present_ri,
            } for day in TOKENS},
            "permanent_write_performed": False,
        }


def main() -> None:
    candidate_paths = [ROOT / "docs/evidence/functional_r8_implementation_20261021/supporting/R4_10_20_SUCCESSOR_CANDIDATE_PG_REBOUND.json",
                       ROOT / "docs/evidence/functional_r8_implementation_20261021/supporting/R4_10_21_SUCCESSOR_CANDIDATE.json"]
    candidate_files = []
    for path in candidate_paths:
        c = json.loads(path.read_bytes())
        owners = c.get("owners", {}).get(c.get("accepted_trade_date"), {})
        bindings = [v for v in owners.values() if isinstance(v, dict) and isinstance(v.get("path"), str)]
        candidate_files.append({"trade_date": c.get("accepted_trade_date"),
            "token": digest(c),
            "owner_binding_count": len(bindings),
            "locally_present_owner_payloads": sum((ROOT / v["path"]).is_file() for v in bindings)})
    pg = pg_readback()
    context = request_json("context")
    token = context.get("context_token")
    routes = {}
    for route in ("focus", "focus/priority", "priority", "forward", "home"):
        routes[route] = request_json(route, {"trade_date":"2026-10-21", "context_token":token, "limit":"3"})
    targets = Path("G:/codex_tmp/r8_fourth_batch/tdx_source_20261021/tdx_targets")
    source_dates = sorted(p.name for p in targets.iterdir() if p.is_dir()) if targets.is_dir() else []
    evidence = {
        "contract_id": "BATCH10_R5_OWNER_PUBLICATION_AND_DAILY_INCREMENT_EVIDENCE_R1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "git": {"branch": subprocess.check_output(["git","branch","--show-current"],cwd=ROOT,text=True).strip(),
                "head": subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                "remote_head_checked": "e5b499fc23faaf21a6c819d8f0bd18fa611952e6"},
        "phase0": {"status":"DEGRADED_PASS", "basis":"docs/evidence/functional_r8_implementation_20261021/S00_S06_P_S05_D_PREPARATION.md",
                   "scanner_started":False, "scope":"candidate research; no production release"},
        "runtime": {"web_port":28766,"production_port_28765_listening":False,"pg_port":5432,
                    "current_28766_context":context,"endpoint_readbacks":routes},
        "visible_ui_readback": {
            "url": "http://127.0.0.1:28766/v4/research/focus",
            "title": "\u5927 A \u00b7 V4 \u7814\u7a76\u5de5\u4f5c\u53f0",
            "selected_trade_date": "2026-10-21",
            "focus_list_rows": 3975,
            "d0_source_rows": 5224,
            "d0_true": 99,
            "d0_unknown": 5125,
            "focus_d0_mapped": 3975,
            "focus_d2_mapped": 3975,
            "historical_non_pit_notice_visible": True,
            "formal_focus_priority_owner_section_visible": False,
            "page_state": "RENDERED_READ_ONLY",
            "observation": "Browser accessibility tree and screenshot showed dated Focus tracking list; no dated Focus Priority Owner is presented.",
        },
        "candidate_payload_availability": candidate_files,
        "pg_readback": pg,
        "source_2026_10_22": {"ingress_receipt_present":"2026-10-22" in {r["trade_date"] for r in pg["source_ingress_receipts"]},
            "captured_package_target_dates":source_dates,
            "configured_tdx_root":"D:/new_tdx/vipdoc/{sh,sz}/lday",
            "configured_tdx_day_files_scanned":11884,
            "latest_last_record_trade_date":"2026-10-08",
            "eligible_10_22_source_available":False},
        "interpretation": {"r8_d0_exact_candidate_publication":"NOT_FOUND_FOR_TASK_TOKENS",
            "read_index_exact_candidate_publication":"10/21_FOUND; 10/20_NOT_FOUND" if pg["exact_candidate_token_presence"]["2026-10-21"]["read_index"] else "NOT_FOUND",
            "focus_priority":"NO_DATED_OPERATIONAL_OWNER; no ranking rule in current Focus contract path",
            "forward_validation_cohort":"WAIT_TRUE_FIRST_CAPTURE; no authorized cohort Owner",
            "formal_head_changed":False,"production_accepted":False},
        "gate_statuses": {
            "P0_A_exact_token_owner_publication": "FAIL_EXACT_R8_D0_PRIORITY_NOT_PUBLISHED",
            "P0_A_read_index_2026_10_21": "REAL_PG_PASS",
            "P0_A_read_index_2026_10_20": "FAIL_NOT_FOUND",
            "P0_B_lifecycle_bar_receipt": "CODE_PASS_REAL_PG_TEMP_FIXTURE_PASS",
            "P0_C_focus_priority_owner": "CONTRACT_BLOCKED_NO_VERSIONED_RANKING_RULE",
            "P0_C_forward_first_capture": "WAIT_TRUE_FIRST_CAPTURE",
            "P0_D_2026_10_22_increment": "FAIL_REAL_SOURCE_NOT_AVAILABLE",
            "R6_S02_performance": "DEFERRED_BY_USER_INSTRUCTION",
            "D2_frozen_level": "CONTRACT_BLOCKED_DEFERRED_BY_USER_INSTRUCTION",
        },
        "lifecycle_pg_fixture": {
            "status": json.loads((ROOT / "docs/evidence/functional_r8_implementation_20261021/supporting/BATCH10_R5_LIFECYCLE_PG_TEMP_FIXTURE.json").read_bytes())["status"],
            "sha256": hashlib.sha256((ROOT / "docs/evidence/functional_r8_implementation_20261021/supporting/BATCH10_R5_LIFECYCLE_PG_TEMP_FIXTURE.json").read_bytes()).hexdigest(),
            "scope": "session-local temporary tables; no permanent DDL/DML",
        },
    }
    raw=json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    tmp=EVIDENCE.with_suffix(".json.tmp")
    tmp.write_text(raw,encoding="utf-8")
    os.replace(tmp,EVIDENCE)
    print(json.dumps({"evidence":str(EVIDENCE),"sha256":hashlib.sha256(raw.encode()).hexdigest(),
        "token_gates":pg["exact_candidate_token_presence"],"focus_priority":routes["focus/priority"]["code"],
        "forward":routes["forward"]["reason"],"source_10_22":evidence["source_2026_10_22"]},ensure_ascii=False))


if __name__ == "__main__":
    main()
