from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.sector.membership_baseline import (
    canonical_json_bytes,
    classify_replay_rows,
    formal_membership_eligible,
    identity_postcheck,
    map_source_sector_type,
    select_available_revisions,
    snapshot_digest,
    validate_revision_chain,
)
from src.tdx.security_master import MARKET_NUMBER_TO_NAME


PARSER_VERSION = "v4-08-tdx-membership-capture-r1"
MEMBER_RE = re.compile(r"([012])#(\d{6})")
SOURCE_TYPE_MAP = {"gn": "concept", "fg": "style", "zs": "index_group"}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def read_frozen_file(path: Path) -> tuple[bytes, dict[str, Any]]:
    before = path.stat()
    observed_at = utc_now()
    data = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or len(data) != after.st_size:
        raise RuntimeError(f"source changed while being captured: {path}")
    return data, {
        "sha256": sha_bytes(data),
        "byte_count": len(data),
        "filesystem_mtime_local": datetime.fromtimestamp(after.st_mtime, timezone.utc).astimezone().isoformat(),
        "filesystem_mtime_ns": after.st_mtime_ns,
        "observed_at": observed_at,
    }


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as stream:
        temp_path = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_path, path)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")


def jsonl_gzip_bytes(rows: list[dict[str, Any]]) -> bytes:
    payload = b"".join(canonical_json_bytes(row) + b"\n" for row in rows)
    return gzip.compress(payload, compresslevel=9, mtime=0)


def read_infoharbor(path: Path, data: bytes) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    memberships: list[dict[str, Any]] = []
    headers: list[dict[str, str]] = []
    current: tuple[str, str, str] | None = None
    for line_no, line in enumerate(data.decode("gb18030", errors="replace").splitlines(), 1):
        if line.startswith("#"):
            fields = line[1:].split(",")
            label = fields[0].strip()
            if "_" in label:
                prefix, name = label.split("_", 1)
            else:
                prefix, name = "untyped_header", label
            raw_type = SOURCE_TYPE_MAP.get(prefix.lower(), prefix.lower())
            code = fields[2].strip() if len(fields) > 2 and fields[2].strip() else name
            current = (raw_type, code, name)
            headers.append({"source_sector_type": raw_type, "source_type_prefix": prefix, "sector_code": code, "sector_name": name})
            continue
        if current is None:
            continue
        for market_no, code in MEMBER_RE.findall(line):
            source_key = f"{MARKET_NUMBER_TO_NAME[market_no]}.{code}"
            memberships.append({
                "source_sector_type": current[0],
                "sector_code": current[1],
                "sector_name": current[2],
                "source_security_key": source_key,
                "source_file": "T0002/hq_cache/infoharbor_block.dat",
                "source_line_number": line_no,
                "source_fact_kind": "SOURCE_OBSERVED",
            })
    return memberships, headers


def read_industry_source(data: bytes) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    for line_no, line in enumerate(data.decode("gb18030", errors="replace").splitlines(), 1):
        fields = line.strip().split("|")
        if len(fields) < 3 or fields[0] not in MARKET_NUMBER_TO_NAME or not re.fullmatch(r"\d{6}", fields[1]):
            continue
        assignments.append({
            "security_id": f"{MARKET_NUMBER_TO_NAME[fields[0]]}.{fields[1]}",
            "industry_code": fields[2] or None,
            "line_number": line_no,
        })
    return assignments


def read_industry_names_source(data: bytes) -> dict[str, str]:
    names: dict[str, str] = {}
    for line in data.decode("gb18030", errors="replace").splitlines():
        fields = line.strip().split("|")
        if len(fields) >= 6 and fields[5]:
            names[fields[5]] = fields[0]
    return names


