"""Full R3 clean-checkout regression in a fresh disposable database only.

Retains prior required tests/manifests and their sole historical deselection.
Run only after the root task has constructed the clean snapshot checkout.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def forbid_config_env(event, args):
    if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
        path = os.fsdecode(args[0]).replace("\\", "/").lower()
        if path.endswith("config/.env") or path.endswith("/config.env"):
            raise RuntimeError("CONFIG_ENV_READ_FORBIDDEN_IN_R3_CLEAN_CHECKOUT")


# Guard this process as well as pytest subprocesses, before project imports.
sys.addaudithook(forbid_config_env)
import psycopg
from scripts.next_round_execution_r3 import (
    verify_protected, read, exact, bind, write, atomic_bytes, PERMISSIONS,
)
from scripts.next_round_bundle_r2 import verify_protected as verify_old_protected
from scripts.verify_next_round_bundle_clean_r3 import required_families as prior_required_families
from scripts.verify_dm01_data_head_promotion_clean_r1 import DESELECT
from scripts.run_v4_08_r3_isolated_verification import disposable_cluster, apply_migrations
from scripts.scan_no_symbol_specific_runtime_logic import run as scan
from scripts.verify_v4_08_r5_1 import compact_scan
from scripts.verify_a02_a05_a04_scoped_r3 import post_readback, verify_a04_sources
from scripts.verify_a02_a05_formal_amendment_readback_r1 import verify_a02, verify_a05
from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2, validate_historical_incremental_registry
from workbench_analysis.parallel_scoped_acceptance_r1 import (
    read_accepted_history, DISPOSITIONS, record_path, validate_record,
    OWNER_PATH, READER_PATH, validate_accepted_owner_metadata, validate_reader_manifest,
)
from workbench_analysis.parallel_scoped_consolidation_r3 import (
    REGISTRY as CONSOLIDATED_REGISTRY, AUTHORITY as CONSOLIDATED_AUTHORITY,
    SUMMARY as CONSOLIDATED_SUMMARY, validate_consolidation, validate_authority_registry,
    validate_summary,
)

NEW_FAMILIES = [
    "tests/v4_11_r3a", "tests/v4_11_r3b", "tests/v4_11_r3c",
    "tests/v4_scoped_promotions_r3", "tests/v4_parallel_scoped_consolidation_r3",
]
OLD_MANIFEST = "reports/next_round_r2/BATCH_CANDIDATE_ARTIFACT_MANIFEST_R2.json"
MANIFEST = "reports/next_round_r3/BATCH_ARTIFACT_MANIFEST.json"
OUTPUT = "reports/v4_11_r3/"
SEALS = {
    "R3A": "reports/v4_11_r3a/R3A_SEALED_PRODUCER_SET_R2.json",
    "R3B": "reports/v4_11_r3b/R3B_SEALED_PRODUCER_SET.json",
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf8").strip()


def required_families():
    previous = prior_required_families()
    families = list(dict.fromkeys(previous + NEW_FAMILIES))
    missing = [p for p in families if not (ROOT / p).exists()]
    if missing:
        raise ValueError("REQUIRED_REGRESSION_FAMILY_MISSING:" + ",".join(missing))
    if not set(previous).issubset(families):
        raise ValueError("OLD_REQUIRED_REGRESSION_FAMILY_OMITTED")
    return families


def check_manifest(path):
    manifest = read(path)
    refs = manifest["artifacts"]
    if not refs:
        raise ValueError("NONEMPTY_ARTIFACT_MANIFEST_REQUIRED:" + path)
    for ref in refs:
        try:exact(ref)
        except ValueError:
            if path!=OLD_MANIFEST or ref['path']!='.gitattributes':raise
            amendment=read('reports/v4_11_r3/GIT_ATTRIBUTE_APPEND_ONLY_AMENDMENT_R1.json')
            original=exact(amendment['original_bytes_archive']).read_bytes()
            current=exact(amendment['current_binding']).read_bytes()
            if amendment['original_binding']!=ref or hashlib.sha256(original).hexdigest()!=ref['sha256'] or len(original)!=ref['bytes'] or not current.startswith(original):
                raise ValueError('PRIOR_ATTRIBUTE_EXACT_ARCHIVE_AND_APPEND_ONLY_AMENDMENT_REQUIRED')
    return dict(binding=bind(path), artifact_count=len(refs), exact_bytes="PASS_WITH_EXACT_BASELINE_ATTRIBUTE_ARCHIVE_AND_DECLARED_APPEND_ONLY_AMENDMENT" if path==OLD_MANIFEST else 'PASS')


def producer_seal_readback():
    """Reopen sealed contracts/publications and every declared source binding."""
    from src.v4.target_fact_producers_r3 import validate
    from src.v4.state_identity import digest as state_digest
    from src.v4.confirmation import digest as confirmation_digest
    result, checked, metadata_representations = {}, {}, []

    def inspect(value, role=()):
        if isinstance(value, dict):
            if "path" in value and "sha256" in value and ("bytes" in value or "byte_count" in value):
                key = (value["path"], value["sha256"], value.get("bytes", value.get("byte_count")))
                if key not in checked:
                    try:exact(value)
                    except ValueError:
                        if stage!='R3B' or 'source_inventory' not in role:raise
                        from workbench_analysis.parallel_scoped_acceptance_r1 import validate_protected_binding
                        archived=validate_protected_binding(ROOT,value)
                        metadata_representations.append(dict(original_metadata_binding=value,exact_original_archive=bind(archived.relative_to(ROOT).as_posix()),role='R3B_SOURCE_CAPABILITY_INVENTORY_ONLY_NOT_BUSINESS_INPUT'))
                    checked[key] = value
            for name,child in value.items():
                inspect(child,role+(name,))
        elif isinstance(value, list):
            for child in value:
                inspect(child,role)

    for stage, path in SEALS.items():
        seal = read(path)
        inspect(seal)
        if seal.get("permissions") != PERMISSIONS or "CANDIDATE_READY" not in seal.get("status", ""):
            raise ValueError("R3_PRODUCER_SEAL_SCOPE_INVALID:" + stage)
        if stage == "R3A":
            if seal.get("sealed") is not True or seal.get("accepted") is not False:
                raise ValueError("R3A_SEALED_CANDIDATE_ONLY_REQUIRED")
            contract = json.loads(exact(seal["contract"]).read_bytes())
            inspect(contract)
            publications = {}
            for day, ref in seal["publications"].items():
                publication = json.loads(gzip.decompress(exact(ref).read_bytes()))
                validate(publication, ROOT, expected_sources=publication["source_bindings"])
                inspect(publication["source_bindings"])
                if (publication["trade_date"] != day
                        or publication["source_digest"] != confirmation_digest(publication["source_bindings"])):
                    raise ValueError("R3A_SEALED_PUBLICATION_DATE_MISMATCH")
                publications[day] = dict(binding=ref, row_count=len(publication["rows"]),
                    publication_id=publication["publication_id"], source_bindings=publication["source_bindings"],
                    source_digest=publication["source_digest"], accepted=False, AS_RECORDED=False)
            result[stage] = dict(status="PASS_EXACT_SEALED_PRODUCER_PUBLICATIONS", seal=bind(path),
                                contract=seal["contract"], publications=publications)
        else:
            if (seal.get("required_external_acceptance") is not True
                    or seal.get("formal_stage_head_created") is not False
                    or seal.get("data_head_advanced") is not False
                    or seal.get("stage_head_advanced") is not False):
                raise ValueError("R3B_SEALED_CANDIDATE_ONLY_REQUIRED")
            if seal["producer_set_digest"] != state_digest(seal["bindings"]):
                raise ValueError("R3B_SEALED_SOURCE_DIGEST_MISMATCH")
            # The contract and receipt include legacy source and parameter refs
            # beyond the seal's top-level runtime/source bindings.
            for ref in seal["bindings"]:
                if ref["path"].endswith(".json"):
                    inspect(json.loads(exact(ref).read_bytes()))
            result[stage] = dict(status="PASS_EXACT_SEALED_PRODUCER_BINDINGS", seal=bind(path),
                                producer_set_digest=seal["producer_set_digest"], bindings=seal["bindings"])
    result["all_declared_source_bindings"] = list(checked.values())
    result["declared_source_binding_count"] = len(checked)
    result['metadata_original_byte_representation_proofs']=metadata_representations
    return result


def real_dag_readback():
    from src.v4.confirmation_d2_candidate_r3 import verify_candidate_d2_publication
    from src.v4.confirmation_events_candidate_r3 import event_unknown_reasons
    from src.v4.confirmation import digest
    report=read('reports/v4_11_r3/V4_11_R3_D2_READBACK.json')
    current=json.loads(gzip.decompress(exact(report['current']).read_bytes()))
    prior=json.loads(gzip.decompress(exact(report['prior']).read_bytes()))
    rows=verify_candidate_d2_publication(current,producer_set=report['source_set'])
    er=read('reports/v4_11_r3/V4_11_R3_EVENT_REPLAY.json')
    frozen=json.loads(gzip.decompress(exact(er['frozen_prior']).read_bytes()))
    material=dict(frozen);head=material.pop('head_digest')
    if digest(material)!=head or frozen['source_binding']!=prior or frozen['rows']!=prior['rows']:raise ValueError('CLEAN_REAL_EVENT_FROZEN_PRIOR_MISMATCH')
    eventrows=json.loads(gzip.decompress(exact(er['events']).read_bytes()))
    currentrows={r['entity_id']:r for r in rows};old={r['entity_id']:r for r in prior['rows']}
    if len(rows)!=5224 or set(currentrows)!=set(r['entity_id'] for r in eventrows):raise ValueError('CLEAN_REAL_DAG_SCOPE_MISMATCH')
    for event in eventrows:
        reasons=event_unknown_reasons(currentrows[event['entity_id']],old.get(event['entity_id']))
        if event['event_unknown_predicates']!=reasons or event['effective_event']!=('UNKNOWN' if reasons else event['primary_event']):raise ValueError('CLEAN_REAL_EVENT_UNKNOWN_GUARD_MISMATCH')
        if event['prior_session_state_head_digest']!=head:raise ValueError('CLEAN_EVENT_PRIOR_HEAD_BINDING_MISMATCH')
    return dict(status='PASS_CLEAN_REAL_D2_EXACT_REEXECUTION_EVENT_SOURCE_GUARDS',row_count=len(rows),D2_readback=bind('reports/v4_11_r3/V4_11_R3_D2_READBACK.json'),event_replay=bind('reports/v4_11_r3/V4_11_R3_EVENT_REPLAY.json'),active_runtime_contract=report['contract'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--postgres-bin", type=Path, default=Path("E:/Postgres/bin"))
    parser.add_argument("--pytest-timeout", type=int, default=1800)
    args = parser.parse_args()
    started = time.monotonic()
    before = git("status", "--porcelain=v1")
    head = git("rev-parse", "HEAD")
    if before or (ROOT / "config/.env").exists() or (ROOT / "config.env").exists():
        raise ValueError("CLEAN_CHECKOUT_WITHOUT_CONFIG_ENV_REQUIRED")
    if (ROOT / "data/v4/V4_11_ACCEPTED_HEAD.json").exists():
        raise ValueError("FORMAL_V4_11_ACCEPTED_HEAD_NOT_AUTHORIZED")
    entry = verify_protected()
    verify_old_protected()
    protected = {ref["path"]: hashlib.sha256((ROOT / ref["path"]).read_bytes()).hexdigest()
                 for ref in entry["protected_heads"]}
    manifests = dict(prior=check_manifest(OLD_MANIFEST), current=check_manifest(MANIFEST))
    source_readback = validate_head_v2(ROOT, read("data/v4/V4_DATA_ACCEPTED_HEAD.json"), source_readback=True)
    registry = validate_historical_incremental_registry(ROOT)
    scoped_records = {key: validate_record(ROOT, read(record_path(key)), key) for key in DISPOSITIONS}
    scoped_owner = validate_accepted_owner_metadata(ROOT, read(OWNER_PATH))
    scoped_reader = validate_reader_manifest(ROOT, read(READER_PATH))
    consolidated = dict(
        registry=validate_consolidation(ROOT, read(CONSOLIDATED_REGISTRY)),
        authority=validate_authority_registry(ROOT, read(CONSOLIDATED_AUTHORITY)),
        summary=validate_summary(ROOT, read(CONSOLIDATED_SUMMARY)),
    )
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(read_accepted_history, ROOT, "V4-09"),
                   pool.submit(read_accepted_history, ROOT, "V4-10"),
                   pool.submit(__import__("scripts.validate_v4_10_promotion_r1", fromlist=["validate"]).validate)]
        historical_v9, historical_v10, current_v10 = [f.result() for f in futures]
    if (historical_v9["status"] != "PASS" or historical_v10["status"] != "PASS"
            or current_v10["checks"]["P19_protected"] != "FAIL"):
        raise ValueError("HISTORY_OR_CURRENT_AUTHORITY_BOUNDARY_CHANGED")
    # Reuse the original independent oracle directly so the main-process
    # config/.env audit hook also covers every legacy source read.
    a02a05 = dict(status="PASS", A02=verify_a02(), A05=verify_a05())
    if any(a02a05[key].get("status") != "PASS" for key in ("A02", "A05")):
        raise ValueError("A02_A05_FORMAL_AMENDMENT_SOURCE_READBACK_FAILED")
    scoped_promotions = post_readback()
    a04_source_readback = verify_a04_sources()
    producer_seals = producer_seal_readback()
    dag_readback = real_dag_readback()
    families = required_families()
    with disposable_cluster(args.postgres_bin) as (dsn, temp):
        with psycopg.connect(dsn) as pg:
            migrations = apply_migrations(pg)
            identity = pg.execute("SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port()").fetchone()
        if [int(Path(item["path"]).name[:3]) for item in migrations] != list(range(1, 28)):
            raise ValueError("UNIFIED_MIGRATION_001_TO_027_REQUIRED")
        guard = temp / "guard"
        guard.mkdir()
        (guard / "sitecustomize.py").write_text(
            "import sys,os\ndef forbid(event,args):\n"
            " if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):\n"
            "  path=os.fsdecode(args[0]).replace('\\\\','/').lower()\n"
            "  if path.endswith('config/.env') or path.endswith('/config.env'):raise RuntimeError('CONFIG_ENV_READ_FORBIDDEN_IN_R3_REGRESSION')\n"
            "sys.addaudithook(forbid)\n", encoding="utf8")
        env = os.environ.copy()
        for key in ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGDATABASE", "PGHOST", "PGPORT", "PGUSER"):
            env.pop(key, None)
        # Explicit DSNs refer only to this newly initialized isolated cluster.
        env.update(WORKBENCH_PG_DSN=dsn, V4_10_DISPOSABLE_TEST_DSN=dsn,
                   PYTHONPATH=str(guard) + os.pathsep + str(ROOT) + os.pathsep + str(ROOT / "src"),
                   PYTHONIOENCODING="utf-8")
        junit = temp / "tests.xml"
        command = [sys.executable, "-m", "pytest", "-q", *families,
                   "--deselect=" + DESELECT, "--junitxml=" + str(junit)]
        proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                              encoding="utf8", errors="replace", timeout=args.pytest_timeout)
        suites = list(ET.parse(junit).getroot().iter("testsuite")) if junit.exists() else []
        summary = {key: sum(int(s.get(key, "0")) for s in suites)
                   for key in ("tests", "failures", "errors", "skipped")}
        summary["passed"] = summary["tests"] - summary["failures"] - summary["errors"] - summary["skipped"]
        xml = junit.read_bytes() if junit.exists() else b""
    no_symbol = scan(ROOT)
    after = git("status", "--porcelain=v1")
    verify_protected()
    verify_old_protected()
    unchanged = all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == checksum
                    for path, checksum in protected.items())
    ok = (bool(suites) and proc.returncode == 0 and unchanged and not after
          and no_symbol["status"] == "PASS" and registry["status"].startswith("PASS")
          and scoped_promotions["status"] == a04_source_readback["status"] == "PASS")
    attempt = 1
    while (ROOT / (OUTPUT + f"V4_11_R3_CLEAN_ATTEMPT_R{attempt}.json")).exists():
        attempt += 1
    prefix = OUTPUT + f"V4_11_R3_CLEAN_ATTEMPT_R{attempt}"
    atomic_bytes(prefix + ".xml", xml)
    atomic_bytes(prefix + ".log", (proc.stdout + "\n" + proc.stderr).encode("utf8"))
    receipt = dict(
        contract_id="V4_11_R3_CLEAN_CHECKOUT_FULL_REGRESSION_V1",
        status="PASS_ENGINEERING_REGRESSION" if ok else "FAIL", tested_commit=head,
        summary=summary, required_families=families, retained_previous_required_families=prior_required_families(),
        pytest_return_code=proc.returncode, authorized_deselects=[DESELECT], new_deselects=[],
        junit=bind(prefix + ".xml"), log=bind(prefix + ".log"), no_symbol=compact_scan(no_symbol),
        git_status_before=before, git_status_after=after, protected_heads_before=protected,
        protected_head_bindings=entry["protected_heads"], protected_heads_unchanged=unchanged,
        stage_head_action="KEEP_V4_00_TO_V4_10_ACCEPTED", data_head_action="KEEP_2026-09-30",
        source_readback=source_readback, incremental_registry=registry,
        A02_A05_independent_source_readback=a02a05, A04_independent_source_readback=a04_source_readback,
        new_scoped_promotions_independent_readback=scoped_promotions, R3_sealed_producer_source_readback=producer_seals,
        real_DAG_clean_reexecution=dag_readback,
        scoped_consolidation_independent_readback=consolidated, scoped_external_acceptance_records=scoped_records,
        inactive_accepted_owner_metadata=scoped_owner, accepted_history_only_reader=scoped_reader,
        historical_publications=dict(V4_09=historical_v9, V4_10=historical_v10),
        current_v4_10_protected_gate=current_v10["checks"]["P19_protected"], artifact_manifests=manifests,
        migrations=migrations, database_identity=dict(zip(("database", "owner", "address", "port"), identity)),
        database_scope="FRESH_DISPOSABLE_ISOLATED_CLUSTER_ONLY", temporary_cluster_cleaned_up=True,
        config_dot_env_read=False, config_dot_env_present=False, config_env_audit_hook_enabled=True,
        configured_or_production_database_used=False, password_persisted=False, permissions=PERMISSIONS,
        authority=entry["authority"], master=entry["master"], external_acceptance=False,
        formal_v4_11_accepted_head_created=False, V4_12_runtime_authorized=False,
        next_stage="STOP_WAIT_FOR_INDEPENDENT_EXTERNAL_ACCEPTANCE",
        completed_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic() - started, 3),
    )
    write(prefix + ".json", receipt)
    write(OUTPUT + "V4_11_R3_CLEAN_CHECKOUT.json", receipt)
    print(json.dumps(dict(status=receipt["status"], tested_commit=head, summary=summary,
                          no_symbol=no_symbol["status"], elapsed_seconds=receipt["elapsed_seconds"])))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
