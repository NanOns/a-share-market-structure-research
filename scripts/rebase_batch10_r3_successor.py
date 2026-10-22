"""Build append-only, candidate-safe 10/20 and 10/21 BATCH10-R3 successors.

The 10/20 Core and D0 inputs must be exact, hash-bound reconstructed artifacts.
This tool never changes the formal Head and preserves every predecessor owner
except the explicitly revised 10/20 raw/adjusted/core/prewatch bindings.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path
from datetime import date
from decimal import Decimal
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO_ROOT), str(REPO_ROOT / "src")]
from workbench_analysis.operational_successor_v1 import CONTRACT, digest, validate
from workbench_analysis.r43_owner_replay import checked, ref

REQUIRED_R3_ROWS = 5226
RPS_EVIDENCE = Path("docs/evidence/functional_r8_implementation_20261021/NINTH_BATCH_RPS5_ENDPOINT_REPAIR_R2_EVIDENCE.json")
D0_EVIDENCE = Path("docs/evidence/functional_r8_implementation_20261021/NINTH_BATCH_D0_FOCUS_EXACT_IDENTITY_R3_EVIDENCE.json")


def _atomic(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".batch10r3.tmp")
    with tmp.open("wb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def _load_binding(root: Path, binding: dict) -> tuple[Path, bytes]:
    path = checked(root, binding)
    raw = path.read_bytes()
    if len(raw) != binding.get("bytes") or hashlib.sha256(raw).hexdigest() != binding.get("sha256"):
        raise ValueError("BATCH10_R3_INPUT_BINDING_MISMATCH:" + str(binding.get("path")))
    return path, raw


def _rows(root: Path, binding: dict) -> list[dict]:
    path, _ = _load_binding(root, binding)
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _write_json(root: Path, path: Path, value: dict) -> dict:
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    _atomic(path, raw)
    return ref(root, path)


def _ensure_new(path: Path) -> None:
    if path.exists():
        raise ValueError("PRESERVE_EXISTING_BATCH10_R3_REBASE_GENERATION:" + str(path))


def validate_exact_identity_sets(core_rows: list[dict], d0_rows: list[dict], *, trade_date: str,
                                 expected_rows: int = REQUIRED_R3_ROWS) -> str:
    core_ids = [r.get("security_id") for r in core_rows]
    d0_ids = [r.get("security_id") or r.get("entity_id") for r in d0_rows]
    if len(core_rows) != expected_rows or len(set(core_ids)) != expected_rows or None in core_ids:
        raise ValueError("BATCH10_R3_CORE_NOT_EXACT_5226_UNIQUE_OBJECTS")
    if len(d0_rows) != expected_rows or len(set(d0_ids)) != expected_rows or None in d0_ids:
        raise ValueError("BATCH10_R3_D0_NOT_EXACT_5226_UNIQUE_OBJECTS")
    if set(core_ids) != set(d0_ids):
        raise ValueError("BATCH10_R3_CORE_D0_IDENTITY_SET_MISMATCH")
    if any(r.get("trade_date") != trade_date for r in core_rows + d0_rows):
        raise ValueError("BATCH10_R3_TARGET_DATE_MISMATCH")
    return hashlib.sha256("\n".join(sorted(core_ids)).encode()).hexdigest()


def validate_rps_evidence(evidence: dict, *, trade_date: str, expected_rows: int = REQUIRED_R3_ROWS) -> dict:
    stats = evidence.get("rps5_delta3") or {}
    expected = dict(core_rows=expected_rows, observed=5202, unknown=24, mismatches=0,
                    independent_exact_matches=5202, independent_current_rps5_mismatches=0)
    if evidence.get("trade_date") != trade_date or any(stats.get(k) != v for k, v in expected.items()):
        raise ValueError("BATCH10_R3_INDEPENDENT_RPS_ORACLE_NOT_ZERO_MISMATCH")
    return stats


def build_period_oracle(root: Path, candidate: dict, candidate_path: Path, label: str) -> dict:
    """Independently verify the newly rebuilt weekly/monthly RAW and QFQ owners."""
    root = root.resolve(); candidate_path = candidate_path.resolve()
    day = candidate["accepted_trade_date"]
    output = candidate_path.parent / f"PERIOD_NUMERIC_ORACLE_{label}.json"
    _ensure_new(output)
    source_copy = candidate_path.parent / f"BATCH10_R3_PERIOD_ORACLE_VERIFIER_{label}.py"
    _ensure_new(source_copy)
    _atomic(source_copy, Path(__file__).read_bytes())

    from workbench_analysis.market_source_acquisition import official_sessions
    core_receipt = json.loads(checked(root, candidate["day_receipt"]).read_bytes())
    core_path = checked(root, core_receipt["numeric_core_oracle"])
    replay = json.loads(core_path.read_bytes())
    owner = next(row for row in replay["owners"] if row.get("trade_date") == day)
    folder = candidate_path.parent
    calendar = official_sessions(root)
    identities = json.loads(checked(root, owner["sources"]["identity"]).read_bytes())["rows"]
    identity = {row["security_id"]: row for row in identities}
    # Reconstruct only status states supported by the same immutable historical
    # status owner and date-bound BaoStock acquisition rows consumed by seal().
    status = defaultdict(dict)
    historical = json.loads((root / "config/v4_sector_operational_authority_v1.json").read_bytes())["sources"]["historical_status"]
    for row in _rows(root, historical):
        if row.get("status") == "SUSPENDED": status[row["trade_date"]][row["security_id"]] = "SUSPENDED"
    acquisition = json.loads((folder / "sources/acquisition.json").read_bytes())
    by_code = {row["source_security_key"].lower(): row["security_id"] for row in identities}
    for query in acquisition.get("queries", []):
        if query.get("method") != "query_daily_history_k_AStock" or not query.get("path"): continue
        day_value = query["params"].get("date", query["params"].get("day"))
        query_path = Path(query["path"])
        if not query_path.is_absolute(): query_path = root / query_path
        for row in json.loads(query_path.read_bytes()).get("rows", []):
            sid = by_code.get(str(row.get("code", "")).lower())
            if sid and row.get("tradestatus") == "0": status[day_value][sid] = "SUSPENDED"
    first_month = min(d for d in calendar if d[:7] == day[:7])
    checks = 0; differences = 0; errors = []; denominator = {}; periods = {}
    for domain in ("period_raw", "period_adjusted"):
        values = _rows(root, candidate["owners"][day][domain])
        grouped = defaultdict(list)
        for row in values: grouped[row["security_id"]].append(row)
        periods[domain] = grouped
        denominator[domain] = dict(securities=len(grouped), rows=len(values))

    def pkey(value, kind):
        if kind == "MONTHLY": return value[:7]
        y, w, _ = date.fromisoformat(value).isocalendar(); return f"{y}-W{w:02d}"

    def compare(actual, expected, scope):
        nonlocal checks, differences
        checks += 1
        equal = Decimal(str(actual)) == expected if actual is not None and isinstance(expected, Decimal) else actual == expected
        if not equal:
            differences += 1
            if len(errors) < 40: errors.append(dict(scope=scope, actual=actual, expected=str(expected) if isinstance(expected, Decimal) else expected))

    seen = set()
    with gzip.open(checked(root, owner["history"]), "rt", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line); sid = item["security_id"]; seen.add(sid)
            start = max(first_month, identity[sid]["list_date"])
            dates = [d for d in calendar if start <= d <= day]
            bars = {b["trade_date"]: b for b in item["bars"] if start <= b["trade_date"] <= day}
            groups = {(kind, pkey(d, kind)) for kind in ("WEEKLY", "MONTHLY") for d in dates}
            for domain, prices_key in (("period_raw", "raw_ohlc"), ("period_adjusted", "qfq_ohlc")):
                actual_rows = periods[domain].get(sid, [])
                compare({(r["period_type"], r["period_key"]) for r in actual_rows}, groups, [sid, domain, "period_denominator"])
                for row in actual_rows:
                    cutoff = row["as_of_date"]; kind = row["period_type"]; key = row["period_key"]
                    required = [d for d in dates if d <= cutoff and pkey(d, kind) == key]
                    actual = [bars[d] for d in required if d in bars]
                    missing = [d for d in required if d not in bars]
                    suspended = sum(status.get(d, {}).get(sid) == "SUSPENDED" for d in missing)
                    unknown = len(missing) - suspended
                    blocked = any(not bar.get(prices_key) for bar in actual)
                    prices = [[Decimal(str(v)) for v in bar[prices_key]] for bar in actual if bar.get(prices_key)]
                    expected_prices = [None] * 4 if blocked or not prices else [prices[0][0], max(v[1] for v in prices), min(v[2] for v in prices), prices[-1][3]]
                    fields = dict(zip(("open", "high", "low", "close"), expected_prices))
                    fields.update(actual_count=len(actual), calendar_count=len(required), unknown_count=unknown,
                        suspended_count=suspended, data_gap_count=0,
                        volume=sum(bar["volume"] for bar in actual), amount=sum(float(bar["amount"]) for bar in actual),
                        price_basis="RAW" if domain == "period_raw" else "QFQ",
                        first_source_date=actual[0]["trade_date"] if actual else None,
                        max_source_date=actual[-1]["trade_date"] if actual else None)
                    fields["period_status"] = ("BLOCKED_BY_ADJUSTMENT" if blocked else "BLOCKED_BY_UNKNOWN_STATUS" if unknown
                        else "NO_ACTUAL_BARS" if not actual else "CLOSED_ONLY_READY" if row["period_view"] == "CLOSED_ONLY" else "AS_OF_PARTIAL_READY")
                    for field, value in fields.items(): compare(row.get(field), value, [sid, domain, key, field])
            if len(seen) % 1000 == 0: print(json.dumps(dict(period_oracle=label, securities=len(seen), checks=checks, differences=differences)), flush=True)
    for domain in periods:
        if set(periods[domain]) != seen: raise ValueError("PERIOD_SECURITY_DENOMINATOR_MISMATCH")
    result = dict(contract_id="V4_DAILY_PERIOD_INDEPENDENT_ORACLE_R1", target_session=day,
        acceptance="PASS" if not differences else "FAIL",
        owners={domain: candidate["owners"][day][domain] for domain in periods}, input_history=owner["history"],
        verifier=ref(root, source_copy), checks=checks, differences=differences, errors=errors,
        denominator=denominator, scope="New dated RAW/QFQ current-week and month outputs; prior immutable PASS evidence retained",
        numerical_producer_recomputed=False, publication=False, source_candidate=ref(root, candidate_path),
        AS_RECORDED=False, PIT_ELIGIBLE=False)
    binding = _write_json(root, output, result)
    if result["acceptance"] != "PASS": raise ValueError("BATCH10_R3_PERIOD_NUMERIC_ORACLE_FAILED")
    candidate["period_numeric_oracle"] = binding
    candidate.setdefault("source_registry", {})[day]["batch10_r3_period_verifier"] = ref(root, source_copy)
    return binding


def build_1020(root: Path, base_path: Path, core_binding: dict, adjusted_binding: dict,
               prewatch_binding: dict, owner_manifest_path: Path, rps_evidence_path: Path,
               d0_evidence_path: Path, label: str) -> tuple[dict, Path]:
    root = root.resolve()
    base_path = (root / base_path).resolve() if not base_path.is_absolute() else base_path.resolve()
    owner_manifest_path = owner_manifest_path.resolve()
    base = json.loads(base_path.read_bytes())
    if base.get("contract_id") != CONTRACT or base.get("accepted_trade_date") != "2026-10-20":
        raise ValueError("BATCH10_R3_BASE_CANDIDATE_MUST_BE_2026_10_20_SUCCESSOR")
    if base.get("AS_RECORDED") is not False or base.get("PIT_ELIGIBLE") is not False:
        raise ValueError("BATCH10_R3_PIT_FLAGS_MUST_REMAIN_FALSE")
    for binding in (core_binding, adjusted_binding, prewatch_binding):
        _load_binding(root, binding)
    owner_manifest = json.loads(owner_manifest_path.read_bytes())
    day = "2026-10-20"
    if owner_manifest.get("trade_date") != day or owner_manifest.get("rows") != REQUIRED_R3_ROWS:
        raise ValueError("BATCH10_R3_OWNER_MANIFEST_DATE_OR_COUNT_MISMATCH")
    if owner_manifest.get("AS_RECORDED") is not False or owner_manifest.get("publication_state") != "STAGING_NOT_ACCEPTED":
        raise ValueError("BATCH10_R3_RECONSTRUCTED_OWNER_FLAGS_MUST_REMAIN_EXPLICIT")
    for name, binding in (("core", core_binding), ("adjusted", adjusted_binding)):
        if owner_manifest.get(name, {}).get("sha256") != binding.get("sha256"):
            raise ValueError("BATCH10_R3_OWNER_MANIFEST_BINDING_MISMATCH:" + name)
    core_rows = _rows(root, core_binding)
    d0_rows = _rows(root, prewatch_binding)
    identity_set_sha256 = validate_exact_identity_sets(core_rows, d0_rows, trade_date=day)
    rps_evidence = json.loads(rps_evidence_path.read_bytes())
    rps_stats = validate_rps_evidence(rps_evidence, trade_date=day)
    d0_evidence = json.loads(d0_evidence_path.read_bytes())
    if d0_evidence.get("trade_date") != day or d0_evidence.get("formal_d0", {}).get("rows") != REQUIRED_R3_ROWS:
        raise ValueError("BATCH10_R3_D0_EVIDENCE_NOT_FULL_5226")
    if d0_evidence.get("formal_d0", {}).get("frozen_scanner_mismatches") != 0:
        raise ValueError("BATCH10_R3_D0_SCANNER_MISMATCH")

    focus_replay_path = root / Path(prewatch_binding["path"]).parent.parent.parent / "FOCUS_FORWARD_REPLAY.json"
    focus_replay = json.loads(focus_replay_path.read_bytes())
    focus_owners = [row for row in focus_replay.get("owners", []) if row.get("trade_date") == day]
    if len(focus_owners) != 1:
        raise ValueError("BATCH10_R3_FOCUS_FORWARD_RECEIPT_DATE_AMBIGUOUS")
    focus_owner = focus_owners[0]
    if focus_owner.get("calculations") != prewatch_binding or focus_owner.get("rows") != REQUIRED_R3_ROWS:
        raise ValueError("BATCH10_R3_FOCUS_FORWARD_D0_BINDING_MISMATCH")
    focus_binding = focus_owner.get("D2")
    forward_binding = focus_replay.get("focus")
    if not isinstance(focus_binding, dict) or not isinstance(forward_binding, dict):
        raise ValueError("BATCH10_R3_FOCUS_OUTPUT_BINDINGS_REQUIRED")
    d2_path, d2_raw = _load_binding(root, focus_binding)
    with gzip.open(d2_path, "rt", encoding="utf-8") as stream:
        d2_payload = json.load(stream)
    if len(d2_payload.get("rows", [])) != REQUIRED_R3_ROWS or any(r.get("trade_date") != day for r in d2_payload["rows"]):
        raise ValueError("BATCH10_R3_D2_OUTPUT_NOT_EXACT_5226_DATE_ROWS")
    _load_binding(root, forward_binding)

    token_hint = hashlib.sha256((base_path.read_bytes() + core_binding["sha256"].encode() + prewatch_binding["sha256"].encode()).strip()).hexdigest()[:16]
    folder = root / "data/v4/batch10_r3_rebases/2026-10-20" / f"{label}_{token_hint}"
    _ensure_new(folder)
    candidate = dict(base)
    owners = dict(base["owners"])
    target = dict(owners[day])
    target.update(raw=owner_manifest["raw"], adjusted=adjusted_binding, core=core_binding,
                  prewatch=prewatch_binding, focus=focus_binding, forward=forward_binding)
    owners[day] = target
    candidate["owners"] = owners

    receipt = json.loads(checked(root, base["day_receipt"]).read_bytes())
    receipt["owners"] = target
    old_core_oracle = json.loads(checked(root, receipt["numeric_core_oracle"]).read_bytes())
    old_targets = [row for row in old_core_oracle.get("owners", []) if row.get("trade_date") == day]
    if len(old_targets) != 1:
        raise ValueError("BATCH10_R3_BASE_NUMERIC_OWNER_RECEIPT_AMBIGUOUS")
    old_targets[0].update(raw=target["raw"], adjusted=target["adjusted"], core=target["core"],
                          actual_raw_rows=owner_manifest.get("actual_raw_rows"))
    old_core_oracle["independent_r3_correction"] = dict(
        contract_id="BATCH10_R3_INDEPENDENT_CORE_D0_CORRECTION_EVIDENCE_R1",
        classification="RECONSTRUCTED_NON_PIT_CANDIDATE_ONLY", trade_date=day,
        core=core_binding, prewatch=prewatch_binding,
        rps_evidence=ref(root, rps_evidence_path), d0_evidence=ref(root, d0_evidence_path),
        core_rows=len(core_rows), d0_rows=len(d0_rows), identity_set_sha256=identity_set_sha256,
        rps5_delta3_exact=rps_stats["observed"],
        rps5_delta3_unknown=rps_stats["unknown"],
        rps5_delta3_mismatches=rps_stats["mismatches"],
        d0_status_counts=d0_evidence["formal_d0"]["status_counts"],
        frozen_scanner_mismatches=d0_evidence["formal_d0"]["frozen_scanner_mismatches"],
        AS_RECORDED=False, PIT_ELIGIBLE=False, production_admission=False)
    oracle_path = folder / "NUMERIC_CORE_ORACLE.json"
    receipt["numeric_core_oracle"] = _write_json(root, oracle_path, old_core_oracle)
    receipt_path = folder / "DAY_RECEIPT.json"
    candidate["day_receipt"] = _write_json(root, receipt_path, receipt)
    registry = json.loads(checked(root, base["registry"]).read_bytes())
    registry["owner_bindings"] = owners
    registry_path = folder / "BUILDER_REGISTRY.json"
    candidate["registry"] = _write_json(root, registry_path, registry)
    # Bind the exact revised generation as source provenance without asserting PIT.
    candidate.setdefault("source_registry", {})[day] = dict(candidate["source_registry"][day],
        batch10_r3_owner_manifest=ref(root, owner_manifest_path),
        batch10_r3_d0_evidence=ref(root, d0_evidence_path),
        batch10_r3_rps_evidence=ref(root, rps_evidence_path),
        batch10_r3_focus_replay=ref(root, focus_replay_path),
        batch10_r3_d2=focus_binding,
        batch10_r3_forward=forward_binding)
    candidate_path = folder / "SUCCESSOR_CANDIDATE.json"
    _write_json(root, candidate_path, candidate)
    validate(root, candidate)
    return candidate, candidate_path


def replay_1021(root: Path, predecessor: dict, predecessor_path: Path,
                base_1021_path: Path, label: str) -> tuple[dict, Path]:
    """Regenerate 10/21 through the normal exact daily Owner pipeline.

    Reusing a 10/21 owner from another 10/20 lineage is deliberately rejected;
    this path changes only the isolated candidate Head and uses the frozen 10/21
    source/readiness with its dependency references rebound to the new 10/20.
    """
    root = root.resolve()
    base_1021_path = (root / base_1021_path).resolve() if not base_1021_path.is_absolute() else base_1021_path.resolve()
    old = json.loads(base_1021_path.read_bytes())
    if old.get("contract_id") != CONTRACT or old.get("accepted_trade_date") != "2026-10-21":
        raise ValueError("BATCH10_R3_1021_BASE_CANDIDATE_REQUIRED")
    if predecessor.get("accepted_trade_date") != "2026-10-20":
        raise ValueError("BATCH10_R3_1021_PREDECESSOR_DATE_REQUIRED")
    receipt = json.loads(checked(root, old["day_receipt"]).read_bytes())
    freeze_binding = receipt.get("source_freeze")
    readiness_binding = receipt.get("source_readiness")
    if not isinstance(freeze_binding, dict) or not isinstance(readiness_binding, dict):
        raise ValueError("BATCH10_R3_1021_FROZEN_SOURCE_READINESS_REQUIRED")
    freeze = json.loads(checked(root, freeze_binding).read_bytes())
    if freeze.get("target_session") != "2026-10-21":
        raise ValueError("BATCH10_R3_1021_FREEZE_DATE_MISMATCH")
    readiness = json.loads(checked(root, readiness_binding).read_bytes())
    if not readiness.get("source_ready") or readiness.get("source_freeze") != freeze_binding:
        raise ValueError("BATCH10_R3_1021_SOURCE_READINESS_NOT_READY")
    lifecycle = json.loads(checked(root, predecessor["owners"]["2026-10-20"]["lifecycle"]).read_bytes())
    deps = readiness.get("dependency_bindings") or {}
    deps["parent_head"] = ref(root, predecessor_path)
    deps["lifecycle"] = predecessor["owners"]["2026-10-20"]["lifecycle"]
    deps["identity"] = lifecycle["identity"]
    deps["membership_snapshot"] = predecessor["membership_snapshot"]
    readiness["dependency_bindings"] = deps
    ready_path = root / "data/v4/batch10_r3_rebases/2026-10-21" / f"{label}_SOURCE_READINESS.json"
    _ensure_new(ready_path)
    ready_binding = _write_json(root, ready_path, readiness)
    head_path = root / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json"
    previous_head = head_path.read_bytes()
    old_head = json.loads(previous_head)
    if old_head.get("contract_id") != CONTRACT or old_head.get("accepted_trade_date") not in ("2026-10-20", "2026-10-21"):
        raise ValueError("BATCH10_R3_CANDIDATE_HEAD_UNEXPECTED_BEFORE_REPLAY")
    archive = root / "data/v4/batch10_r3_rebases/2026-10-21" / f"{label}_PRE_REPLAY_HEAD.json"
    _ensure_new(archive); _atomic(archive, previous_head)
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    atomic_json(root, head_path, predecessor)
    try:
        from workbench_analysis.operational_daily_ready_owner_v2 import build, seal
        _, context = build(root, freeze_binding, source_readiness=ready_binding,
            candidate_only_exact=True, exact_policy_binding=predecessor["release_policy"])
        candidate, candidate_binding = seal(root, context)
        candidate_path = root / candidate_binding["path"]
        build_period_oracle(root, candidate, candidate_path, label)
        atomic_json(root, candidate_path, candidate)
        validate(root, candidate)
        if candidate["predecessor"] != ref(root, predecessor_path):
            raise ValueError("BATCH10_R3_1021_SUCCESSOR_PREDECESSOR_MISMATCH")
        return candidate, candidate_path
    except Exception:
        # Keep the candidate-only pointer at the last validated 10/20 parent;
        # the preserved old Head bytes are available in the immutable archive.
        atomic_json(root, head_path, predecessor)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--base-1020", required=True, type=Path)
    parser.add_argument("--base-1021", required=True, type=Path)
    parser.add_argument("--owner-manifest", required=True, type=Path)
    parser.add_argument("--core-binding-json", required=True, type=Path)
    parser.add_argument("--adjusted-binding-json", required=True, type=Path)
    parser.add_argument("--d0-binding-json", required=True, type=Path)
    parser.add_argument("--existing-1020-candidate", type=Path,
                        help="resume from an already built 10/20 candidate path under --input-root")
    parser.add_argument("--period-only-candidate", type=Path,
                        help="attach a new independent period oracle to an already built 10/21 candidate")
    parser.add_argument("--rps-evidence", type=Path, default=Path("docs/evidence/functional_r8_implementation_20261021/NINTH_BATCH_RPS5_ENDPOINT_REPAIR_R2_EVIDENCE.json"))
    parser.add_argument("--d0-evidence", type=Path, default=Path("docs/evidence/functional_r8_implementation_20261021/NINTH_BATCH_D0_FOCUS_EXACT_IDENTITY_R3_EVIDENCE.json"))
    parser.add_argument("--label", required=True)
    parser.add_argument("--prepare-pg-owner-authority", action="store_true")
    args = parser.parse_args()
    root = args.input_root.resolve(strict=True)
    from scripts.run_batch10_r2_d0_release import _load_local_dsn
    _load_local_dsn(root)
    if args.period_only_candidate:
        candidate_path = root / args.period_only_candidate if not args.period_only_candidate.is_absolute() else args.period_only_candidate
        candidate_path = candidate_path.resolve()
        candidate = json.loads(candidate_path.read_bytes())
        binding = build_period_oracle(root, candidate, candidate_path, args.label)
        from workbench_analysis.operational_daily_storage_v1 import atomic_json
        atomic_json(root, candidate_path, candidate)
        validate(root, candidate)
        print(json.dumps(dict(status="BATCH10_R3_PERIOD_ORACLE_PASS", trade_date=candidate["accepted_trade_date"],
            candidate_token=digest(candidate), period_numeric_oracle=binding, candidate_path=str(candidate_path)), ensure_ascii=False))
        return
    manifest_path = root / args.owner_manifest if not args.owner_manifest.is_absolute() else args.owner_manifest
    rps_path = root / args.rps_evidence if not args.rps_evidence.is_absolute() else args.rps_evidence
    d0_path = root / args.d0_evidence if not args.d0_evidence.is_absolute() else args.d0_evidence
    read_binding = lambda p: json.loads((root / p if not p.is_absolute() else p).read_bytes())
    if args.existing_1020_candidate:
        core_path = root / args.existing_1020_candidate if not args.existing_1020_candidate.is_absolute() else args.existing_1020_candidate
        core_path = core_path.resolve()
        core = json.loads(core_path.read_bytes())
        if core.get("accepted_trade_date") != "2026-10-20":
            raise ValueError("BATCH10_R3_RESUME_CANDIDATE_DATE_MISMATCH")
        validate(root, core)
        for label_key, binding in (("core", read_binding(args.core_binding_json)),
                                   ("adjusted", read_binding(args.adjusted_binding_json)),
                                   ("prewatch", read_binding(args.d0_binding_json))):
            if core["owners"]["2026-10-20"].get(label_key) != binding:
                raise ValueError("BATCH10_R3_RESUME_CANDIDATE_OWNER_BINDING_MISMATCH:" + label_key)
    else:
        core, core_path = build_1020(root, args.base_1020, read_binding(args.core_binding_json),
            read_binding(args.adjusted_binding_json), read_binding(args.d0_binding_json), manifest_path,
            rps_path, d0_path, args.label)
    if args.prepare_pg_owner_authority and not core.get("native_pg_owner_authority"):
        from workbench_db.v4_operational_owner_authority_v2 import prepare_successor
        prepare_successor(root, core)
        validate(root, core)
        from workbench_analysis.operational_daily_storage_v1 import atomic_json
        atomic_json(root, core_path, core)
    if not args.prepare_pg_owner_authority:
        raise ValueError("BATCH10_R3_PG_OWNER_AUTHORITY_PREPARATION_REQUIRED_FOR_REBASE")
    rebased, rebased_path = replay_1021(root, core, core_path, args.base_1021, args.label)
    print(json.dumps(dict(status="BATCH10_R3_REBASE_READY", token_1020=digest(core), token_1021=digest(rebased),
        candidate_1020=str(core_path), candidate_1021=str(rebased_path), pg_owner_authority_prepared=args.prepare_pg_owner_authority,
        formal_head_modified=False, production_admission=False, PIT_ELIGIBLE=False), ensure_ascii=False))


if __name__ == "__main__":
    main()
