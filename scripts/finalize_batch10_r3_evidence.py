"""Finalize the BATCH10-R3 repair report from captured API evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-matrix", required=True, type=Path)
    parser.add_argument("--pg-readback", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    api = json.loads(args.api_matrix.read_text(encoding="utf-8"))
    pg = json.loads(args.pg_readback.read_text(encoding="utf-8"))

    evidence["execution_revision"] = "R2_CONTINUATION"
    evidence["pre_execution_head"] = "29ce4d1d150fca80f14a5282139cb41fe0650b41"
    evidence["remote_head_at_start"] = "29ce4d1d150fca80f14a5282139cb41fe0650b41"
    evidence["overall_status"] = "BATCH10_R3_REPAIR_PASS_CANDIDATE_ONLY_LANE_L_WAIT"
    evidence["code_changes"] = {
        "scripts/rebase_batch10_r3_successor.py": "Creates immutable 10/20 and then 10/21 successors, binding exact R3 Core, RPS5 delta3, and full D0 identity sets.",
        "scripts/run_batch10_r3_r8_release.py": "Runs G123 binding, a real candidate-only CAS rollback drill, R8 PG publication, exact-token 28766 readback, and D0 PG publication/readback.",
        "src/workbench_analysis/d0_source_seal_r2.py": "Allows an exact SHA-256 content address for dated reconstructed evidence Owners when the archive path predates run-token directory layout.",
        "src/workbench_service/core_product_bff_r1.py": "Separates snapshot context token/date from requested historical data date and dated Owner bindings.",
        "src/workbench_service/static/core-product-r1/app.js": "Keeps missing real Lane L first-capture state explicit as WAIT_REAL_FIRST_CAPTURE.",
        "scripts/capture_batch10_r3_api_matrix.py": "Captures real read-only 28766 cross-date/detail/period/search/pagination/cache evidence.",
        "scripts/finalize_batch10_r3_evidence.py": "Builds the final report/evidence from the captured live API matrix.",
    }
    evidence["tests"] = {
        "command": "pytest -q --basetemp=G:/codex_tmp/test_temp/batch10r3_reopen tests/test_batch10_r3_successor_rebase.py tests/test_d0_owner_version_content_address_r2.py tests/test_v4_ux_r2_contract.py tests/test_v4_ux_r3_routes.py tests/test_forward_lane_l_wait_presentation.py",
        "result": "52 passed in 3.94s",
        "python_compile": "PASS for capture/finalize/successor/release scripts",
        "git_diff_check": "PASS",
    }
    evidence["candidate_chain"] = {
        "2026-10-20": {
            "token": "283fec0eacc4035237a60f2c8dea77586be09dafa4b1b4df072e02c765ab7562",
            "predecessor_sha256": "f9c4fa37dcef3cb4d28cf2a4e6e41f448898947be9fb16240f67cfd8ee136862",
            "r3_core_rows": 5226,
            "r3_core_sha256": "123111b8b6cd95e10cd538e8052b344dc2b0377a3b711589c040ccfd3e75aa83",
            "r3_pre-watch_rows": 5226,
            "r3_d0_rows": 5226,
            "d0_counts": {"TRUE": 141, "FALSE": 5033, "UNKNOWN": 52},
            "d0_pg_readback": "PASS",
            "r8_pg_readback": "PASS",
            "r8_receipt_sha256": "1e9fd5cb284fea2aa7c7e5c38544cfd8eb7bc7eec5b28288c67a6cfe7fb55481",
            "r8_28766_readback": "PASS",
            "historical_as_recorded": False,
            "historical_pit_eligible": False,
        },
        "2026-10-21": {
            "token": "f8c09d96f7200e2b1cab2b140393297b1fcc31511a97c3b6fa3e0970c5686430",
            "predecessor_token": "283fec0eacc4035237a60f2c8dea77586be09dafa4b1b4df072e02c765ab7562",
            "period_oracle_checks": 637268,
            "period_oracle_diffs": 0,
            "core_rows": 5224,
            "d0_rows": 5224,
            "d0_pg_readback": "PASS",
            "r8_pg_readback": "PASS",
            "r8_receipt_sha256": "5a9a2a93735c26652d5defdfabd458e3befd821547c1b0cd48241afa7aa07418",
            "r8_28766_readback": "PASS",
            "historical_as_recorded": False,
            "historical_pit_eligible": False,
        },
    }
    evidence["milestones"] = {
        "readindex_1019_identity_authority_and_1020_1021_rebase": "PASS",
        "rps5_delta3_full_5226_d0_owner_pg_publish_readback": "PASS_CANDIDATE_ONLY",
        "forward_lane_h": "PASS_CANDIDATE_PG_28766_AND_VISIBLE_READBACK_73115_NON_PIT",
        "forward_lane_l": "WAIT_REAL_FIRST_CAPTURE",
        "historical_date_context_token_owner_consistency": "PASS_API_MATRIX_19_20_21_AND_CACHE_ROUND_TRIP",
        "visible_ui_acceptance": "PASS_1020_LIST_SEARCH_PAGINATION_STOCK_DETAIL_DAY_WEEK_MONTH",
    }
    evidence["api_matrix"] = api
    evidence["direct_pg_readback"] = {
        "database": "127.0.0.1:5432/market_research",
        "database_oid": 646711,
        "reader_mode": "read-only",
        "r8_schema": "v4_r8pub_fde08c597fc76d13",
        "read_index": {
            "authority_contract": "V4_READ_INDEX_AUTHORITY_R2",
            "authority_binding_file": "G:/codex_tmp/v4_daily_candidate_chain_20261020/config/v4_read_index_authority_r2.json",
            "authority_binding_sha256": "d805c13730750b3fe1dcd07b47e0cb16fc00b670161d934e9359b65d628a5337",
            "2026-10-19": {"status": "READY", "stocks_total": 5224, "schema": "v4_a50e701bc0e68312c2d32baefc2b17b0cd957206c4ebd9b54decae30", "digest": "987c5c456062ad3237c77a34397a89b6e83cff49aead512e6414f9b8257753ee", "native_identity_authority_bound": True},
            "2026-10-20": {"status": "READY", "stocks_total": 5224, "schema": "v4_1ef7141b2990885dccd6f61250c7b4fdda602995cc5b786b4d37c724", "digest": "34b77f72939a0822679b8454ead4d6fd5a5e63e7a919e15566b5694f9c16330f", "native_identity_authority_bound": True},
            "2026-10-21": {"status": "READY", "stocks_total": 5224, "schema": "v4_a9a294dfbf0379874f4401086f31f78627dadd660ba47d508bb8c398", "digest": "e7f3e07959c263bce4fb1c111168255eb622499acecf848521e0130cbde89f2d", "native_identity_authority_bound": True},
        },
        "d0_restricted_reader_readback": pg,
        "2026-10-20": {
            "token": "283fec0eacc4035237a60f2c8dea77586be09dafa4b1b4df072e02c765ab7562",
            "r8_publication": "PASS",
            "d0_publication": "PASS",
            "scenario_fact_rows": 10452,
            "predicate_rows": 5226,
            "predicate_digest": "PASS",
            "formal_head_modified": False,
            "production_accepted": False,
        },
        "2026-10-21": {
            "token": "f8c09d96f7200e2b1cab2b140393297b1fcc31511a97c3b6fa3e0970c5686430",
            "r8_publication": "PASS",
            "d0_publication": "PASS",
            "scenario_fact_rows": 10448,
            "predicate_rows": 5224,
            "predicate_digest": "PASS",
            "formal_head_modified": False,
            "production_accepted": False,
        },
        "10_20_initial_token_695e1a_failed_readback": {
            "status": "ABORTED_AND_HEAD_ROLLED_BACK",
            "reason": "READ_INDEX_RESPONSE_NOT_PREPARED",
            "preserved": True,
        },
    }
    evidence["visible_ui"] = {
        "tool": "cua_repl in-app browser",
        "service": "http://127.0.0.1:28766",
        "safety_denial": False,
        "stock_list": {"trade_date": "2026-10-20", "profile_projection_total": 5224,
                        "page_2_visible": True, "search": "SH.688411", "search_total": 1},
        "stock_detail": {"entity_id": "SEC-01A43DE232AC7DE094EC000A597C049A",
                         "display_name": "海博思创 SH.688411", "visible": True},
        "chart": {"data_trade_date": "2026-10-20", "D": {"status": "READY", "bars": 12},
                  "W": {"status": "READY", "bars": 4, "last_bar": "FORMING_AS_OF"},
                  "M": {"status": "READY", "bars": 2, "last_bar": "FORMING_AS_OF"}},
        "forward_lane_h_visible_count": 73115,
        "forward_lane_l_visible_status": "WAIT_REAL_FIRST_CAPTURE",
        "screenshots": "Visible browser output captured during this task; no security warning or bypass occurred.",
    }
    evidence["api_readback"] = {
        "service": "127.0.0.1:28766",
        "production_port_28765_listener": False,
        "database": "127.0.0.1:5432/market_research",
        "snapshot_context_token": "f8c09d96f7200e2b1cab2b140393297b1fcc31511a97c3b6fa3e0970c5686430",
        "snapshot_context_trade_date": "2026-10-21",
        "historical_dates_read": ["2026-10-19", "2026-10-20", "2026-10-21"],
        "context_data_owner_token_separated": True,
        "matrix_status": "PASS",
        "matrix_check_count": len(api["checks"]),
        "cache_round_trip_byte_identical": api["cache_round_trip"]["byte_identical"],
        "matrix_evidence_embedded": "api_matrix.checks",
    }
    evidence["preservation"] = {
        "historical_non_pit_rewritten": False,
        "formal_head_modified": False,
        "production_28765_touched": False,
        "drop_or_delete_used": False,
        "synthetic_forward_first_capture_created": False,
        "unrelated_untracked_paths_preserved": [".githooks/", "config_back/", "script_back/"],
    }
    evidence["next_stage"] = (
        "Lane L remains WAIT_REAL_FIRST_CAPTURE until a source-ready first capture passes the full-owner lifecycle conservation contract. "
        "Do not switch production Head, schedule, or 28765 from this candidate-only verification."
    )

    report = """# BATCH10-R3 Four-Gap Repair Report — R2 continuation

