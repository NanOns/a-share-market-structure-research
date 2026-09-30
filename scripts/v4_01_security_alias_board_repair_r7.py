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
from workbench_analysis.dated_security_alias import DatedSecurityAliasResolver

REPAIR_CONTRACT = Path("data/v4/source_evidence/v4_01/security_alias_board_repair_r7_contract_v1.json")


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
    repair_contract = json.loads((ROOT / REPAIR_CONTRACT).read_text(encoding="utf-8"))
    target_current_id = repair_contract["stable_security_id"]
    superseded_identity_ids = set(repair_contract["superseded_identity_ids"])
    target_identity_ids = superseded_identity_ids | {target_current_id}
    alias_specs = repair_contract["aliases"]
    aliases_by_key = {item["source_security_key"]: item for item in alias_specs}
    target_keys = set(aliases_by_key)
    current_key = next(item["source_security_key"] for item in alias_specs if item["alias_role"] == "CURRENT")
    store = ROOT / "data/v4/artifact_store"
    input_universe = store / "v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz"
    input_status = store / "v4_02/V4_02_DATED_TRADING_STATUS_R6_2_20260926.jsonl.gz"
    input_isst = store / "v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926_RECOVERED_R1.jsonl.gz"
    identity_path = store / "v4_01/security_entity_map_R5_20260925.json"
    evidence_ref = repair_contract["official_evidence"]
    evidence_path = ROOT / evidence_ref["capture_path"]
    out_universe = store / "v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz"
    out_status = store / "v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz"
    out_isst = store / "v4_02/V4_02_DATED_ST_STATUS_R7_20260927.jsonl.gz"
    out_identity = store / "v4_01/security_entity_map_R7_20260927.json"

    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    records = identity["records"]
    selected = [row for row in records if row.get("security_id") in target_identity_ids]
    if {row.get("source_security_key") for row in selected} != target_keys:
        raise SystemExit("R7_TARGET_IDENTITY_INPUT_SET_MISMATCH")
    if sha(evidence_path) != evidence_ref["capture_sha256"]:
        raise SystemExit("R7_OFFICIAL_IDENTITY_EVIDENCE_HASH_MISMATCH")

    # Keep the identity already assigned to the replacement code as the one
    # stable ID, and express both exchange aliases as dated records.
    repaired_records = [row for row in records if row not in selected]
    source_revision = "sha256:" + sha(evidence_path)
    alias_template = dict(next(row for row in selected if row.get("security_id") == target_current_id))
    for alias_spec in alias_specs:
        key = alias_spec["source_security_key"]
        repaired = dict(alias_template)
        repaired.update({
            "security_id": target_current_id,
            "lifecycle_entity_id": target_current_id,
            "source_security_key": key,
            "symbol": key,
            "exchange": alias_spec["exchange"],
            "board": alias_spec["board"],
            "list_date": alias_spec["list_date"],
            "delist_date": alias_spec.get("delist_date"),
            "symbol_effective_from": alias_spec["symbol_effective_from"],
            "symbol_effective_to": alias_spec.get("symbol_effective_to"),
            "identity_quality": "OFFICIAL_DATED_CODE_CHANGE_REPAIR_R7",
            "alias_role": alias_spec["alias_role"],
            "source_contract_id": "V4_01_SECURITY_ALIAS_BOARD_REPAIR_R7",
            "source_revision_id": source_revision,
            "evidence_source": evidence_ref["source_revision_label"],
        })
        repaired_records.append(repaired)
    alias_evidence_ref = evidence_ref["source_ref"]
    alias_facts = [{
        "security_id": row["security_id"], "source_security_key": row["source_security_key"],
        "effective_from": row["symbol_effective_from"], "effective_to": row.get("symbol_effective_to"),
        "exchange": row["exchange"], "board": row["board"], "alias_role": row["alias_role"],
        "source_revision": source_revision, "evidence_ref": alias_evidence_ref,
        "evidence_hash": sha(evidence_path),
    } for row in repaired_records if row.get("security_id") == target_current_id]
    alias_resolver = DatedSecurityAliasResolver(alias_facts)
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
    input_rows = output_rows = target_sessions_emitted = duplicate_rows_removed = 0
    target_days: set[str] = set()
    target_id_key_history: dict[str, set[str]] = defaultdict(set)

    try:
        with gzip.open(input_universe, "rt", encoding="utf-8") as u, \
             gzip.open(input_status, "rt", encoding="utf-8") as s, \
             gzip.open(input_isst, "rt", encoding="utf-8") as i:
            day_rows: list[tuple[dict, dict, dict]] = []
            current_day = None

            def emit_group(group: list[tuple[dict, dict, dict]]) -> None:
                nonlocal output_rows, target_sessions_emitted, duplicate_rows_removed
                by_key: dict[str, tuple[dict, dict, dict]] = {}
                passthrough = []
                for ur, sr, ir in group:
                    sid = ur.get("security_id")
                    key = ur.get("source_security_key")
                    if sid in target_identity_ids or key in target_keys:
                        if key not in target_keys or sid not in target_identity_ids:
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
                if not set(by_key).issubset(target_keys):
                    raise RuntimeError("R7_TARGET_ALIAS_SET_INVALID")
                target_days.add(str(group[0][0]["trade_date"]).replace("-", ""))
                duplicate_rows_removed += max(0, len(by_key) - 1)
                chosen = by_key.get(current_key) or next(iter(by_key.values()))
                bar_present = any(pair[0].get("source_bar_present") is True for pair in by_key.values())
                status_values = {pair[1].get("status") for pair in by_key.values()}
                if len(status_values) > 1 and status_values != {"ACTUAL_TRADED", "SUSPENDED"}:
                    raise RuntimeError(f"R7_DUPLICATE_TARGET_TRADING_STATUS_CONFLICT:{group[0][0].get('trade_date')}:{sorted(status_values)}")
                isst_values = {pair[2].get("is_st") for pair in by_key.values()}
                if len(isst_values) > 1:
                    raise RuntimeError(f"R7_DUPLICATE_TARGET_ISST_CONFLICT:{group[0][0].get('trade_date')}:{sorted(map(str, isst_values))}")
                date_value = str(chosen[0]["trade_date"]).replace("-", "")
                alias = alias_resolver.resolve_alias(target_current_id, date_value)
                board_scope = alias_resolver.resolve_board(target_current_id, date_value)
                if alias is None or board_scope is None:
                    raise RuntimeError("R7_DATED_ALIAS_RESOLUTION_MISSING")
                ur, sr, ir = by_key.get(alias, chosen)
                ur["source_bar_present"] = bar_present
                if bar_present:
                    ur["eligibility_status"] = "EVALUABLE_BAR_AVAILABLE"
                if len(status_values) > 1:
                    sr["status"] = "ACTUAL_TRADED" if bar_present else "SUSPENDED"
                    sr["status_source"] = "LOCAL_TDX_BAR_PRESENCE_MERGED_ACROSS_DATED_ALIASES"
                for row in (ur, sr, ir):
                    row["security_id"] = target_current_id
                    row["source_security_key"] = alias
                    row["historical_exchange_symbol"] = alias
                    row["provider_roster_code"] = current_key
                    row["code_change_source_revision"] = source_revision
                ur["board_scope"] = board_scope
                ur["membership_basis"] = "R7_OFFICIAL_DATED_ALIAS_AND_BOARD_REPAIR"
                ir["binding_quality"] = "STABLE_ID_WITH_DATED_HISTORICAL_ALIAS_R7"
                for stream, row in zip(streams, (ur, sr, ir), strict=True):
                    stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                output_rows += 1
                target_sessions_emitted += 1

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
        "target": {"security_id": target_current_id,
                   "predecessor_identity_ids": sorted(superseded_identity_ids),
                   "aliases": [{"historical_alias": item["source_security_key"],
                                "effective_from": item["symbol_effective_from"],
                                "effective_to": item.get("symbol_effective_to"),
                                "alias_role": item["alias_role"]} for item in alias_specs],
                   "board_effective_from": repair_contract["board_effective_from"],
                   "board_effective_to": repair_contract.get("board_effective_to")},
        "evidence": {"source_ref": alias_evidence_ref,
                     "source_capture_path": evidence_ref["capture_path"],
                     "source_capture_sha256": sha(evidence_path),
                     "source_revision": evidence_ref["source_revision_label"]},
        "scan": {"input_membership_rows": input_rows, "output_membership_rows": output_rows,
                 "target_identity_session_rows_emitted": target_sessions_emitted,
                 "duplicate_membership_rows_removed": duplicate_rows_removed,
                 "target_alias_history": {sid: sorted(keys) for sid, keys in target_id_key_history.items()},
                 "preexisting_multi_alias_stable_identities": len(prior_multi_key),
                 "preexisting_multi_alias_examples": dict(list(sorted(prior_multi_key.items()))[:25]),
                 "unresolved_required_scope_code_change_identities": len(prior_multi_key)},
        "outputs": {},
        "execution_identity": {"script_sha256": sha(Path(__file__).resolve())},
        "next_stage": "REBUILD_AFFECTED_DAILY_PERIOD_AND_PRICE_LIMIT_ARTIFACTS; V4-03_BLOCKED",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    for path in (*paths, identity_r7_path):
        repair_doc["outputs"][str(path.relative_to(ROOT)).replace("\\", "/")] = {"sha256": sha(path), "bytes": path.stat().st_size}
    atomic_json(ROOT / "reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json", repair_doc)
    print(json.dumps({"status": repair_doc["status"], "input_rows": input_rows,
                      "output_rows": output_rows, "target_sessions": target_sessions_emitted,
                      "duplicate_rows_removed": duplicate_rows_removed,
                      "unresolved": len(prior_multi_key), "output_paths": repair_doc["outputs"]}, ensure_ascii=False))
    return 0 if not prior_multi_key else 2


if __name__ == "__main__":
    raise SystemExit(main())
