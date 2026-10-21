"""Append-only D0 candidate Owner/Publication closure for R8 Batch 07."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
import gzip
import hashlib
import json
from pathlib import Path
import re

CONTRACT_ID = 'V4_D0_SOURCE_SEAL_SUCCESSOR_R2'
CONTRACT_VERSION = '2.0.0'
FORMAL_SCENARIOS = ('LAUNCH_CONFIRM', 'RECOVERY_TURN')
CHECK_INPUTS = {
    'LAUNCH_CONFIRM': {'ACTUAL_BAR':'actual_bar','AMR20_GTE_120':'amr20_mean_prior','BREAKOUT_V3':'breakout_v3','CLOSE_ABOVE_PHC20':'close_above_prior_high','CLV_GTE_060':'clv','INPUT_IDENTITY_COMPATIBLE':'input_identity_compatible','LIQ20':'liq20','NORMAL_UNIVERSE':'normal_universe','NOT_EXTENDED':'extended_v3','NOT_FIRST_DAY_DAMAGE':'first_day_damage','NOT_SEVERE_DROP':'severe_drop','NOT_STRUCTURE_BREAK':'structure_break_v3','NO_INTRADAY_REJECT_HIGH20':'intraday_reject_high20','POSITIVE_RET1':'ret1_adj','WINDOW_VALID':'window_valid'},
    'RECOVERY_TURN': {'ACTUAL_BAR':'actual_bar','AMR20_GTE_105':'amr20_mean_prior','CLOSE_GTE_098_MA20':'close_to_ma20','CLV_GTE_055':'clv','INPUT_IDENTITY_COMPATIBLE':'input_identity_compatible','LIQ20':'liq20','NORMAL_UNIVERSE':'normal_universe','NOT_EXTENDED':'extended_v3','NOT_FIRST_DAY_DAMAGE':'first_day_damage','NOT_SEVERE_DROP':'severe_drop','NOT_STRUCTURE_BREAK':'structure_break_v3','POSITIVE_RET1':'ret1_adj','R5_OR_R20':'rps5_or_rps20','RPS5_DELTA3_POSITIVE':'rps5_delta3','WINDOW_VALID':'window_valid'},
}
SCHEMA = 'v4_r8d0seal_batch07_r1'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_ref(root, binding, role, owner_contract, version_token, *, time_role, evidence_class, available_at=None, ingress_sha=None):
    path = Path(root) / binding['path']
    raw = path.read_bytes()
    digest = sha(raw)
    if digest != binding['sha256'] or len(raw) != binding['bytes']:
        raise ValueError('D0_OWNER_BYTES_MISMATCH:' + role)
    return dict(source_role=role, source_path=str(path), source_sha256=digest, source_bytes=len(raw),
        owner_contract_id=owner_contract, owner_version_token=version_token, time_role=time_role,
        evidence_class=evidence_class, available_at=available_at, source_ingress_artifact_sha256=ingress_sha)


def owner_version_from_binding(binding, trade_date):
    """Extract the immutable 64-hex owner run token from its bound path."""
    parts=Path(binding['path']).parts
    try: start=parts.index(trade_date)+1
    except ValueError: start=0
    for part in parts[start:]:
        if re.fullmatch(r'[0-9a-f]{64}',part):
            return part
    raise ValueError('D0_OWNER_VERSION_TOKEN_NOT_BOUND:'+binding.get('path',''))


def derive_cutoff(snapshot_published_at):
    """Use the actual R8 PG snapshot publication clock, never a guessed close time."""
    value = snapshot_published_at
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('D0_CUTOFF_REQUIRES_TIMEZONE')
    return value


def classify_source(source, cutoff):
    available = source.get('available_at')
    instant=None
    if available:
        try: instant=datetime.fromisoformat(str(available).replace('Z', '+00:00'))
        except (TypeError,ValueError): return 'UNKNOWN'
        if instant.tzinfo is None:return 'UNKNOWN'
        if instant > cutoff:return 'RECONSTRUCTED_AFTER_CUTOFF'
    if source.get('evidence_class') in ('RECONSTRUCTED_NON_PIT', 'CAPTURED_AFTER_CLOSE_NON_PIT') or 'RECONSTRUCTED' in source.get('time_role', '').upper() or 'LATE' in source.get('time_role', '').upper():
        return 'RECONSTRUCTED_NON_PIT'
    if not source.get('time_role') or instant is None:return 'UNKNOWN'
    return 'AVAILABLE_BY_CUTOFF'


def same_cutoff_source_eligible(candidate, *, evidence_class, time_role, available_at, cutoff, membership_observed_at):
    """Gate a dev PIT-capable seal on candidate facts and all actual source clocks."""
    try:
        available=datetime.fromisoformat(str(available_at).replace('Z','+00:00'))
        membership=datetime.fromisoformat(str(membership_observed_at).replace('Z','+00:00'))
    except (TypeError,ValueError):
        return False
    return bool(candidate.get('AS_RECORDED') is True and candidate.get('PIT_ELIGIBLE') is True and
        evidence_class not in ('RECONSTRUCTED_NON_PIT','CAPTURED_AFTER_CLOSE_NON_PIT') and
        'RECONSTRUCTED' not in str(time_role).upper() and 'LATE' not in str(time_role).upper() and
        available.tzinfo is not None and membership.tzinfo is not None and available<=cutoff and membership<=cutoff)


def load_owner(path):
    rows = []
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def independent_scanner_comparison(owner_path):
    """Run the frozen scanner over saved values and compare exact formal D0 outputs."""
    from .corrected_focus_replay import confirmation
    rows=load_owner(owner_path)
    state_counts=Counter((r.get('confirmation') or {}).get('confirmation_status','UNKNOWN') for r in rows)
    scenario_counts={s:Counter() for s in FORMAL_SCENARIOS}
    compared=0
    mismatch_count=0
    mismatches=[]
    for row in rows:
        target=row.get('target_values') or {}
        recomputed=confirmation(target)
        original=row.get('confirmation') or {}
        for scenario in FORMAL_SCENARIOS:
            actual=next((x for x in original.get('scenario_evidence',[]) if x.get('scenario')==scenario),None)
            expected=next((x for x in recomputed.get('scenario_evidence',[]) if x.get('scenario')==scenario),None)
            if actual is None or expected is None:
                mismatch_count+=1
                if len(mismatches)<25:mismatches.append(dict(security_id=row.get('security_id'),scenario=scenario,reason='SCENARIO_MISSING'))
            else:
                scenario_counts[scenario][actual.get('status','UNKNOWN')]+=1
                if actual.get('status')!=expected.get('status') or actual.get('checks')!=expected.get('checks'):
                    mismatch_count+=1
                    if len(mismatches)<25:mismatches.append(dict(security_id=row.get('security_id'),scenario=scenario,reason='FROZEN_SCANNER_OUTPUT_MISMATCH'))
                compared+=1
    return dict(owner_rows=len(rows),scenario_rows=compared,predicate_counts=dict(state_counts),
        scenario_status_counts={k:dict(v) for k,v in scenario_counts.items()},
        comparison='PASS' if compared==len(rows)*len(FORMAL_SCENARIOS) and mismatch_count==0 else 'MISMATCH',
        mismatch_count=mismatch_count,mismatches=mismatches)


def field_lineage(check, scenario, owner_refs, row):
    if check == 'NORMAL_UNIVERSE': source_role='UNIVERSE_SESSION_MEMBERSHIP'
    elif check == 'INPUT_IDENTITY_COMPATIBLE': source_role='MEMBERSHIP_AUTHORITY_REFERENCE'
    else: source_role = 'CORE_AND_RELATIVE_STRENGTH_FACTS' if check in ('AMR20_GTE_120','AMR20_GTE_105','R5_OR_R20','RPS5_DELTA3_POSITIVE','LIQ20') else 'RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW'
    ref = owner_refs[source_role]
    input_name = CHECK_INPUTS[scenario][check]
    vals = row.get('target_values') or {}
    return dict(check=check, input_field=input_name, input_value=vals.get(input_name),
        source_role=source_role, owner_sha256=ref['source_sha256'], owner_version_token=ref['owner_version_token'],
        window_role='TARGET_SESSION_AND_REQUIRED_PRIOR_MASTER_SESSIONS',
        price_coordinate='TDX_NATIVE_AFFINE_QFQ' if source_role == 'RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW' else None)


def publish_candidate(*, repository_root, candidate_root, candidate, trade_date, candidate_token):
    """Publish a D0 candidate, granting PIT only when all frozen clocks support it."""
    import psycopg
    from psycopg.types.json import Jsonb
    from workbench_db.v4_native import configured_dsn

    day = date.fromisoformat(trade_date)
    owners = candidate.get('owners', {}).get(trade_date, {})
    required = ('raw', 'adjusted', 'core', 'prewatch')
    if not all(owners.get(key) for key in required):
        raise ValueError('D0_REQUIRED_OWNER_BINDING_MISSING')
    owner_rows = load_owner(Path(candidate_root) / owners['prewatch']['path'])
    if not owner_rows:
        raise ValueError('D0_OWNER_EMPTY')
    predicate_counts = Counter((r.get('confirmation') or {}).get('confirmation_status', 'UNKNOWN') for r in owner_rows)
    if set(predicate_counts) - {'TRUE','FALSE','UNKNOWN'}:
        raise ValueError('D0_THREE_STATE_CONTRACT_MISMATCH')
    producer = Path(repository_root)
    config_path = producer / 'config/research_attention_v3.yaml'
    param_sha = sha(config_path.read_bytes())
    with psycopg.connect(configured_dsn(), connect_timeout=5) as pg:
        pg.execute("SET LOCAL statement_timeout='60s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        pg.execute("SET LOCAL search_path TO pg_catalog")
        pg.execute('SET TRANSACTION READ WRITE')
        snapshot = pg.execute("SELECT candidate_token,trade_date::text,owner_authority_sha256,source_freeze_sha256,inserted_at FROM v4_r8pub_fde08c597fc76d13.r8_publications WHERE candidate_token=%s AND trade_date=%s", (candidate_token, day)).fetchone()
        if not snapshot:
            raise ValueError('D0_R8_SNAPSHOT_PUBLICATION_NOT_FOUND')
        cutoff = derive_cutoff(snapshot[4])
        receipt = pg.execute("SELECT source_contract,source_sha256,available_at,time_role,evidence_class,artifact_path,artifact_sha256,artifact_bytes,recorded_at FROM v4_r8_batch04_source_ingress.source_receipts WHERE trade_date=%s ORDER BY recorded_at DESC LIMIT 1", (day,)).fetchone()
        if not receipt:
            raise ValueError('D0_SOURCE_INGRESS_RECEIPT_NOT_FOUND')
        source_contract, source_sha, available, time_role, evidence_class, artifact_path, artifact_sha, artifact_bytes, recorded = receipt
        ingress_path = Path(artifact_path)
        ingress_raw = ingress_path.read_bytes()
        if sha(ingress_raw) != artifact_sha or len(ingress_raw) != artifact_bytes:
            raise ValueError('D0_SOURCE_INGRESS_BYTES_MISMATCH')
        owner_refs = {}
        membership_clock_raw=candidate.get('membership_observed_at') or candidate.get('snapshot_membership_asof')
        try:
            membership_clock=datetime.fromisoformat(str(membership_clock_raw).replace('Z','+00:00'))
            if membership_clock.tzinfo is None: membership_clock=None
        except (TypeError,ValueError): membership_clock=None
        source_truthful=same_cutoff_source_eligible(candidate,evidence_class=evidence_class,time_role=time_role,
            available_at=available,cutoff=cutoff,membership_observed_at=membership_clock_raw)
        source_evidence_class=evidence_class if source_truthful else 'RECONSTRUCTED_NON_PIT'
        source_time_role=time_role if source_truthful else 'RECONSTRUCTED_OWNER_REPLAY'
        d0_class='AVAILABLE_BY_CUTOFF' if source_truthful else ('RECONSTRUCTED_AFTER_CUTOFF' if available and available>cutoff else 'RECONSTRUCTED_NON_PIT')
        for key, role in (('raw','RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW'),('adjusted','TDX_NATIVE_ADJUSTED_DAILY_WINDOW'),('core','CORE_AND_RELATIVE_STRENGTH_FACTS'),('prewatch','D0_PREDICATE_OWNER_OUTPUT')):
            owner_refs[role] = file_ref(candidate_root, owners[key], role, candidate.get('contract_id','V4_D0_FORMAL_AGGREGATION_REPAIR_R1'), owner_version_from_binding(owners[key],trade_date),
                time_role='OWNER_BYTES_BOUND_TO_R8_SNAPSHOT' if source_truthful else 'RECONSTRUCTED_OWNER_REPLAY',
                evidence_class=source_evidence_class, available_at=cutoff if source_truthful else available, ingress_sha=artifact_sha)
        for rel, role in [
            ('config/v4_11_confirmation_detector_contract_r2.json','FROZEN_D0_SCANNER_AND_THRESHOLDS'),
            ('src/v4/target_fact_producers_r4.py','TARGET_FACT_PRODUCER'),
            ('src/workbench_analysis/corrected_focus_replay.py','SCENARIO_DETECTOR'),
            ('config/v4_d0_source_seal_successor_v1.json','D0_SOURCE_SEAL_CONTRACT'),
            ('config/research_attention_v3.yaml','D0_PRODUCER_PARAMETERS'),
            ('src/workbench_analysis/d0_source_seal_r2.py','D0_PG_OWNER_PUBLICATION_PRODUCER'),
            ('src/workbench_analysis/d0_source_seal_r1.py','D0_PG_READBACK_VERIFIER'),
            ('src/workbench_analysis/r6_reason_attribution.py','D0_BFF_SOURCE_VERIFICATION'),
            ('src/workbench_db/migrations/v4_postgres/027_d0_source_seal_batch07_r1.sql','D0_PG_SCHEMA_MIGRATION'),
            ('scripts/run_v4_d0_batch07_seal.py','D0_PG_SEAL_RUNNER'),
            ('scripts/verify_v4_d0_batch07_seal.py','D0_INDEPENDENT_VERIFIER_SCRIPT')]:
            contract_file=producer/rel
            contract_raw=contract_file.read_bytes()
            owner_refs[role]=dict(source_role=role,source_path=str(contract_file),source_sha256=sha(contract_raw),source_bytes=len(contract_raw),
                owner_contract_id=CONTRACT_ID,owner_version_token=CONTRACT_VERSION,time_role='VERSIONED_CODE_CONTRACT_AT_SNAPSHOT_FREEZE',
                evidence_class='VERSIONED_CONTRACT',available_at=cutoff,source_ingress_artifact_sha256=None)
        for key, role in (('membership_snapshot','UNIVERSE_SESSION_MEMBERSHIP'),('native_membership_reference','MEMBERSHIP_AUTHORITY_REFERENCE')):
            binding=candidate.get(key)
            if binding:
                owner_refs[role]=file_ref(candidate_root,binding,role,'V4_D0_UNIVERSE_MEMBERSHIP_SNAPSHOT_R1',owner_version_from_binding(binding,trade_date),
                    time_role='MEMBERSHIP_SNAPSHOT_AS_OF' if source_truthful else 'RECONSTRUCTED_MEMBERSHIP_BINDING',
                    evidence_class=source_evidence_class,available_at=membership_clock if source_truthful else None,ingress_sha=artifact_sha)
        receipt_ref = dict(source_role='TDX_SOURCE_INGRESS_ARTIFACT',source_path=artifact_path,source_sha256=artifact_sha,source_bytes=artifact_bytes,
            owner_contract_id=source_contract,owner_version_token=source_sha,time_role=time_role,evidence_class=evidence_class,
            available_at=available,source_ingress_artifact_sha256=artifact_sha)
        source_refs = list(owner_refs.values()) + [receipt_ref]
        previous_revision=pg.execute(f"SELECT max(revision_no) FROM {SCHEMA}.publications WHERE trade_date=%s AND candidate_token=%s",(day,candidate_token)).fetchone()[0]
        revision_no=(previous_revision or 0)+1
        publication_id='D0B07:'+trade_date+':'+candidate_token+':r'+str(revision_no)
        pred_rows=[]
        fact_rows=[]
        for row in owner_rows:
            security_id=str(row.get('security_id') or row.get('entity_id') or '')
            if not security_id: raise ValueError('D0_SECURITY_ID_MISSING')
            confirmation=row.get('confirmation') or {}
            state=confirmation.get('confirmation_status','UNKNOWN')
            pred_rows.append([security_id,state])
            for scenario in FORMAL_SCENARIOS:
                scenario_row=next((x for x in confirmation.get('scenario_evidence',[]) if x.get('scenario')==scenario),None)
                if scenario_row is None: raise ValueError('D0_FORMAL_SCENARIO_MISSING:'+scenario)
                checks=scenario_row.get('checks') or {}
                lineage={check:field_lineage(check,scenario,owner_refs,row) for check in CHECK_INPUTS[scenario]}
                payload=dict(publication_id=publication_id,scenario=scenario,security_id=security_id,
                    predicate_state=scenario_row.get('status','UNKNOWN'),check_values=checks,field_lineage=lineage)
                fact_rows.append((scenario,security_id,payload['predicate_state'],checks,lineage,sha(canonical(payload))))
        if len({x[0] for x in pred_rows}) != len(pred_rows): raise ValueError('D0_DUPLICATE_SECURITY_ID')
        predicate_digest=sha(canonical(sorted(pred_rows)))
        owner_binding=owners['prewatch']; owner_path=Path(candidate_root)/owner_binding['path']; owner_raw=owner_path.read_bytes()
        if sha(owner_raw)!=owner_binding['sha256'] or len(owner_raw)!=owner_binding['bytes']:
            raise ValueError('D0_PREDICATE_OWNER_BYTES_MISMATCH')
        window=dict(target_session=trade_date,range_role='TARGET_SESSION_AND_REQUIRED_PRIOR_MASTER_SESSIONS',
            published_sessions=[s for s in candidate.get('published_sessions',[]) if s<=trade_date],
            raw_owner_sha256=owner_refs['RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW']['source_sha256'],
            price_coordinate='TDX_NATIVE_AFFINE_QFQ')
        existing=pg.execute(f"SELECT publication_id,owner_sha256,predicate_digest,row_count FROM {SCHEMA}.publications WHERE trade_date=%s AND candidate_token=%s AND owner_sha256=%s AND predicate_digest=%s AND row_count=%s ORDER BY revision_no DESC LIMIT 1",(day,candidate_token,owner_binding['sha256'],predicate_digest,len(owner_rows))).fetchone()
        required_roles={r['source_role'] for r in source_refs}
        if existing:
            current_producer_sha=sha(Path(__file__).read_bytes())
            existing_sources=pg.execute(f"SELECT source_role,source_sha256 FROM {SCHEMA}.consumed_sources WHERE publication_id=%s",(existing[0],)).fetchall()
            existing_source_map=dict(existing_sources)
            existing_fact_count=pg.execute(f"SELECT count(*) FROM {SCHEMA}.facts WHERE publication_id=%s",(existing[0],)).fetchone()[0]
            if required_roles.issubset(existing_source_map) and existing_source_map.get('D0_PG_OWNER_PUBLICATION_PRODUCER')==current_producer_sha and existing_fact_count==len(fact_rows):
                checked=independent_pg_readback(trade_date,candidate_token)
                if checked.get('status')=='PG_BINDING_PRESENT':
                    return dict(publication_id=existing[0],status='ALREADY_PUBLISHED',predicate_counts=dict(predicate_counts),row_count=len(owner_rows),predicate_digest=predicate_digest)
        publication_status='DEV_SOURCE_VERIFIED' if source_truthful else 'DEV_RECONSTRUCTED_NON_PIT'
        pg.execute(f"INSERT INTO {SCHEMA}.publications(publication_id,revision_no,trade_date,candidate_token,owner_sha256,owner_bytes,predicate_digest,row_count,producer_contract_id,producer_version,parameter_sha256,predecessor_window,knowledge_cutoff_at,cutoff_basis,publication_status,as_recorded,pit_eligible) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'EXACT_R8_SNAPSHOT_PUBLICATION_INSERTED_AT',%s,%s,%s)",
            (publication_id,revision_no,day,candidate_token,owner_binding['sha256'],len(owner_raw),predicate_digest,len(owner_rows),CONTRACT_ID,CONTRACT_VERSION,param_sha,Jsonb(window),cutoff,publication_status,source_truthful,source_truthful))
        for ref in source_refs:
            source_before_cutoff=bool(ref.get('available_at') and ref['available_at']<=cutoff)
            pg.execute(f"INSERT INTO {SCHEMA}.consumed_sources(publication_id,trade_date,candidate_token,source_role,source_path,source_sha256,source_bytes,owner_contract_id,owner_version_token,time_role,evidence_class,available_at,source_ingress_artifact_sha256,source_available_before_cutoff) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (publication_id,day,candidate_token,ref['source_role'],ref['source_path'],ref['source_sha256'],ref['source_bytes'],ref['owner_contract_id'],ref['owner_version_token'],ref['time_role'],ref['evidence_class'],ref['available_at'],ref['source_ingress_artifact_sha256'],source_before_cutoff))
        with pg.cursor().copy(f"COPY {SCHEMA}.facts(publication_id,scenario,security_id,predicate_state,check_values,field_lineage,fact_digest) FROM STDIN") as copy:
            for scenario,security_id,state,checks,lineage,digest in fact_rows:
                copy.write_row((publication_id,scenario,security_id,state,Jsonb(checks),Jsonb(lineage),digest))
        return dict(publication_id=publication_id,status='PUBLISHED_'+publication_status,candidate_token=candidate_token,
            trade_date=trade_date,knowledge_cutoff_at=cutoff.isoformat(),cutoff_basis='EXACT_R8_SNAPSHOT_PUBLICATION_INSERTED_AT',
            owner_sha256=owner_binding['sha256'],owner_bytes=len(owner_raw),predicate_digest=predicate_digest,
            predicate_counts=dict(predicate_counts),scenario_fact_rows=len(fact_rows),source_roles=[r['source_role'] for r in source_refs],
            source_class=d0_class,as_recorded=source_truthful,pit_eligible=source_truthful,production_admission=False)


publish_reconstructed_candidate=publish_candidate


def independent_pg_readback(trade_date, candidate_token):
    """Read the D0 publication as the restricted reader role and rehash facts/owners."""
    import psycopg
    from workbench_db.v4_native import configured_reader_dsn
    result=dict(status='PG_BINDING_MISSING',permission_chain_proven=False,reader_role='v4_r8_d0_seal_reader_r1',
        publications=[],consumed_source_rows=[],fact_rows=0,fact_digest_readback='NOT_RUN',
        reader_session_user=None,reader_current_user=None)
    with psycopg.connect(configured_reader_dsn(),connect_timeout=5) as pg:
        pg.execute('SET TRANSACTION READ ONLY')
        pg.execute("SET LOCAL statement_timeout='20s'")
        pg.execute('SET LOCAL ROLE v4_r8_d0_seal_reader_r1')
        identity=pg.execute('SELECT session_user,current_user,current_setting(\'transaction_read_only\')').fetchone()
        result.update(reader_session_user=identity[0],reader_current_user=identity[1],transaction_read_only=identity[2])
        pub=pg.execute(f"SELECT publication_id,revision_no,trade_date::text,candidate_token,owner_sha256,owner_bytes,predicate_digest,row_count,producer_contract_id,producer_version,parameter_sha256,predecessor_window,knowledge_cutoff_at::text,cutoff_basis,publication_status,as_recorded,pit_eligible,production_admission,published_at::text FROM {SCHEMA}.publications WHERE trade_date=%s AND candidate_token=%s ORDER BY revision_no DESC LIMIT 1",(date.fromisoformat(trade_date),candidate_token)).fetchone()
        if not pub:
            result['reason']='D0_EXACT_DATE_TOKEN_PUBLICATION_NOT_FOUND'
            return result
        keys=('publication_id','revision_no','trade_date','candidate_token','owner_sha256','owner_bytes','predicate_digest','row_count','producer_contract_id','producer_version','parameter_sha256','predecessor_window','knowledge_cutoff_at','cutoff_basis','publication_status','as_recorded','pit_eligible','production_admission','published_at')
        publication=dict(zip(keys,pub)); result['publications']=[publication]
        r8=pg.execute("SELECT candidate_token,trade_date::text,owner_authority_sha256,source_freeze_sha256,inserted_at FROM v4_r8pub_fde08c597fc76d13.r8_publications WHERE candidate_token=%s AND trade_date=%s",(candidate_token,date.fromisoformat(trade_date))).fetchone()
        ingress=pg.execute("SELECT artifact_sha256,artifact_bytes,available_at,time_role,evidence_class,recorded_at FROM v4_r8_batch04_source_ingress.source_receipts WHERE trade_date=%s ORDER BY recorded_at DESC LIMIT 1",(date.fromisoformat(trade_date),)).fetchone()
        sources=pg.execute(f"SELECT source_role,source_path,source_sha256,source_bytes,owner_contract_id,owner_version_token,time_role,evidence_class,available_at::text,source_ingress_artifact_sha256,source_available_before_cutoff FROM {SCHEMA}.consumed_sources WHERE publication_id=%s ORDER BY source_role",(publication['publication_id'],)).fetchall()
        source_keys=('source_role','source_path','source_sha256','source_bytes','owner_contract_id','owner_version_token','time_role','evidence_class','available_at','source_ingress_artifact_sha256','source_available_before_cutoff')
        consumed=[dict(zip(source_keys,row)) for row in sources]
        for source in consumed:
            path=Path(source['source_path'])
            if not path.is_file() or path.stat().st_size!=source['source_bytes'] or sha(path.read_bytes())!=source['source_sha256']:
                source['byte_readback']='MISMATCH'
            else: source['byte_readback']='PASS'
        owner_source=next((s for s in consumed if s['source_role']=='D0_PREDICATE_OWNER_OUTPUT'),None)
        facts=pg.execute(f"SELECT scenario,security_id,predicate_state,check_values,field_lineage,fact_digest FROM {SCHEMA}.facts WHERE publication_id=%s ORDER BY scenario,security_id",(publication['publication_id'],)).fetchall()
        fact_errors=[]
        scenario_status_counts={scenario:Counter() for scenario in FORMAL_SCENARIOS}
        field_samples={}
        for scenario,sid,state,checks,lineage,digest in facts:
            actual=sha(canonical(dict(publication_id=publication['publication_id'],scenario=scenario,security_id=sid,predicate_state=state,check_values=checks,field_lineage=lineage)))
            if actual!=digest: fact_errors.append(sid+':'+scenario)
            scenario_status_counts.setdefault(scenario,Counter())[state]+=1
            if state not in field_samples and checks and lineage:
                check=next(iter(checks))
                field_samples[state]=dict(scenario=scenario,security_id=sid,predicate_state=state,
                    check=check,check_value=checks[check],field_lineage=lineage.get(check))
        usage=pg.execute("SELECT has_schema_privilege(current_user,%s,'USAGE'),has_table_privilege(current_user,%s,'SELECT'),has_table_privilege(current_user,%s,'SELECT'),has_table_privilege(current_user,%s,'SELECT'),has_schema_privilege(current_user,'v4_r8pub_fde08c597fc76d13','USAGE'),has_table_privilege(current_user,'v4_r8pub_fde08c597fc76d13.r8_publications','SELECT'),has_schema_privilege(current_user,'v4_r8_batch04_source_ingress','USAGE'),has_table_privilege(current_user,'v4_r8_batch04_source_ingress.source_receipts','SELECT')",
            (SCHEMA,SCHEMA+'.publications',SCHEMA+'.consumed_sources',SCHEMA+'.facts')).fetchone()
        cutoff_match=bool(r8 and r8[0]==candidate_token and r8[1]==trade_date and r8[4]==datetime.fromisoformat(publication['knowledge_cutoff_at'].replace(' ','T',1)))
        ingress_ref=next((s for s in consumed if s['source_role']=='TDX_SOURCE_INGRESS_ARTIFACT'),None)
        ingress_time=datetime.fromisoformat(ingress_ref['available_at'].replace(' ','T',1)) if ingress_ref and ingress_ref.get('available_at') else None
        ingress_match=bool(ingress and ingress_ref and ingress[0]==ingress_ref['source_sha256'] and ingress[1]==ingress_ref['source_bytes'] and ingress_time==ingress[2])
        producer_match=publication['producer_contract_id']==CONTRACT_ID and publication['producer_version']==CONTRACT_VERSION
        truth_flags_match=((publication['publication_status']=='DEV_RECONSTRUCTED_NON_PIT' and publication['as_recorded'] is False and publication['pit_eligible'] is False) or
            (publication['publication_status']=='DEV_SOURCE_VERIFIED' and publication['as_recorded'] is True and publication['pit_eligible'] is True))
        result.update(consumed_source_rows=consumed,fact_rows=len(facts),fact_digest_readback='PASS' if not fact_errors else 'MISMATCH',fact_digest_errors=fact_errors[:20],
            scenario_status_counts={k:dict(v) for k,v in scenario_status_counts.items()},field_lineage_samples=field_samples,
            snapshot_clock_readback=dict(r8_candidate_present=bool(r8),cutoff_matches_r8_inserted_at=cutoff_match,
                candidate_token_match=bool(r8 and r8[0]==candidate_token),trade_date_match=bool(r8 and r8[1]==trade_date)),
            source_ingress_readback=dict(receipt_present=bool(ingress),exact_artifact_match=ingress_match,
                artifact_sha256=ingress[0] if ingress else None,available_at=ingress[2].isoformat() if ingress else None,
                time_role=ingress[3] if ingress else None,evidence_class=ingress[4] if ingress else None),
            producer_contract_match=producer_match,
            owner_select_privileges=dict(schema_usage=bool(usage[0]),publications=bool(usage[1]),consumed_sources=bool(usage[2]),facts=bool(usage[3]),
                r8_schema=bool(usage[4]),r8_publications=bool(usage[5]),source_ingress_schema=bool(usage[6]),source_receipts=bool(usage[7])),
            permission_chain_proven=(identity[1]=='v4_r8_d0_seal_reader_r1' and identity[2]=='on' and all(usage)),
            status='PG_BINDING_PRESENT' if identity[1]=='v4_r8_d0_seal_reader_r1' and publication['trade_date']==trade_date and publication['candidate_token']==candidate_token and publication['owner_sha256']==(owner_source or {}).get('source_sha256') and truth_flags_match and publication['production_admission'] is False and producer_match and cutoff_match and ingress_match and len(facts)==2*publication['row_count'] and not fact_errors and all(s['byte_readback']=='PASS' for s in consumed) and all(usage) else 'PG_BINDING_INVALID')
    return result