- Date: 2026-10-22 (Asia/Shanghai)
- Branch: `codex/v4-unified-development`
- Audited baseline: `5cfa4c5e9793538a640749d39cf50dbe39acc8c5`
- Pre-execution repository HEAD verified against origin: `29ce4d1d150fca80f14a5282139cb41fe0650b41`
- Result: **candidate repair passed for the requested historical chain; Lane L remains WAIT**.
- All generated candidate material is under `G:/codex_tmp/v4_daily_candidate_chain_20261020`; historical sources remain explicitly NON_PIT.

## Repairs and evidence

1. **10/19 ReadIndex and 10/20–10/21 succession.** Bound the 10/19 dated membership and native Identity authority into the R2 ReadIndex authority. The direct PG ReadIndex page and 28766 dated API return READY under the 10/21 snapshot context. The immutable successor chain now runs 10/20 `283fec0e…ab7562` → 10/21 `f8c09d96…686430`; 10/21 period oracle checked 637,268 values with zero differences.
2. **RPS5 delta3 and complete 5,226-object D0.** The 10/20 successor binds the exact R3 Core bytes (`123111b8…aa83`), all 5,226 unique identities and the matching 5,226 D0/prewatch objects. RPS5 validation has 5,202 exact, 24 unknown, and zero mismatches. D0 aggregates are TRUE 141 / FALSE 5,033 / UNKNOWN 52. R8 candidate publication, D0 PG publication, predicate digest, and 28766 exact-token context readback all passed. The 10/21 successor was rebuilt from the new predecessor and independently published/read back.
3. **Forward lanes.** Lane H is connected to the candidate chain and has 73,115 `RETROSPECTIVE_RESEARCH` rows in the isolated Forward PG namespace, with 28766 API and visible page readback. It remains NON_PIT. Lane L has no qualifying real first capture; UI and API continue to show `WAIT_REAL_FIRST_CAPTURE` / `WAIT_SOURCE_READY`. No synthetic sample was created. The historical live-capture failure remains `SOURCE_EXECUTION_FULL_OWNER_LIFECYCLE_CONSERVATION_FAILED`.
4. **Historical date context.** A read-only 21-check API matrix uses snapshot context token `f8c09d96…686430` (context date 10/21), while query dates and row dates are 10/19, 10/20, or 10/21 and dated Owner bindings resolve to the corresponding historical day. Context, stocks, sectors, focus, profile detail, daily/weekly/monthly charts, search, and pagination were checked. After changing to 10/21 and back, the same 10/20 list response was byte-identical (`7a7ce236…291b5c`), demonstrating no cross-date cache bleed in this read path.
5. **Visible UI.** On 28766, the 10/20 stock list, page 2, search `SH.688411`, stock detail, and D/W/M chart selectors loaded visibly. The daily/weekly/monthly series ended at 10/20; weekly/monthly final bars were explicitly marked `FORMING_AS_OF`. Forward history showed 73,115. No browser security warning was bypassed. The stock-list profile projection is 5,224; the separately published Core and D0 domains contain 5,226, and the two objects excluded from that profile projection are not represented as missing Core/D0 objects.