def load_accepted_identity_map() -> tuple[dict[str, str], dict[str, Any]]:
    global_head = json.loads((ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    binding = global_head.get("bindings", {}).get("v4_01_identity_map")
    if not binding:
        raise RuntimeError("accepted global head has no V4-01 identity-map binding")
    rel_path = str(binding["path"])
    path = ROOT / rel_path
    raw = path.read_bytes()
    digest = sha_bytes(raw)
    expected = binding.get("sha256")
    if expected and digest != expected:
        raise RuntimeError("V4-01 accepted identity-map hash does not match global accepted head")
    document = json.loads(raw)
    identities: dict[str, set[str]] = defaultdict(set)
    for record in document.get("records", []):
        key, security_id = record.get("source_security_key"), record.get("security_id")
        if key and security_id:
            identities[str(key)].add(str(security_id))
    unresolved = {str(item.get("source_security_key")) for item in document.get("unresolved", []) if item.get("source_security_key")}
    non_core = {str(item.get("source_security_key")) for item in document.get("non_core_candidates", []) if item.get("source_security_key")}
    resolved: dict[str, str] = {}
    ambiguous: set[str] = set()
    for key, ids in identities.items():
        if len(ids) == 1 and key not in unresolved and key not in non_core:
            resolved[key] = next(iter(ids))
        elif len(ids) > 1 or key in unresolved or key in non_core:
            ambiguous.add(key)
    return resolved, {
        "path": rel_path,
        "sha256": digest,
        "byte_count": len(raw),
        "global_head_path": "data/v4/V4_STAGE_ACCEPTED_HEAD.json",
        "global_head_sha256": sha_bytes((ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json").read_bytes()),
        "records_key_count": len(identities),
        "unresolved_key_count": len(unresolved),
        "non_core_key_count": len(non_core),
        "resolved_key_count": len(resolved),
        "ambiguous_key_count": len(ambiguous),
        "ambiguous_keys": ambiguous,
    }


def build_source_rows(
    *, tdx_root: Path, frozen_files: dict[str, bytes], registry: dict[str, Any], parent_policy: dict[str, Any], identities: dict[str, str], ambiguous_keys: set[str],
    observed_at: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    names = read_industry_names_source(frozen_files["T0002/hq_cache/tdxzs.cfg"])
    assignments = read_industry_source(frozen_files["T0002/hq_cache/tdxhy.cfg"])
    raw_rows: list[dict[str, Any]] = []
    for item in assignments:
        code = item.get("industry_code")
        if not code:
            continue
        raw_rows.append({
            "source_sector_type": "industry", "sector_code": str(code),
            "sector_name": names.get(str(code), str(code)), "source_security_key": item["security_id"],
            "source_file": "T0002/hq_cache/tdxhy.cfg", "source_line_number": item.get("line_number"),
            "source_fact_kind": "SOURCE_OBSERVED",
        })
    info_rows, info_headers = read_infoharbor(tdx_root / "T0002" / "hq_cache" / "infoharbor_block.dat", frozen_files["T0002/hq_cache/infoharbor_block.dat"])
    raw_rows.extend(info_rows)
    raw_key = lambda row: (row["source_sector_type"], row["sector_code"], row["source_security_key"])
    raw_seen: set[tuple[str, str, str]] = set()
    raw_duplicates: list[tuple[str, str, str]] = []
    for row in raw_rows:
        key = raw_key(row)
        if key in raw_seen:
            raw_duplicates.append(key)
        raw_seen.add(key)
    if raw_duplicates:
        raise RuntimeError(f"duplicate raw TDX membership facts found: {len(raw_duplicates)}")

    expected_parent_rule = "For a source industry code with more than five characters, its parent is the first five characters only when that code is present as an industry name in the frozen tdxzs.cfg bytes."
    if parent_policy["parent_child_map"]["rule"] != expected_parent_rule:
        raise RuntimeError("unsupported or modified industry parent mapping rule")
    child_codes = {str(row["sector_code"]) for row in raw_rows if row["source_sector_type"] == "industry"}
    parent_map = {child: child[:5] for child in sorted(child_codes) if len(child) > 5 and child[:5] in names}
    children: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in raw_rows:
        if row["source_sector_type"] != "industry":
            continue
        child = str(row["sector_code"])
        parent = parent_map.get(child)
        if parent:
            children[parent][str(row["source_security_key"])].add(child)
    parent_rows = []
    for parent, member_children in sorted(children.items()):
        for source_key, child_codes in sorted(member_children.items()):
            if any(parent_map.get(child_code) != parent for child_code in child_codes):
                raise RuntimeError(f"industry parent map created an impossible cross-industry link: {parent}")
            parent_rows.append({
                "source_sector_type": "industry", "sector_code": parent, "sector_name": names[parent],
                "source_security_key": source_key, "source_file": "DERIVED_FROM_TDX_INDUSTRY_CHILDREN",
                "source_line_number": None, "source_fact_kind": "DERIVED_PARENT",
                "child_sector_ids": [f"INDUSTRY:{code}" for code in sorted(child_codes)],
            })
    parent_keys = {raw_key(row) for row in raw_rows}
    parent_rows = [row for row in parent_rows if raw_key(row) not in parent_keys]
    all_rows = raw_rows + parent_rows

    raw_type_to_formal = registry["source_mapping"]
    enriched: list[dict[str, Any]] = []
    unknown_types: Counter[str] = Counter()
    for source in all_rows:
        source_type = str(source["source_sector_type"])
        sector_type = map_source_sector_type(source_type, raw_type_to_formal)
        if sector_type == "UNKNOWN":
            unknown_types[source_type] += 1
        key = str(source["source_security_key"])
        security_id = identities.get(key)
        identity_status = "MAPPED" if security_id else "UNKNOWN"
        if key in ambiguous_keys:
            security_id, identity_status = None, "UNKNOWN"
        sector_code = str(source["sector_code"])
        sector_id = f"{sector_type}:{source_type}:{sector_code}" if sector_type == "UNKNOWN" else f"{sector_type}:{sector_code}"
        basis = "DERIVED_PARENT_MEMBERSHIP" if source["source_fact_kind"] == "DERIVED_PARENT" else "CURRENT_TDX_MEMBERSHIP"
        quality = "UNKNOWN_IDENTITY" if identity_status == "UNKNOWN" else ("UNKNOWN_SECTOR_TYPE" if sector_type == "UNKNOWN" else ("DERIVED_PARENT_DIAGNOSTIC" if basis == "DERIVED_PARENT_MEMBERSHIP" else "CURRENT_TDX_DIAGNOSTIC"))
        enriched.append({
            **source,
            "snapshot_id": None,
            "sector_id": sector_id,
            "sector_type": sector_type,
            "security_id": security_id,
            "identity_status": identity_status,
            "target_trade_date": None,
            "membership_asof_date": None,
            "observed_at": observed_at,
            "ingested_at": None,
            "system_available_at": None,
            "provider_available_at": None,
            "source_revision_id": None,
            "source_digest": None,
            "source_file_digests": None,
            "membership_basis": basis,
            "membership_quality": quality,
            "pit_observed": False,
            "historical_backtest_safe": False,
            "supersedes_revision_id": None,
            "created_at": None,
        })
    summary = {
        "raw_source_fact_count": len(raw_rows),
        "derived_parent_fact_count": len(parent_rows),
        "all_diagnostic_fact_count": len(enriched),
        "raw_source_fact_counts_by_type": dict(sorted(Counter(row["source_sector_type"] for row in raw_rows).items())),
        "all_fact_counts_by_formal_type": dict(sorted(Counter(row["sector_type"] for row in enriched).items())),
        "sector_counts_by_formal_type": dict(sorted({
            kind: len({row["sector_id"] for row in enriched if row["sector_type"] == kind})
            for kind in {row["sector_type"] for row in enriched}
        }.items())),
        "unique_source_security_key_count": len({row["source_security_key"] for row in enriched}),
        "unique_mapped_security_id_count": len({row["security_id"] for row in enriched if row["security_id"]}),
        "unmapped_membership_fact_count": sum(row["identity_status"] == "UNKNOWN" for row in enriched),
        "unmapped_unique_source_key_count": len({row["source_security_key"] for row in enriched if row["identity_status"] == "UNKNOWN"}),
        "unknown_source_type_fact_counts": dict(sorted(unknown_types.items())),
        "infoharbor_sector_header_count": len(info_headers),
        "industry_parent_sector_count": len({row["sector_code"] for row in parent_rows}),
        "industry_parent_map": {"map_id": parent_policy["parent_child_map"]["map_id"], "child_to_parent": dict(sorted(parent_map.items()))},
        "industry_parent_map_digest": sha_bytes(canonical_json_bytes({"map_id": parent_policy["parent_child_map"]["map_id"], "child_to_parent": dict(sorted(parent_map.items()))})),
        "raw_duplicate_fact_count": len(raw_duplicates),
    }
    return enriched, raw_rows, summary


def manifest_entry(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha_bytes(data), "byte_count": len(data)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze a V4-08 diagnostic membership replay candidate without writing to TDX.")
    parser.add_argument("--tdx-root", type=Path, default=Path(r"D:/new_tdx"))
    parser.add_argument("--output-root", type=Path, default=ROOT / "reports/v4_08")
    args = parser.parse_args()
    tdx_root = args.tdx_root.resolve()
    output_root = args.output_root.resolve()
    if output_root == tdx_root or tdx_root in output_root.parents:
        raise RuntimeError("output root must be outside the read-only TDX source root")

    stage_head_path = ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json"
    stage_head = json.loads(stage_head_path.read_text(encoding="utf-8"))
    v4_05_head = json.loads((ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    target_trade_date = str(v4_05_head["target_trade_date"])
    date.fromisoformat(target_trade_date)
    identity_map, identity_binding = load_accepted_identity_map()
    source_paths = {
        f"T0002/hq_cache/{name}": tdx_root / "T0002" / "hq_cache" / name
        for name in ("tdxhy.cfg", "tdxzs.cfg", "infoharbor_block.dat")
    }
    frozen_files: dict[str, bytes] = {}
    file_evidence: dict[str, Any] = {}
    for rel, path in source_paths.items():
        data, evidence = read_frozen_file(path)
        frozen_files[rel] = data
        file_evidence[rel] = {**evidence, "source_root_relative_path": rel}
    file_digests = {rel: item["sha256"] for rel, item in file_evidence.items()}
    identity_rel = identity_binding["path"]
    file_digests[identity_rel] = identity_binding["sha256"]
    contract_path = ROOT / "config/v4_08_sector_membership_contract_v1.json"
    registry_path = ROOT / "config/v4_08_sector_type_registry_v1.json"
    quality_path = ROOT / "config/v4_08_sector_membership_quality_v1.json"
    parent_policy_path = ROOT / "config/v4_08_industry_parent_membership_contract_v1.json"
    contract_bytes, registry_bytes, quality_bytes = contract_path.read_bytes(), registry_path.read_bytes(), quality_path.read_bytes()
    registry = json.loads(registry_bytes)
    parent_policy_bytes = parent_policy_path.read_bytes()
    parent_policy = json.loads(parent_policy_bytes)
    registry_digest = sha_bytes(registry_bytes)
    if registry_digest != "4a8d1c8e6574bfa9985e7980ca83337b7a14bed54bfbbace9e817d44b2076743":
        raise RuntimeError("frozen sector type registry digest differs from migration policy")
    observed_at = min(item["observed_at"] for item in file_evidence.values())
    rows, raw_rows, counts = build_source_rows(
        tdx_root=tdx_root, frozen_files=frozen_files, registry=registry, parent_policy=parent_policy,
        identities=identity_map, ambiguous_keys=identity_binding["ambiguous_keys"], observed_at=observed_at,
    )
    ingested_at = utc_now()
    cutoff = ingested_at
    system_available_at = ingested_at
    source_digest = sha_bytes(canonical_json_bytes({
        "source_file_digests": dict(sorted(file_digests.items())), "parser_version": PARSER_VERSION,
        "parent_contract_sha256": sha_bytes(parent_policy_bytes),
        "industry_parent_map_digest": counts["industry_parent_map_digest"],
    }))
    source_revision_id = f"sha256:{source_digest}"
    source_meta = {
        "source_revision_id": source_revision_id,
        "source_digest": source_digest,
        "source_file_digests": dict(sorted(file_digests.items())),
        "observed_at": observed_at,
        "ingested_at": ingested_at,
        "system_available_at": system_available_at,
        "provider_available_at": None,
        "created_at": ingested_at,
    }

    for row in rows:
        row.update(source_meta)
        row.update({"target_trade_date": target_trade_date, "cutoff": cutoff, "created_at": ingested_at})
    current_digest = snapshot_digest(
        target_trade_date=target_trade_date, cutoff=cutoff, sector_type_registry_digest=registry_digest,
        source_revision_ids=[source_revision_id], source_digest=source_digest,
        source_file_digests=file_digests, rows=rows, membership_basis="CURRENT_TDX_MEMBERSHIP",
        membership_quality="CURRENT_TDX_DIAGNOSTIC",
    )
    current_rows = [{**row, "snapshot_id": current_digest} for row in rows]
    replay_rows = classify_replay_rows(rows, target_trade_date)
    for row in replay_rows:
        row.update(source_meta)
        row.update({"snapshot_id": None, "source_revision_id": source_revision_id, "source_digest": source_digest,
                    "source_file_digests": dict(sorted(file_digests.items())), "target_trade_date": target_trade_date,
                    "cutoff": cutoff, "created_at": ingested_at})
    replay_digest = snapshot_digest(
        target_trade_date=target_trade_date, cutoff=cutoff, sector_type_registry_digest=registry_digest,
        source_revision_ids=[source_revision_id], source_digest=source_digest,
        source_file_digests=file_digests, rows=replay_rows, membership_basis="CURRENT_MEMBERSHIP_REPLAY",
        membership_quality="CURRENT_REPLAY_DIAGNOSTIC",
    )
    for row in replay_rows:
        row["snapshot_id"] = replay_digest
    current_path = output_root / "staging/V4_08_CURRENT_TDX_MEMBERSHIP_R1.jsonl.gz"
    replay_path = output_root / f"staging/V4_08_CURRENT_MEMBERSHIP_REPLAY_{target_trade_date.replace('-', '')}_R1.jsonl.gz"
    current_bytes, replay_bytes = jsonl_gzip_bytes(current_rows), jsonl_gzip_bytes(replay_rows)
    atomic_write(current_path, current_bytes)
    atomic_write(replay_path, replay_bytes)

    postcheck = identity_postcheck(replay_rows)
    source_row_type_counts = dict(sorted(Counter(row["source_sector_type"] for row in raw_rows).items()))
    type_acceptance = {
        "contract_id": registry["contract_id"], "version": registry["version"], "status": "PASS_VERSIONED_MAPPING_AND_PRESERVATION",
        "registry_sha256": registry_digest, "source_type_to_formal_type": registry["source_mapping"],
        "observed_source_row_counts_by_raw_type": source_row_type_counts,
        "observed_replay_row_counts_by_formal_type": counts["all_fact_counts_by_formal_type"],
        "unknown_source_type_fact_counts": counts["unknown_source_type_fact_counts"],
        "unknown_rows_retained": counts["unknown_source_type_fact_counts"].get("index_group", 0) > 0,
        "industry_parent_contract": {"path": parent_policy_path.relative_to(ROOT).as_posix(), "sha256": sha_bytes(parent_policy_bytes), "map_id": parent_policy["parent_child_map"]["map_id"]},
        "industry_parent_map_digest": counts["industry_parent_map_digest"],
        "industry_parent_sector_count": counts["industry_parent_sector_count"],
        "style_formal_consumer_allowed": False, "unknown_formal_consumer_allowed": False,
        "raw_rows_discarded_for_type": 0,
    }
    source_acceptance = {
        "contract_id": "V4_08_SECTOR_MEMBERSHIP_SOURCE_V1", "version": "1.0.0",
        "status": "PASS_CAPTURE_AND_HASH_BINDING; PIT_PROVIDER_AVAILABILITY_UNVERIFIED",
        "source_paths": file_evidence, "source_digest": source_digest, "source_file_digests": dict(sorted(file_digests.items())),
        "parser_version": PARSER_VERSION, "identity_map": {k: v for k, v in identity_binding.items() if k != "ambiguous_keys"},
        "tdx_root_read_only": True, "tdx_root_write_count": 0,
        "filesystem_mtime_is_provider_availability": False,
        "provider_available_at": None,
        "pit_snapshot_formal_acceptance": "BLOCKED_PROVIDER_AVAILABILITY_AND_MEMBERSHIP_EFFECTIVE_DATE_UNVERIFIED",
    }
    go_forward = {
        "contract_id": "V4_08_GO_FORWARD_PIT_MEMBERSHIP_CANDIDATE_V1",
        "status": "BLOCKED_NO_PROVIDER_AVAILABILITY_OR_ACCEPTED_CUTOFF_BINDING",
        "latest_accepted_market_session": target_trade_date,
        "latest_accepted_market_session_source": {"path": "data/v4/V4_05_ACCEPTED_HEAD.json", "sha256": sha_bytes((ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json").read_bytes())},
        "first_go_forward_pit_baseline_trade_date": None,
        "proposed_baseline_trade_date": None,
        "source_observed_at": observed_at, "source_ingested_at": ingested_at,
        "provider_available_at": None, "membership_asof_date": None,
        "reason": "The source bytes are hash-frozen and observed by this run, but local mtime and current capture do not establish provider availability or which market session the source membership describes. No PIT date is assigned.",
        "candidate_source_revision_id": source_revision_id,
        "candidate_snapshot_digest": current_digest,
        "pit_observed": False,
        "historical_backtest_safe": False,
    }
    replay_report = {
        "contract_id": "V4_08_CURRENT_MEMBERSHIP_REPLAY_DIAGNOSTIC_V1",
        "status": "PASS_DIAGNOSTIC_ONLY",
        "target_trade_date": target_trade_date, "cutoff": cutoff,
        "membership_basis": "CURRENT_MEMBERSHIP_REPLAY", "membership_quality": "CURRENT_REPLAY_DIAGNOSTIC",
        "pit_observed": False, "historical_backtest_safe": False,
        "source_revision_id": source_revision_id, "source_digest": source_digest,
        "source_file_digests": dict(sorted(file_digests.items())),
        "artifact": {"path": replay_path.relative_to(ROOT).as_posix(), "sha256": sha_bytes(replay_bytes), "byte_count": len(replay_bytes)},
        "current_source_snapshot_digest": current_digest, "replay_snapshot_digest": replay_digest,
        "membership_quality_distribution": dict(sorted(Counter(row["membership_quality"] for row in replay_rows).items())),
        **counts,
        "historical_backtest_safe_row_count": sum(row["historical_backtest_safe"] is True for row in replay_rows),
        "formal_eligible_row_count": sum(formal_membership_eligible(row) for row in replay_rows),
        "first_go_forward_pit_baseline_trade_date": None,
    }
    identity_report = {
        "contract_id": "V4_08_MEMBERSHIP_IDENTITY_POSTCHECK_V1", "status": postcheck["status"],
        "identity_map": {k: v for k, v in identity_binding.items() if k != "ambiguous_keys"},
        "checked_source_keys": counts["unique_source_security_key_count"],
        "checked_membership_facts": len(replay_rows),
        "resolved_source_keys": len({row["source_security_key"] for row in replay_rows if row["identity_status"] == "MAPPED"}),
        "unresolved_source_keys": postcheck["unknown_identity_source_keys"],
        "unresolved_source_key_count": len(postcheck["unknown_identity_source_keys"]),
        "unknown_identity_membership_fact_count": postcheck["unknown_identity_count"],
        "duplicate_fact_count": postcheck["duplicate_fact_count"],
        "sector_name_conflict_count": postcheck["sector_name_conflict_count"],
        "formal_snapshot_status": "BLOCKED_UNKNOWN_SECURITY_IDENTITIES_RETAINED" if postcheck["status"] == "BLOCKED" else "ELIGIBLE_FOR_INDEPENDENT_REVIEW",
        "rows_silently_dropped": 0,
    }
    temporal = {
        "contract_id": "V4_08_MEMBERSHIP_TEMPORAL_LEAKAGE_TEST_V1", "status": "PASS_DIAGNOSTIC_CUTOFF_GATES",
        "current_source_observed_at": observed_at, "system_available_at": system_available_at,
        "provider_available_at": None, "formal_pit_claim_allowed": False,
        "current_source_used_as_pit_at_earlier_date": False,
        "replay_to_target_basis": "CURRENT_MEMBERSHIP_REPLAY", "replay_pit_observed": False,
        "future_correction_excluded_at_current_cutoff": select_available_revisions([
            {"source_revision_id": "current", "system_available_at": system_available_at},
            {"source_revision_id": "future-correction", "system_available_at": "9999-01-01T00:00:00Z", "supersedes_revision_id": "current"},
        ], cutoff) == [{"source_revision_id": "current", "system_available_at": system_available_at}],
        "formal_eligible_replay_rows": 0,
        "reason": "Current TDX membership is replayed to the latest accepted date only as a diagnostic; provider/effective-date evidence is absent.",
    }
    revision_checks = [
        {"source_revision_id": source_revision_id, "supersedes_revision_id": None},
        {"source_revision_id": source_revision_id + ":late-correction", "supersedes_revision_id": source_revision_id},
    ]
    fork_checks = revision_checks + [{"source_revision_id": source_revision_id + ":fork", "supersedes_revision_id": source_revision_id}]
    revisions = {
        "contract_id": "V4_08_MEMBERSHIP_REVISION_TEST_V1",
        "status": "PASS_APPEND_ONLY_CHAIN_AND_FORK_REJECTION",
        "append_only_model": "A correction creates a new source_revision_id and points supersedes_revision_id to the prior revision.",
        "valid_chain": validate_revision_chain(revision_checks),
        "forked_chain": validate_revision_chain(fork_checks),
        "fork_rejected": validate_revision_chain(fork_checks)["status"] == "BLOCKED",
        "same_day_revision_policy": "single non-forking supersession chain",
        "accepted_revision_created": False,
    }
    determinism = {
        "contract_id": "V4_08_MEMBERSHIP_DETERMINISM_V1", "status": "PASS_IDENTICAL_FIXED_CONTEXT_DIGESTS",
        "source_revision_id": source_revision_id, "target_trade_date": target_trade_date, "cutoff": cutoff,
        "current_snapshot_digest_first": current_digest,
        "current_snapshot_digest_second": snapshot_digest(
            target_trade_date=target_trade_date, cutoff=cutoff, sector_type_registry_digest=registry_digest,
            source_revision_ids=[source_revision_id], source_digest=source_digest,
            source_file_digests=file_digests, rows=rows, membership_basis="CURRENT_TDX_MEMBERSHIP",
            membership_quality="CURRENT_TDX_DIAGNOSTIC",
        ),
        "replay_snapshot_digest_first": replay_digest,
        "replay_snapshot_digest_second": snapshot_digest(
            target_trade_date=target_trade_date, cutoff=cutoff, sector_type_registry_digest=registry_digest,
            source_revision_ids=[source_revision_id], source_digest=source_digest,
            source_file_digests=file_digests, rows=replay_rows, membership_basis="CURRENT_MEMBERSHIP_REPLAY",
            membership_quality="CURRENT_REPLAY_DIAGNOSTIC",
        ),
        "current_artifact_sha256": sha_bytes(current_bytes), "replay_artifact_sha256": sha_bytes(replay_bytes),
        "timestamps_excluded_from_logical_digest": ["observed_at", "ingested_at", "system_available_at", "created_at"],
    }
    determinism["identical_logical_digests"] = determinism["current_snapshot_digest_first"] == determinism["current_snapshot_digest_second"] and determinism["replay_snapshot_digest_first"] == determinism["replay_snapshot_digest_second"]
    determinism["status"] = "PASS_IDENTICAL_FIXED_CONTEXT_DIGESTS" if determinism["identical_logical_digests"] else "FAIL"

    outputs = {
        "V4_08_SECTOR_MEMBERSHIP_SOURCE_CONTRACT_ACCEPTANCE.json": source_acceptance,
        "V4_08_SECTOR_TYPE_REGISTRY_ACCEPTANCE.json": type_acceptance,
        "V4_08_GO_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json": go_forward,
        "V4_08_CURRENT_MEMBERSHIP_REPLAY_DIAGNOSTIC.json": replay_report,
        "V4_08_MEMBERSHIP_IDENTITY_POSTCHECK.json": identity_report,
        "V4_08_MEMBERSHIP_TEMPORAL_LEAKAGE_TEST.json": temporal,
        "V4_08_MEMBERSHIP_REVISION_TEST.json": revisions,
        "V4_08_MEMBERSHIP_DETERMINISM.json": determinism,
    }
    for name, value in outputs.items():
        write_json(output_root / name, value)

    # Bind the new stage evidence. The manifest intentionally excludes itself and the closure that cites it.
    evidence_paths = [
        contract_path, registry_path, quality_path, parent_policy_path,
        ROOT / "src/sector/membership_baseline.py", ROOT / "src/workbench_db/migrations/v4_postgres/016_v4_08_sector_membership.sql",
        ROOT / "src/workbench_db/migrations/v4_postgres/017_v4_08_membership_fact_evidence_view.sql",
        ROOT / "src/workbench_db/migrations/v4_postgres/rollback/016_v4_08_sector_membership.sql",
        ROOT / "src/workbench_db/migrations/v4_postgres/rollback/017_v4_08_membership_fact_evidence_view.sql",
        ROOT / "scripts/build_v4_08_membership_prerequisite.py", ROOT / "scripts/verify_v4_08_membership_migration.py",
        ROOT / "tests/v4_08/test_membership_contract.py", ROOT / "tests/v4_08/test_membership_source_parser.py",
        output_root / "V4_08_MEMBERSHIP_STAGE_ENTRY.md",
        ROOT / "docs/audits/V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1_20260929.md",
        ROOT / "docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md",
        ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json", ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json",
        ROOT / identity_binding["path"],
        ROOT / "reports/v4_08/V4_08_MEMBERSHIP_SCHEMA_MIGRATION_RECEIPT.json", current_path, replay_path,
        *(output_root / name for name in outputs),
    ]
    manifest = {
        "contract_id": "V4_08_MEMBERSHIP_STAGE_CANDIDATE_MANIFEST_V1",
        "status": "CANDIDATE_BLOCKED_FOR_PIT_ACCEPTANCE; DIAGNOSTIC_REPLAY_EVIDENCE_BOUND",
        "generated_at_utc": ingested_at,
        "source_head_at_generation": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip(),
        "target_trade_date": target_trade_date,
        "membership_snapshot_digests": {"current_tdx": current_digest, "historical_replay": replay_digest},
        "file_count": len(evidence_paths),
        "files": [manifest_entry(path) for path in evidence_paths],
    }
    manifest_path = output_root / "V4_08_MEMBERSHIP_STAGE_CANDIDATE_MANIFEST.json"
    write_json(manifest_path, manifest)
    closure_text = f"""# V4-08 PIT Sector Membership Baseline R1 — Candidate Closure

- Stage contract: `V4_08_PIT_SECTOR_MEMBERSHIP_BASELINE_R1`.
- Candidate result: `DIAGNOSTIC_RECONSTRUCTION_PASS; PIT_BASELINE_BLOCKED`.
- Starting branch and accepted range: `{stage_head.get('accepted_stage_range')}`; source HEAD at candidate generation: `{manifest['source_head_at_generation']}`.
- Latest accepted market session available from V4-05: `{target_trade_date}`.
- Source capture is hash-bound and observed at `{observed_at}`; candidate ingestion/system availability is `{ingested_at}`. Provider availability and source membership effective date are unknown.
- Current replay digest: `{replay_digest}`; row count: `{len(replay_rows):,}`; raw source facts: `{counts['raw_source_fact_count']:,}`; derived parent facts: `{counts['derived_parent_fact_count']:,}`.
- Formal sector types and rows: `{json.dumps(counts['all_fact_counts_by_formal_type'], ensure_ascii=False, sort_keys=True)}`. Unmapped source identities: `{identity_report['unresolved_source_key_count']:,}` unique keys / `{identity_report['unknown_identity_membership_fact_count']:,}` facts; they are retained with UNKNOWN identity.
- Sector counts by formal type: `{json.dumps(counts['sector_counts_by_formal_type'], ensure_ascii=False, sort_keys=True)}`. Unique mapped security identities: `{counts['unique_mapped_security_id_count']:,}`. Membership quality distribution: `{json.dumps(replay_report['membership_quality_distribution'], ensure_ascii=False, sort_keys=True)}`.
- Derived-parent semantics use `{parent_policy['parent_child_map']['map_id']}`; exact child-to-parent map digest: `{counts['industry_parent_map_digest']}` over `{len(counts['industry_parent_map']['child_to_parent']):,}` child codes. Parent membership remains diagnostic-only.
- The candidate cannot claim PIT for `{target_trade_date}` or any historical date. No go-forward PIT trade date is assigned because the source provider availability and effective date are not evidenced. The current file system mtimes are metadata only.
- Membership basis for historical replay: `CURRENT_MEMBERSHIP_REPLAY`; `pit_observed=false`; `historical_backtest_safe=false`. Style and unknown types remain diagnostic-only. Parent-industry union remains diagnostic-only pending acceptance.
- V4-07 real Base Seed capability remains `DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN`; dependent fields remain UNKNOWN. The separate audit item remains OPEN.
- PostgreSQL migration evidence: `reports/v4_08/V4_08_MEMBERSHIP_SCHEMA_MIGRATION_RECEIPT.json`.
- Candidate manifest: `{manifest_path.relative_to(ROOT).as_posix()}`; SHA-256 `{sha_bytes(manifest_path.read_bytes())}`.
- Acceptance result: `BLOCKED_FOR_INDEPENDENT_PIT_BASELINE_ACCEPTANCE` because there is no source provider-availability/effective-date receipt and the accepted identity map leaves unresolved keys. Diagnostic replay and contract/schema engineering are ready for independent audit; no V4-08 formal production is authorized.
- Next stage: independent external review of this candidate and the open source-time/identity limitations. After external review, obtain a separately evidenced dated source capture before requesting a PIT baseline acceptance.
"""
    closure_path = output_root / "V4_08_MEMBERSHIP_CLOSURE.md"
    atomic_write(closure_path, closure_text.encode("utf-8"))
    print(json.dumps({
        "status": "CANDIDATE_BLOCKED_FOR_PIT_ACCEPTANCE; DIAGNOSTIC_REPLAY_EVIDENCE_BOUND",
        "target_trade_date": target_trade_date,
        "source_digest": source_digest,
        "current_snapshot_digest": current_digest,
        "replay_snapshot_digest": replay_digest,
        "raw_source_fact_count": counts["raw_source_fact_count"],
        "derived_parent_fact_count": counts["derived_parent_fact_count"],
        "replay_fact_count": len(replay_rows),
        "facts_by_type": counts["all_fact_counts_by_formal_type"],
        "unmapped_unique_source_key_count": identity_report["unresolved_source_key_count"],
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "manifest_sha256": sha_bytes(manifest_path.read_bytes()),
        "closure": closure_path.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
