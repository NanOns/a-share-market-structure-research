from __future__ import annotations

"""Apply the bounded, evidence-backed R7 alias/board repair to V4-02 inputs."""

import gzip
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.dated_security_alias import historical_exchange_symbol

TARGET_CURRENT_ID = "SEC-EDEDE35FE66896ACCA0AC85EEB2F133B"
TARGET_PREDECESSOR_ID = "SEC-B2F87F189D1D143B67730E3640E617CA"
TARGET_KEYS = {"SZ.300114", "SZ.302132"}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def signature(row: dict, ignored: set[str]) -> dict:
    return {key: value for key, value in row.items() if key not in ignored}


def main() -> int:
    store = ROOT / "data/v4/artifact_store"
    input_universe = store / "v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz"
    input_status = store / "v4_02/V4_02_DATED_TRADING_STATUS_R6_2_20260926.jsonl.gz"
    input_isst = store / "v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926_RECOVERED_R1.jsonl.gz"
    identity_path = store / "v4_01/security_entity_map_R5_20260925.json"
    evidence_path = ROOT / "data/v4/source_evidence/v4_02_r3/szse_2025_028_code_change_302132.pdf"
    out_universe = store / "v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz"
    out_status = store / "v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz"
    out_isst = store / "v4_02/V4_02_DATED_ST_STATUS_R7_20260927.jsonl.gz"
    out_identity = store / "v4_01/security_entity_map_R7_20260927.json"

    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    records = identity["records"]
    selected = [row for row in records if row.get("security_id") in {TARGET_CURRENT_ID, TARGET_PREDECESSOR_ID}]
    if {row.get("source_security_key") for row in selected} != TARGET_KEYS:
        raise SystemExit("R7_TARGET_IDENTITY_INPUT_SET_MISMATCH")
    if sha(evidence_path) != "dd68049c48df826848f361fd9e7b23dd20b6805144a2e5bc36e54db638611488":
        raise SystemExit("R7_OFFICIAL_IDENTITY_EVIDENCE_HASH_MISMATCH")

    # Keep the identity already assigned to the replacement code as the one
    # stable ID, and express both exchange aliases as dated records.
    repaired_records = [row for row in records if row not in selected]
    source_revision = "sha256:" + sha(evidence_path)
    alias_template = dict(selected[0])
    for key, start, end in (("SZ.300114", "2010-08-27", "2025-02-16"),
                             ("SZ.302132", "2025-02-17", None)):
        repaired = dict(alias_template)
        repaired.update({
            "security_id": TARGET_CURRENT_ID,
            "lifecycle_entity_id": TARGET_CURRENT_ID,
            "source_security_key": key,
            "symbol": key,
            "exchange": "SZ",
            "board": "CHINEXT",
            "list_date": "2010-08-27",
            "delist_date": None,
            "symbol_effective_from": start,
            "symbol_effective_to": end,
            "identity_quality": "OFFICIAL_DATED_CODE_CHANGE_REPAIR_R7",
            "alias_role": "PREDECESSOR" if key == "SZ.300114" else "CURRENT",
            "source_contract_id": "V4_01_SECURITY_ALIAS_BOARD_REPAIR_R7",
            "source_revision_id": source_revision,
            "evidence_source": "SZSE_2025_028_IMPLEMENTATION_ANNOUNCEMENT",
        })
        repaired_records.append(repaired)
    identity_r7 = dict(identity)
    identity_r7.update({"contract_id": "V4_01_SECURITY_ENTITY_MAP_R7", "version": "7.0.0",
                        "records": repaired_records, "supersedes": "security_entity_map_R5_20260925.json"})
    identity_r7_path = out_identity
    atomic_json(identity_r7_path, identity_r7)

    out_universe.parent.mkdir(parents=True, exist_ok=True)
    paths = (out_universe, out_status, out_isst)
    temp_paths = []
    streams = []
    for final in paths:
        fd, name = tempfile.mkstemp(prefix=final.name + ".", suffix=".tmp", dir=final.parent)
        os.close(fd)
        temp_paths.append(Path(name))
        streams.append(gzip.open(name, "wt", encoding="utf-8", newline="\n", compresslevel=6))
    seen: dict[str, set[str]] = defaultdict(set)
    input_rows = output_rows = merged_rows = 0
    target_days: set[str] = set()
    target_id_key_history: dict[str, set[str]] = defaultdict(set)

    try:
        with gzip.open(input_universe, "rt", encoding="utf-8") as u, \
             gzip.open(input_status, "rt", encoding="utf-8") as s, \
             gzip.open(input_isst, "rt", encoding="utf-8") as i:
            day_rows: list[tuple[dict, dict, dict]] = []
            current_day = None

            def emit_group(group: list[tuple[dict, dict, dict]]) -> None:
                nonlocal output_rows, merged_rows
                by_key: dict[str, tuple[dict, dict, dict]] = {}
                passthrough = []
                for ur, sr, ir in group:
                    sid = ur.get("security_id")
                    key = ur.get("source_security_key")
                    if sid in {TARGET_CURRENT_ID, TARGET_PREDECESSOR_ID} or key in TARGET_KEYS:
                        if key not in TARGET_KEYS or sid not in {TARGET_CURRENT_ID, TARGET_PREDECESSOR_ID}:
                            raise RuntimeError("R7_TARGET_ALIAS_IDENTITY_BINDING_INVALID")
                        target_id_key_history[sid].add(key)
                        by_key[key] = (ur, sr, ir)
                    else:
                        passthrough.append((ur, sr, ir))
                        seen[sid].add(key)
                for ur, sr, ir in passthrough:
                    for stream, row in zip(streams, (ur, sr, ir), strict=True):
                        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                    output_rows += 1
                if not by_key:
                    return
                if not set(by_key).issubset(TARGET_KEYS):
                    raise RuntimeError("R7_TARGET_ALIAS_SET_INVALID")
                target_days.add(str(group[0][0]["trade_date"]).replace("-", ""))
                old = by_key.get("SZ.300114")
                new = by_key.get("SZ.302132")
                chosen = new or old
                bar_present = any(pair[0].get("source_bar_present") is True for pair in by_key.values())
                status_values = {pair[1].get("status") for pair in by_key.values()}
                if len(status_values) > 1 and status_values != {"ACTUAL_TRADED", "SUSPENDED"}:
                    raise RuntimeError(f"R7_DUPLICATE_TARGET_TRADING_STATUS_CONFLICT:{group[0][0].get('trade_date')}:{sorted(status_values)}")
                isst_values = {pair[2].get("is_st") for pair in by_key.values()}
                if len(isst_values) > 1:
                    raise RuntimeError(f"R7_DUPLICATE_TARGET_ISST_CONFLICT:{group[0][0].get('trade_date')}:{sorted(map(str, isst_values))}")
                date_value = str(chosen[0]["trade_date"]).replace("-", "")
                alias = historical_exchange_symbol(date_value)
                ur, sr, ir = by_key.get(alias, chosen)
                ur["source_bar_present"] = bar_present
                if bar_present:
                    ur["eligibility_status"] = "EVALUABLE_BAR_AVAILABLE"
                if len(status_values) > 1:
                    sr["status"] = "ACTUAL_TRADED" if bar_present else "SUSPENDED"
                    sr["status_source"] = "LOCAL_TDX_BAR_PRESENCE_MERGED_ACROSS_DATED_ALIASES"
                for row in (ur, sr, ir):
                    row["security_id"] = TARGET_CURRENT_ID
                    row["source_security_key"] = alias
                    row["historical_exchange_symbol"] = alias
                    row["provider_roster_code"] = "SZ.302132"
                    row["code_change_source_revision"] = source_revision
                ur["board_scope"] = "CHINEXT"
                ur["membership_basis"] = "R7_OFFICIAL_DATED_ALIAS_AND_BOARD_REPAIR"
                ir["binding_quality"] = "STABLE_ID_WITH_DATED_HISTORICAL_ALIAS_R7"
                for stream, row in zip(streams, (ur, sr, ir), strict=True):
                    stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                output_rows += 1
                merged_rows += 1

            for lines in zip(u, s, i, strict=True):
                rows = tuple(json.loads(line) for line in lines)
                input_rows += 1
                dates = {str(row.get("trade_date")) for row in rows}
                ids = {str(row.get("security_id")) for row in rows}
                if len(dates) != 1 or len(ids) != 1:
                    raise RuntimeError("R7_INPUT_COMPONENT_ROW_BINDING_MISMATCH")
                day = str(rows[0]["trade_date"])
                if current_day is not None and day != current_day:
                    emit_group(day_rows)
                    day_rows = []
                current_day = day
                day_rows.append(rows)
                if input_rows % 500000 == 0:
                    print(json.dumps({"input_rows": input_rows, "output_rows": output_rows}), flush=True)
            if day_rows:
                emit_group(day_rows)
        for stream in streams:
            stream.close()
        for temp, final in zip(temp_paths, paths, strict=True):
            with temp.open("rb+") as stream:
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, final)
    finally:
        for stream in streams:
            try:
                stream.close()
            except Exception:
                pass
        for temp in temp_paths:
            temp.unlink(missing_ok=True)

    prior_multi_key = {sid: sorted(keys) for sid, keys in seen.items() if len(keys) > 1}
    repair_doc = {
        "contract_id": "V4_01_SECURITY_ALIAS_BOARD_REPAIR_R7",
        "version": "7.0.0",
        "status": "PASS_WITH_BOUNDED_ALIAS_REPAIR" if not prior_multi_key else "BLOCKED_UNRESOLVED_CODE_CHANGE_IDENTITIES",
        "required_scope": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"],
        "target": {"security_id": TARGET_CURRENT_ID, "predecessor_identity_id": TARGET_PREDECESSOR_ID,
                   "aliases": [{"historical_alias": "SZ.300114", "effective_from": "2010-08-27", "effective_to": "2025-02-16"},
                               {"historical_alias": "SZ.302132", "effective_from": "2025-02-17", "effective_to": None}],
                   "exchange": "SZ", "board": "CHINEXT", "board_effective_from": "2010-08-27", "board_effective_to": None},
        "evidence": {"source_ref": "https://disc.static.szse.cn/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF",
                     "source_capture_path": "data/v4/source_evidence/v4_02_r3/szse_2025_028_code_change_302132.pdf",
                     "source_capture_sha256": sha(evidence_path),
                     "source_revision": "公告2025-028; 代码变更启用日2025-02-17"},
        "scan": {"input_membership_rows": input_rows, "output_membership_rows": output_rows,
                 "merged_target_identity_session_rows": merged_rows,
                 "target_alias_history": {sid: sorted(keys) for sid, keys in target_id_key_history.items()},
                 "preexisting_multi_alias_stable_identities": len(prior_multi_key),
                 "preexisting_multi_alias_examples": dict(list(sorted(prior_multi_key.items()))[:25]),
                 "unresolved_required_scope_code_change_identities": len(prior_multi_key)},
        "outputs": {},
        "next_stage": "REBUILD_AFFECTED_DAILY_PERIOD_AND_PRICE_LIMIT_ARTIFACTS; V4-03_BLOCKED",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    for path in (*paths, identity_r7_path):
        repair_doc["outputs"][str(path.relative_to(ROOT)).replace("\\", "/")] = {"sha256": sha(path), "bytes": path.stat().st_size}
    atomic_json(ROOT / "reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json", repair_doc)
    print(json.dumps({"status": repair_doc["status"], "input_rows": input_rows,
                      "output_rows": output_rows, "merged_rows": merged_rows,
                      "unresolved": len(prior_multi_key), "output_paths": repair_doc["outputs"]}, ensure_ascii=False))
    return 0 if not prior_multi_key else 2


if __name__ == "__main__":
    raise SystemExit(main())