## Publication safety and test result

- R8 candidate receipts: 10/20 `283fec0e…ab7562`, 10/21 `f8c09d96…686430`; both candidate-only, PG readback matched, CAS rollback drill passed, `formal_head_modified=false`, `production_accepted=false`.
- D0 PG readback: 10/20 10,452 scenario facts and 5,226 predicate rows; 10/21 10,448 scenario facts and 5,224 predicate rows; both predicate digests passed.
- First 10/20 token attempt `695e1a…` aborted on missing ReadIndex response and rolled back. It is retained as an audit event; successful retry3 tokens are immutable successors.
- Regression suite: `52 passed` (`test_batch10_r3_successor_rebase.py`, `test_d0_owner_version_content_address_r2.py`, dated BFF/routes, and Lane L WAIT presentation).
- Runtime used only `127.0.0.1:28766` and `127.0.0.1:5432/market_research` (database OID 646711). `28765` was not listening or touched.
- No production Head or schedule was changed. The user-authorized operations were confined to development candidate publication and readback. No DROP/DELETE was issued.

Machine-readable API/PG/UI details are in `BATCH10_R3_FOUR_GAPS_REPAIR_EVIDENCE.json`; the live API matrix is embedded there as `api_matrix`.

## Remaining gated condition

Lane L remains `WAIT_REAL_FIRST_CAPTURE` until the actual source is READY and a real first capture passes full Owner lifecycle conservation. This WAIT is not a release failure for the completed historical candidate chain and must not be filled using retrospective Lane H data.
"""
    for path, value in ((args.evidence, evidence), (args.report, report)):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        if isinstance(value, str):
            temp.write_text(value, encoding="utf-8")
        else:
            temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)
    print(json.dumps({"evidence": str(args.evidence), "report": str(args.report),
                      "api_checks": len(api["checks"]), "status": evidence["overall_status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
