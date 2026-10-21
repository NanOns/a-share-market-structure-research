"""D0 successor source evidence and independent PostgreSQL seal verification.

Predicate outputs remain owned by the frozen D0 scanner. This module adds
source lineage and verifies source/Owner/Publication facts from the live PG
database; caller booleans and self-reported digests are never authorities.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from datetime import timezone

CONTRACT_ID = 'V4_D0_SOURCE_SEAL_SUCCESSOR_R1'
CONTRACT_VERSION = '1.0.0'
FORMAL_SCENARIOS = ('LAUNCH_CONFIRM', 'RECOVERY_TURN')
DIAGNOSTIC_SCENARIOS = ('STRONG_PULLBACK', 'TREND_CONTINUE')
CHECK_INPUTS = {
    'LAUNCH_CONFIRM': {
        'ACTUAL_BAR':'actual_bar','AMR20_GTE_120':'amr20_mean_prior',
        'BREAKOUT_V3':'breakout_v3','CLOSE_ABOVE_PHC20':'close_above_prior_high',
        'CLV_GTE_060':'clv','INPUT_IDENTITY_COMPATIBLE':'input_identity_compatible',
        'LIQ20':'liq20','NORMAL_UNIVERSE':'normal_universe','NOT_EXTENDED':'extended_v3',
        'NOT_FIRST_DAY_DAMAGE':'first_day_damage','NOT_SEVERE_DROP':'severe_drop',
        'NOT_STRUCTURE_BREAK':'structure_break_v3','NO_INTRADAY_REJECT_HIGH20':'intraday_reject_high20',
        'POSITIVE_RET1':'ret1_adj','WINDOW_VALID':'window_valid'},
    'RECOVERY_TURN': {
        'ACTUAL_BAR':'actual_bar','AMR20_GTE_105':'amr20_mean_prior',
        'CLOSE_GTE_098_MA20':'close_to_ma20','CLV_GTE_055':'clv',
        'INPUT_IDENTITY_COMPATIBLE':'input_identity_compatible','LIQ20':'liq20',
        'NORMAL_UNIVERSE':'normal_universe','NOT_EXTENDED':'extended_v3',
        'NOT_FIRST_DAY_DAMAGE':'first_day_damage','NOT_SEVERE_DROP':'severe_drop',
        'NOT_STRUCTURE_BREAK':'structure_break_v3','POSITIVE_RET1':'ret1_adj',
        'R5_OR_R20':'rps5_or_rps20','RPS5_DELTA3_POSITIVE':'rps5_delta3',
        'WINDOW_VALID':'window_valid'},
}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def source_ref(root, binding, *, role, time_role='RECONSTRUCTED_INPUT_BINDING'):
    """Recheck one exact candidate Owner file and describe its source role."""
    from .r43_owner_replay import checked
    path = checked(root, binding)
    return dict(role=role, path=binding['path'], sha256=_sha(path), bytes=path.stat().st_size,
        time_role=time_role, source_available_at=None,
        source_availability_proven=False,
        availability_reason='CANDIDATE_FILE_BINDING_HAS_NO_TRUSTED_SOURCE_CLOCK')


def _versioned_source_ref(path, role):
    from .r43_owner_replay import ref
    repository_root=Path(__file__).resolve().parents[2]
    return ref(repository_root,repository_root/path)|dict(role=role,source_scope='WORKSPACE_SOURCE',
        time_role='VERSIONED_CODE_CONTRACT',source_available_at=None,
        source_availability_proven=False)


def _clock_evidence(pg_readback):
    return dict(source_ingress_receipts=[dict(
            trade_date=r.get('trade_date'),source_contract=r.get('source_contract'),
            source_revision_id=r.get('artifact_sha256'),source_sha256=r.get('source_sha256'),
            source_file_bytes=r.get('artifact_bytes'),source_file_sha256=r.get('artifact_sha256'),
            source_available_at=r.get('available_at'),recorded_at=r.get('recorded_at'),
            time_role=r.get('time_role'),evidence_class=r.get('evidence_class'),
            byte_readback=r.get('byte_readback'),publication_id=None,
            publication_status='SOURCE_INGRESS_ONLY_NOT_D0_PUBLICATION')
        for r in pg_readback.get('source_ingress',{}).get('receipts',[])],
        d0_owner_publication=pg_readback.get('d0_owner_publication',{}),
        candidate_publication=pg_readback.get('candidate_publication',{}),
        clock_source_schema=pg_readback.get('source_ingress',{}).get('schema'),
        source_ingress_time_is_historical_first_availability=False)


def _observed_timezone(value):
    """Return the actual offset in a producer observation timestamp."""
    try:
        parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    except (TypeError,ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return 'UTC' if parsed.utcoffset().total_seconds()==0 else parsed.strftime('%z')


def build_scenario_lineage(root, *, trade_date, owner, parameters_path, observed_at, calendar_binding):
    """Make the formal scenario-to-input-to-byte lineage without extra inputs."""
    from .r43_owner_replay import ref
    source_refs = [
        source_ref(root, owner['history'], role='RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW'),
        source_ref(root, owner['core'], role='CORE_AND_RELATIVE_STRENGTH_FACTS'),
        dict(calendar_binding, role='OFFICIAL_MASTER_SESSION_CALENDAR',
            time_role='VERSIONED_SESSION_CALENDAR', source_available_at=None,
            source_availability_proven=False),
        _versioned_source_ref('config/v4_11_confirmation_detector_contract_r2.json','FROZEN_D0_SCANNER_AND_THRESHOLDS'),
        _versioned_source_ref('src/v4/target_fact_producers_r4.py','TARGET_FACT_PRODUCER'),
        _versioned_source_ref('src/workbench_analysis/corrected_focus_replay.py','SCENARIO_DETECTOR'),
        _versioned_source_ref('config/v4_d0_source_seal_successor_v1.json','D0_SOURCE_SEAL_CONTRACT'),
        _versioned_source_ref(parameters_path,'D0_PRODUCER_PARAMETERS'),
    ]
    pg_readback=verify_pg_binding(trade_date)
    return dict(contract_id=CONTRACT_ID, version=CONTRACT_VERSION,
        trade_date=trade_date, source_refs=source_refs,
        producer_observed_at=observed_at,
        observed_at_semantics='THIS_PRODUCER_INVOCATION_TIME_ONLY_NOT_SOURCE_FIRST_AVAILABILITY',
        time_zone=_observed_timezone(observed_at), knowledge_cutoff=None,
        independent_source_clocks=_clock_evidence(pg_readback),
        cutoff_status='CUTOFF_CONTRACT_UNRESOLVED',
        predecessor_window=dict(owner_path=owner['history']['path'],
            owner_sha256=owner['history']['sha256'],
            range_role='TARGET_SESSION_AND_REQUIRED_PRIOR_MASTER_SESSIONS',
            session_dates_status='BOUND_BY_SOURCE_OWNER_NOT_RECONSTRUCTED_FROM_FILE_MTIME'),
        formal_scenarios={scenario:dict(required_checks=list(CHECK_INPUTS[scenario]),
            check_to_input=dict(CHECK_INPUTS[scenario]),
            source_roles=['RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW','CORE_AND_RELATIVE_STRENGTH_FACTS',
                'FROZEN_D0_SCANNER_AND_THRESHOLDS','TARGET_FACT_PRODUCER','SCENARIO_DETECTOR',
                'D0_SOURCE_SEAL_CONTRACT','D0_PRODUCER_PARAMETERS'])
            for scenario in FORMAL_SCENARIOS},
        diagnostic_scenarios=dict((scenario,dict(admission='DEV_DIAGNOSTIC',
            source='NOT_IN_FORMAL_D0_AGGREGATION')) for scenario in DIAGNOSTIC_SCENARIOS),
        predicate_state_mutated=False, AS_RECORDED=False, PIT_ELIGIBLE=False,
        production_admission=False)


def build_candidate_lineage(root, candidate, trade_date, *, observed_at, pg_readback=None):
    """Build a live readback source map from the exact candidate Owner bindings."""
    owners=candidate.get('owners',{}).get(trade_date,{})
    if not owners:
        return None
    refs=[]
    for key,role in (('raw','RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW'),
        ('adjusted','TDX_NATIVE_ADJUSTED_DAILY_WINDOW'),
        ('core','CORE_AND_RELATIVE_STRENGTH_FACTS'),
        ('prewatch','D0_PREDICATE_OWNER_OUTPUT')):
        binding=owners.get(key)
        if binding:
            refs.append(source_ref(root,binding,role=role))
    for path,role in (("config/v4_11_confirmation_detector_contract_r2.json","FROZEN_D0_SCANNER_AND_THRESHOLDS"),
        ("src/v4/target_fact_producers_r4.py","TARGET_FACT_PRODUCER"),
        ("src/workbench_analysis/corrected_focus_replay.py","SCENARIO_DETECTOR"),
        ("config/v4_d0_source_seal_successor_v1.json","D0_SOURCE_SEAL_CONTRACT"),
        ("config/research_attention_v3.yaml","D0_PRODUCER_PARAMETERS")):
        refs.append(_versioned_source_ref(path,role))
    sessions=[x for x in candidate.get('published_sessions',[]) if x<=trade_date]
    pg_readback=pg_readback or verify_pg_binding(trade_date)
    return dict(contract_id=CONTRACT_ID,version=CONTRACT_VERSION,trade_date=trade_date,
        evidence_origin='LIVE_CANDIDATE_OWNER_BINDINGS_RECONCILED_BY_BFF',source_refs=refs,
        producer_observed_at=observed_at,
        observed_at_semantics='BFF_READBACK_TIME_ONLY_NOT_SOURCE_FIRST_AVAILABILITY',
        time_zone=_observed_timezone(observed_at),knowledge_cutoff=None,cutoff_status='CUTOFF_CONTRACT_UNRESOLVED',
        independent_source_clocks=_clock_evidence(pg_readback),
        predecessor_window=dict(candidate_session_count=len(sessions),first_candidate_session=sessions[0] if sessions else None,
            target_session=trade_date,history_owner_binding_present=bool(owners.get('raw')),
            coverage_status='CANDIDATE_DAILY_OWNER_BINDINGS_ONLY; FULL_D0_PREDECESSOR_WINDOW_AND_PG_PUBLICATION_NOT_PROVEN'),
        formal_scenarios={scenario:dict(required_checks=list(CHECK_INPUTS[scenario]),
            check_to_input=dict(CHECK_INPUTS[scenario]),
            source_roles=['RAW_AND_TDX_QFQ_DAILY_WINDOW','TDX_NATIVE_ADJUSTED_DAILY_WINDOW',
                'CORE_AND_RELATIVE_STRENGTH_FACTS','FROZEN_D0_SCANNER_AND_THRESHOLDS',
                'TARGET_FACT_PRODUCER','SCENARIO_DETECTOR','D0_SOURCE_SEAL_CONTRACT',
                'D0_PRODUCER_PARAMETERS']) for scenario in FORMAL_SCENARIOS},
        diagnostic_scenarios=dict((scenario,dict(admission='DEV_DIAGNOSTIC',
            source='NOT_IN_FORMAL_D0_AGGREGATION')) for scenario in DIAGNOSTIC_SCENARIOS),
        predicate_state_mutated=False,AS_RECORDED=False,PIT_ELIGIBLE=False,
        production_admission=False)


def _pg_readback(trade_date, candidate_token=None):
    """Read source ingress and D0 publication bindings from the configured PG."""
    from workbench_db.v4_native import configured_reader_dsn
    import psycopg
    with psycopg.connect(configured_reader_dsn(),connect_timeout=5) as pg:
        pg.execute('SET TRANSACTION READ ONLY')
        pg.execute("SET LOCAL statement_timeout='15s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        pg.execute('SET LOCAL search_path TO v4, pg_catalog')
        identity = pg.execute("SELECT current_database(), (SELECT oid FROM pg_database WHERE datname=current_database()), current_setting('server_version_num'), current_setting('transaction_read_only')").fetchone()
        receipt_exists = pg.execute("SELECT to_regclass('v4_r8_batch04_source_ingress.source_receipts')").fetchone()[0]
        source_rows = []
        bar_counts = []
        if receipt_exists:
            source_rows = pg.execute("SELECT trade_date::text,source_contract,source_sha256,package_date::text,available_at,time_role,evidence_class,artifact_path,artifact_sha256,artifact_bytes,row_count,candidate_only,production_accepted,recorded_at FROM v4_r8_batch04_source_ingress.source_receipts WHERE trade_date=%s ORDER BY recorded_at,artifact_sha256", (date.fromisoformat(trade_date),)).fetchall()
            bar_counts = pg.execute("SELECT evidence_class,source_sha256,count(*) FROM v4_r8_batch04_source_ingress.tdx_bars WHERE trade_date=%s GROUP BY evidence_class,source_sha256 ORDER BY evidence_class,source_sha256", (date.fromisoformat(trade_date),)).fetchall()
        pubs_exists = pg.execute("SELECT to_regclass('v4.publications')").fetchone()[0]
        module_exists = pg.execute("SELECT to_regclass('v4.publication_module_results')").fetchone()[0]
        consumed_exists = pg.execute("SELECT to_regclass('v4.publication_consumed_sources')").fetchone()[0]
        prewatch_exists = pg.execute("SELECT to_regclass('v4.stock_prewatch_publications')").fetchone()[0]
        r8_publications_exists = pg.execute("SELECT to_regclass('v4_r8pub_fde08c597fc76d13.r8_publications')").fetchone()[0]
        publications = []
        module_results = []
        prewatch_publications = []
        candidate_publications = []
        consumed_sources = []
        owner_privileges = []
        if pubs_exists:
            publications = pg.execute("SELECT publication_id,status,model_namespace_id,source_manifest_sha256,computation_identity_sha256,prior_session_publication_id,accepted_at FROM v4.publications WHERE trade_date=%s ORDER BY revision_no", (date.fromisoformat(trade_date),)).fetchall()
        if module_exists:
            module_results = pg.execute("SELECT publication_id,module_key,module_contract_id,owner_schema,owner_relation,owner_version_token,owner_trade_date::text,owner_contract_id,result_digest,row_count,quality_status,as_recorded,pit_eligible,created_at FROM v4.publication_module_results WHERE owner_trade_date=%s AND (module_key ILIKE '%%d0%%' OR module_key ILIKE '%%prewatch%%' OR owner_contract_id ILIKE '%%D0%%' OR owner_contract_id ILIKE '%%PREWATCH%%') ORDER BY created_at", (date.fromisoformat(trade_date),)).fetchall()
        if prewatch_exists:
            prewatch_publications = pg.execute("SELECT publication_id,trade_date::text,model_contract_id,parameter_set_id,source_publication_id,source_core_logical_digest,publication_digest,row_count,acceptance_scope,created_at FROM v4.stock_prewatch_publications WHERE trade_date=%s ORDER BY created_at", (date.fromisoformat(trade_date),)).fetchall()
        if r8_publications_exists and candidate_token:
            candidate_publications = pg.execute("SELECT candidate_token,trade_date::text,predecessor_head_sha256,candidate_head_sha256,owner_authority_sha256,source_freeze_sha256,inserted_at::text FROM v4_r8pub_fde08c597fc76d13.r8_publications WHERE trade_date=%s AND candidate_token=%s ORDER BY inserted_at", (date.fromisoformat(trade_date),candidate_token)).fetchall()
        if consumed_exists and publications:
            publication_ids=[row[0] for row in publications]
            consumed_sources=pg.execute("SELECT publication_id,source_key,source_revision_id,digest FROM v4.publication_consumed_sources WHERE publication_id=ANY(%s) ORDER BY publication_id,source_key", (publication_ids,)).fetchall()
        for row in module_results:
            schema,relation=row[3],row[4]
            if schema and relation:
                try:
                    privilege=pg.execute("SELECT has_schema_privilege(current_user,%s,'USAGE'),has_table_privilege(current_user,%s,'SELECT')",(schema,schema+'.'+relation)).fetchone()
                except Exception:
                    privilege=(False,False)
                owner_privileges.append(dict(owner_schema=schema,owner_relation=relation,
                    current_reader_usage=bool(privilege[0]),current_reader_select=bool(privilege[1])))
    receipts=[]
    for row in source_rows:
        (trade_day,contract,source_sha,package_day,available,time_role,evidence_class,
         artifact_path,artifact_sha,artifact_bytes,row_count,candidate_only,production_accepted,recorded)=row
        artifact=Path(artifact_path)
        byte_check=dict(status='UNAVAILABLE',actual_sha256=None,actual_bytes=None)
        if artifact.is_file():
            byte_check=dict(status='PASS' if _sha(artifact)==artifact_sha and artifact.stat().st_size==artifact_bytes else 'MISMATCH',
                actual_sha256=_sha(artifact),actual_bytes=artifact.stat().st_size)
        receipts.append(dict(trade_date=trade_day,source_contract=contract,source_sha256=source_sha,
            package_date=package_day,available_at=available.isoformat(),time_role=time_role,
            evidence_class=evidence_class,artifact_path=artifact_path,artifact_sha256=artifact_sha,
            artifact_bytes=artifact_bytes,row_count=row_count,candidate_only=candidate_only,
            production_accepted=production_accepted,recorded_at=recorded.isoformat(),byte_readback=byte_check,
            historical_first_availability_proven=False if evidence_class in ('RECONSTRUCTED_NON_PIT','CAPTURED_AFTER_CLOSE_NON_PIT') else None))
    module_publication_ids={r[0] for r in module_results}
    publication_ids={r[0] for r in publications}
    consumed_ids={r[0] for r in consumed_sources}
    consumed_digests={r[3] for r in consumed_sources}
    binding_present=bool(module_results and prewatch_publications and
        module_publication_ids.issubset(publication_ids) and
        module_publication_ids.issubset(consumed_ids) and owner_privileges and
        all(r['current_reader_usage'] and r['current_reader_select'] for r in owner_privileges))
    return dict(database=dict(database=identity[0],oid=identity[1],server_version_num=identity[2],
            transaction_read_only=identity[3],host='127.0.0.1',port=5432),
        source_ingress=dict(schema='v4_r8_batch04_source_ingress',receipt_table_present=bool(receipt_exists),
            receipts=receipts,bar_counts=[dict(evidence_class=r[0],source_sha256=r[1],row_count=r[2]) for r in bar_counts]),
        d0_owner_publication=dict(publications_schema_table_present=bool(pubs_exists),
            module_results_table_present=bool(module_exists),d0_publications=[dict(zip(
                ('publication_id','status','model_namespace_id','source_manifest_sha256','computation_identity_sha256','prior_session_publication_id','accepted_at'),r)) for r in publications],
            d0_module_owner_rows=[dict(zip(('publication_id','module_key','module_contract_id','owner_schema','owner_relation','owner_version_token','owner_trade_date','owner_contract_id','result_digest','row_count','quality_status','as_recorded','pit_eligible','created_at'),r)) for r in module_results],
            consumed_source_rows=[dict(zip(('publication_id','source_key','source_revision_id','digest'),r)) for r in consumed_sources],
            owner_select_privileges=owner_privileges,
            stock_prewatch_table_present=bool(prewatch_exists),
            stock_prewatch_publications=[dict(zip(('publication_id','trade_date','model_contract_id','parameter_set_id','source_publication_id','source_core_logical_digest','publication_digest','row_count','acceptance_scope','created_at'),r)) for r in prewatch_publications],
            status='PG_BINDING_PRESENT' if binding_present else 'PG_BINDING_MISSING',
            permission_chain_proven=binding_present,
            consumed_source_digest_count=len(consumed_digests)),
        candidate_publication=dict(schema='v4_r8pub_fde08c597fc76d13',
            table_present=bool(r8_publications_exists),expected_token=candidate_token,
            rows=[dict(zip(('candidate_token','trade_date','predecessor_head_sha256','candidate_head_sha256','owner_authority_sha256','source_freeze_sha256','inserted_at'),r)) for r in candidate_publications],
            status='TOKEN_MATCH' if candidate_publications and all(r[0]==candidate_token and r[1]==trade_date for r in candidate_publications) else 'PG_CANDIDATE_PUBLICATION_TOKEN_NOT_BOUND'),
        query_scope='EXACT_TARGET_DATE_READ_ONLY; NO OWNER OR PUBLICATION WRITE')


def verify_pg_binding(trade_date, candidate_token=None):
    try:
        return _pg_readback(trade_date,candidate_token)
    except Exception as exc:
        primary=getattr(getattr(exc,'diag',None),'message_primary',None)
        return dict(database=dict(database='market_research',host='127.0.0.1',port=5432,
                transaction_read_only='NOT_CONFIRMED'),
            source_ingress=dict(receipt_table_present=False,receipts=[],bar_counts=[]),
            d0_owner_publication=dict(status='PG_BINDING_MISSING',reason='PG_READ_FAILED:'+type(exc).__name__,
                sqlstate=getattr(exc,'sqlstate',None),detail=primary),
            candidate_publication=dict(status='PG_READ_FAILED',expected_token=candidate_token),
            query_scope='EXACT_TARGET_DATE_READ_ONLY; NO OWNER OR PUBLICATION WRITE')


def candidate_publication_token_matches(expected_token, observed_row, trade_date):
    """Bind an actual candidate publication row to the exact HTTP context token."""
    return bool(isinstance(expected_token,str) and expected_token and
        isinstance(observed_row,dict) and observed_row.get('candidate_token')==expected_token and
        observed_row.get('trade_date')==trade_date)


def evaluate_d0_source_seal(*, root, evidence, scenario, predicate_state, pg_readback):
    """Classify a produced row against independent source and PG receipts."""
    if scenario not in FORMAL_SCENARIOS:
        return dict(predicate_state=predicate_state,seal_state='DIAGNOSTIC_ONLY',
            admission='DEV_DIAGNOSTIC',reason='SCENARIO_EXCLUDED_FROM_FORMAL_D0')
    if not isinstance(evidence,dict):
        return dict(predicate_state=predicate_state,seal_state='SOURCE_MISSING',
            admission='NOT_ADMITTED',reason='D0_SOURCE_LINEAGE_NOT_EMITTED')
    refs=evidence.get('source_refs') or []
    needed={'RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW','CORE_AND_RELATIVE_STRENGTH_FACTS',
        'FROZEN_D0_SCANNER_AND_THRESHOLDS','TARGET_FACT_PRODUCER','SCENARIO_DETECTOR',
        'D0_SOURCE_SEAL_CONTRACT','D0_PRODUCER_PARAMETERS'}
    roles={r.get('role') for r in refs if isinstance(r,dict)}
    if not needed.issubset(roles):
        return dict(predicate_state=predicate_state,seal_state='SOURCE_MISSING',
            admission='NOT_ADMITTED',reason='FORMAL_SCENARIO_INPUT_LINEAGE_INCOMPLETE',
            missing_source_roles=sorted(needed-roles))
    from .r43_owner_replay import checked
    for ref in refs:
        try:
            source_root=Path(__file__).resolve().parents[2] if ref.get('source_scope')=='WORKSPACE_SOURCE' else root
            checked(source_root, ref)
        except (OSError, ValueError, KeyError, TypeError):
            return dict(predicate_state=predicate_state,seal_state='SOURCE_DIGEST_MISMATCH',
                admission='NOT_ADMITTED',reason='PRODUCER_SOURCE_BYTES_DO_NOT_MATCH_BOUND_DIGEST',
                mismatched_source_role=ref.get('role'))
    if evidence.get('cutoff_status')!='CUTOFF_CONTRACT_RESOLVED' or not evidence.get('knowledge_cutoff'):
        state='SOURCE_REPRODUCIBLE_POST_HOC' if any(r.get('evidence_class')=='RECONSTRUCTED_NON_PIT' for r in pg_readback.get('source_ingress',{}).get('receipts',[])) else 'CUTOFF_CONTRACT_UNRESOLVED'
        return dict(predicate_state=predicate_state,seal_state='CUTOFF_CONTRACT_UNRESOLVED',
            source_class=state,historical_first_availability='HISTORICAL_FIRST_AVAILABILITY_NOT_PROVEN',
            admission='NOT_ADMITTED',reason='ACTIVE_SCENARIO_CUTOFF_AND_TIME_ROLE_CONTRACT_NOT_BOUND',
            pg_binding_status=pg_readback.get('d0_owner_publication',{}).get('status'))
    try:
        from datetime import timezone
        cutoff=datetime.fromisoformat(evidence['knowledge_cutoff'].replace('Z','+00:00'))
        if cutoff.tzinfo is None:
            raise ValueError('TIMEZONE_REQUIRED')
    except (TypeError,ValueError):
        return dict(predicate_state=predicate_state,seal_state='CUTOFF_CONTRACT_UNRESOLVED',
            admission='NOT_ADMITTED',reason='KNOWLEDGE_CUTOFF_MUST_BE_CONTRACT_BOUND_AND_TIMEZONED')
    receipts=pg_readback.get('source_ingress',{}).get('receipts',[])
    if not receipts:
        return dict(predicate_state=predicate_state,seal_state='SOURCE_MISSING',
            admission='NOT_ADMITTED',reason='PG_SOURCE_INGRESS_RECEIPT_MISSING')
    for receipt in receipts:
        if receipt.get('trade_date') and receipt['trade_date']!=evidence.get('trade_date'):
            return dict(predicate_state=predicate_state,seal_state='PG_BINDING_MISSING',
                admission='NOT_ADMITTED',reason='PG_SOURCE_RECEIPT_T0_MISMATCH')
        if receipt.get('max_source_trade_date') and receipt['max_source_trade_date']>evidence.get('trade_date',''):
            return dict(predicate_state=predicate_state,seal_state='PG_BINDING_MISSING',
                admission='NOT_ADMITTED',reason='PG_SOURCE_WINDOW_CONTAINS_FUTURE_TRADE_DATE')
        if evidence.get('price_coordinate') not in (None,'TDX_NATIVE_AFFINE_QFQ'):
            return dict(predicate_state=predicate_state,seal_state='SOURCE_DIGEST_MISMATCH',
                admission='NOT_ADMITTED',reason='D0_PRICE_COORDINATE_MISMATCH',
                actual_price_coordinate=evidence.get('price_coordinate'))
        if receipt.get('evidence_class') in ('RECONSTRUCTED_NON_PIT','CAPTURED_AFTER_CLOSE_NON_PIT') or 'RECONSTRUCTED' in str(receipt.get('time_role','')).upper():
            return dict(predicate_state=predicate_state,seal_state='POST_HOC_AFTER_CUTOFF',
                source_class='SOURCE_REPRODUCIBLE_POST_HOC',
                historical_first_availability='HISTORICAL_FIRST_AVAILABILITY_NOT_PROVEN',
                admission='NOT_ADMITTED',reason='POST_HOC_SOURCE_CANNOT_CLAIM_AS_RECORDED')
        if not receipt.get('time_role'):
            return dict(predicate_state=predicate_state,seal_state='PG_BINDING_MISSING',
                admission='NOT_ADMITTED',reason='PG_SOURCE_TIME_ROLE_MISSING')
        try:
            available=datetime.fromisoformat(str(receipt.get('available_at')).replace('Z','+00:00'))
        except (TypeError,ValueError):
            return dict(predicate_state=predicate_state,seal_state='PG_BINDING_MISSING',
                admission='NOT_ADMITTED',reason='PG_SOURCE_INGRESS_CLOCK_OR_TIMEZONE_MISSING')
        if available.tzinfo is None:
            return dict(predicate_state=predicate_state,seal_state='PG_BINDING_MISSING',
                admission='NOT_ADMITTED',reason='PG_SOURCE_INGRESS_CLOCK_OR_TIMEZONE_MISSING')
        if receipt.get('byte_readback',{}).get('status')!='PASS':
            return dict(predicate_state=predicate_state,seal_state='SOURCE_DIGEST_MISMATCH',
                admission='NOT_ADMITTED',reason='PG_SOURCE_ARTIFACT_BYTES_DO_NOT_MATCH_RECEIPT')
        if available > cutoff:
            return dict(predicate_state=predicate_state,seal_state='POST_HOC_AFTER_CUTOFF',
                source_class='SOURCE_REPRODUCIBLE_POST_HOC',
                historical_first_availability='HISTORICAL_FIRST_AVAILABILITY_NOT_PROVEN',
                admission='NOT_ADMITTED',reason='PG_SOURCE_AVAILABLE_AFTER_KNOWLEDGE_CUTOFF',
                available_at=available.isoformat(),knowledge_cutoff=cutoff.isoformat())
    if pg_readback.get('d0_owner_publication',{}).get('status')!='PG_BINDING_PRESENT':
        return dict(predicate_state=predicate_state,seal_state='PG_BINDING_MISSING',
            admission='NOT_ADMITTED',reason='ACTUAL_PG_D0_OWNER_PUBLICATION_PERMISSION_EDGE_MISSING')
    required_source_digests={r.get('sha256') for r in refs if r.get('role') in
        ('RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW','CORE_AND_RELATIVE_STRENGTH_FACTS')}
    consumed_digests={r.get('digest') for r in pg_readback.get('d0_owner_publication',{}).get('consumed_source_rows',[])}
    if not required_source_digests.issubset(consumed_digests):
        return dict(predicate_state=predicate_state,seal_state='PG_BINDING_MISSING',
            admission='NOT_ADMITTED',reason='PG_PUBLICATION_DOES_NOT_CONSUME_EXACT_D0_SOURCE_BYTES')
    if pg_readback.get('d0_owner_publication',{}).get('status')!='PG_BINDING_PRESENT' or not pg_readback.get('d0_owner_publication',{}).get('permission_chain_proven'):
        return dict(predicate_state=predicate_state,seal_state='PERMISSION_NOT_PROVEN',
            admission='NOT_ADMITTED',reason='PG_OWNER_PUBLICATION_PERMISSION_CLOSURE_MISSING')
    return dict(predicate_state=predicate_state,seal_state='VERIFIED_BY_CUTOFF',
        admission='DEV_SOURCE_VERIFIED',reason='EXACT_PG_SOURCE_OWNER_PUBLICATION_AND_PERMISSION_CHAIN_VERIFIED',
        knowledge_cutoff=cutoff.isoformat(),production_admission=False)


def enrich_producer_confirmation(confirmation, evidence):
    """Attach scenario-specific source mapping while preserving predicates."""
    result=dict(confirmation)
    result['source_lineage']=evidence
    result['source_seal_contract']=dict(contract_id=CONTRACT_ID,version=CONTRACT_VERSION,
        seal_state='PENDING_INDEPENDENT_PG_READBACK',admission='NOT_ADMITTED',
        predicate_state=result.get('confirmation_status'),predicate_states_unchanged=True)
    for scenario in result.get('scenario_evidence',[]):
        name=scenario.get('scenario')
        scenario['source_lineage_ref'] = dict(contract_id=CONTRACT_ID,version=CONTRACT_VERSION,
            trade_date=evidence['trade_date'],formal=name in FORMAL_SCENARIOS,
            check_to_input=evidence.get('formal_scenarios',{}).get(name,{}).get('check_to_input'),
            source_roles=evidence.get('formal_scenarios',{}).get(name,{}).get('source_roles'),
            cutoff_status=evidence.get('cutoff_status'),source_refs=evidence.get('source_refs') if name in FORMAL_SCENARIOS else [])
    return result


def source_snapshot_from_pg(trade_date):
    """Compact, auditable target-day PG receipt summary for evidence reports."""
    result=verify_pg_binding(trade_date)
    result['receipt_counts']={
        'source_ingress':len(result.get('source_ingress',{}).get('receipts',[])),
        'd0_publication':len(result.get('d0_owner_publication',{}).get('d0_publications',[])),
        'd0_module_owner':len(result.get('d0_owner_publication',{}).get('d0_module_owner_rows',[])),
        'stock_prewatch_publication':len(result.get('d0_owner_publication',{}).get('stock_prewatch_publications',[]))}
    return result
