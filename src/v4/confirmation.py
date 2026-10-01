"""Exact V3.3 D0 extraction wrapped by explicit candidate provenance gates."""
from copy import deepcopy
from datetime import datetime,date,timezone
from functools import lru_cache
from pathlib import Path
import ast,hashlib,json,math
ROOT=Path(__file__).resolve().parents[2]
MODEL='CONFIRMATION_DETECTOR_V1';PARAMETERS='V4_11_CONFIRMATION_PARAMETER_SET_V1'
CONTRACT='config/v4_11_confirmation_detector_contract_r1.json'
SCENARIO_KEYS={'LAUNCH_CONFIRM':'launch','STRONG_PULLBACK':'pullback','RECOVERY_TURN':'recovery_turn','TREND_CONTINUE':'trend_continue'}
AMOUNT_BRANCHES={'LAUNCH_CONFIRM','RECOVERY_TURN','TREND_CONTINUE'}
FORBIDDEN_ROLES={'FINAL_STATE','FOCUS','SAME_DAY_DOWNSTREAM','ONLINE_SUPPLEMENTAL','FUTURE_OUTCOME'}
class ConfirmationError(ValueError):pass
def digest(value):
    from .state_identity import digest as canonical_digest
    return canonical_digest(value)
def exact(ref):
    p=(ROOT/ref['path']).resolve()
    if not p.is_relative_to(ROOT) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=ref['sha256'] or p.stat().st_size!=ref.get('bytes',ref.get('byte_count',p.stat().st_size)):
        raise ConfirmationError('EXACT_INPUT_BINDING_INVALID:'+ref['path'])
    return p
def bound(ref):return json.loads(exact(ref).read_bytes())
@lru_cache(maxsize=1)
def package():
    c=json.loads((ROOT/CONTRACT).read_bytes());entry=bound(c['entry_contract']);legacy=entry['legacy_inventory']['source']
    source=exact(legacy).read_text(encoding='utf8');tree=ast.parse(source)
    manifest=bound(c['legacy_manifest']);parameters=bound(c['parameters']);machine=bound(c['machine_ast'])
    functions={n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    if functions!=manifest['exact_function_AST'] or manifest['legacy_source']!=legacy:raise ConfirmationError('EXACT_LEGACY_AST_REQUIRED')
    from workbench_analysis.today_research_scanner_v3_3 import PARAMETER_CONTRACT,SCENARIOS,scan_today_research
    if parameters['values']!=PARAMETER_CONTRACT or machine['scenario_priority']!=[manifest['scenario_mapping'][s] for s in SCENARIOS]:raise ConfirmationError('LEGACY_PARAMETER_OR_PRIORITY_CHANGED')
    if c['amount_A']['formal_branch']!='DISABLED' or c['permissions']!=dict(production=False,shadow=False,focus=False):raise ConfirmationError('CANDIDATE_PERMISSION_OVERCLAIM')
    exact(c['v4_10_head']);exact(c['executable_authority'])
    return c,manifest,parameters,machine,scan_today_research
def _timestamp(value):
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None:raise ConfirmationError('AWARE_TIMESTAMP_REQUIRED')
    return t
def validate_publication(publication):
    c,m,p,a,scanner=package()
    if publication.get('producer_contract_id')!=c['input_producer_contract_id']:raise ConfirmationError('PRODUCER_MISMATCH')
    if publication.get('parameter_set_id')!=c['input_parameter_set_id']:raise ConfirmationError('PARAMETER_MISMATCH')
    if publication.get('accepted_data_head')!=c['accepted_data_head']:raise ConfirmationError('UNACCEPTED_DATA_HEAD')
    head=bound(c['accepted_data_head'])
    if head['contract_id']!='V4_DATA_ACCEPTED_HEAD_V2' or head['accepted_trade_date']!=publication['trade_date']:raise ConfirmationError('ACCEPTED_DATA_HEAD_DATE_MISMATCH')
    if publication.get('mode') not in ('REAL_ACCEPTED_INPUT_CANDIDATE','SYNTHETIC_ENGINEERING_VECTOR'):raise ConfirmationError('INPUT_MODE_INVALID')
    cutoff=_timestamp(publication['cutoff_timestamp']);target=date.fromisoformat(publication['trade_date'])
    if cutoff>datetime.now(timezone.utc):raise ConfirmationError('FUTURE_TIMESTAMP_REJECTED')
    if cutoff<_timestamp(head['promoted_at_utc']):raise ConfirmationError('DATA_HEAD_NOT_AVAILABLE_AT_KNOWLEDGE_CUTOFF')
    refs=publication.get('source_bindings',[])
    if not refs or publication['source_publication_ids']!=[r['sha256'] for r in refs] or len(set(publication['source_publication_ids']))!=len(refs):raise ConfirmationError('PUBLICATION_MISMATCH')
    allowed={digest(ref) for ref in [head['calendar'],head['identity'],head['accepted_chain'],*head['component_artifacts'].values()]}
    for ref in refs:
        exact(ref)
        if digest(ref) not in allowed:raise ConfirmationError('SOURCE_PUBLICATION_OUTSIDE_ACCEPTED_HEAD')
    rows=publication.get('rows')
    if type(rows) is not list or not rows or len({r['security_id'] for r in rows})!=len(rows):raise ConfirmationError('DUPLICATE_OR_EMPTY_INPUT_ROWS')
    real_components={}
    if publication['mode']=='REAL_ACCEPTED_INPUT_CANDIDATE':
        for cap in ('IDENTITY_UNIVERSE','RAW_DAILY','TRADING_STATUS'):
            real_components[cap]={r['security_id']:r for r in bound(head['component_artifacts'][cap])['rows']}
        if {r['security_id'] for r in rows}!=set(real_components['IDENTITY_UNIVERSE']):raise ConfirmationError('FULL_MARKET_UNIVERSE_REQUIRED')
    for row in rows:
        if row['trade_date']!=publication['trade_date']:raise ConfirmationError('TARGET_DATE_MISMATCH')
        if real_components and row['security_id'] not in real_components['IDENTITY_UNIVERSE']:raise ConfirmationError('IDENTITY_OUTSIDE_ACCEPTED_UNIVERSE')
        for field,fact in row['facts'].items():
            if fact['time_role'] in FORBIDDEN_ROLES:raise ConfirmationError('SAME_DAY_FEEDBACK_REJECTED')
            if field not in m['input_fields'] or fact['time_role']!=m['input_time_roles'][field]:raise ConfirmationError('FACT_TIME_ROLE_MISMATCH')
            if fact['time_role']=='PRIOR_SESSION_WINDOW' and fact.get('trade_date',row['trade_date'])>=target.isoformat():raise ConfirmationError('PRIOR_WINDOW_MUST_END_BEFORE_TARGET')
            if fact['time_role']=='TARGET_SESSION_D0' and fact.get('trade_date')!=target.isoformat():raise ConfirmationError('CURRENT_FACT_MUST_BIND_TARGET_SESSION')
            if fact.get('trade_date',row['trade_date'])>target.isoformat() or _timestamp(fact['system_available_at'])>cutoff:raise ConfirmationError('FUTURE_TIMESTAMP_REJECTED')
            if fact['source_publication_id'] not in publication['source_publication_ids']:raise ConfirmationError('PUBLICATION_MISMATCH')
            if field in m['input_units'] and fact.get('unit')!=m['input_units'][field]:raise ConfirmationError('INPUT_UNIT_MISMATCH')
            if real_components and fact.get('quality')=='KNOWN':
                sid=row['security_id']
                if fact.get('acceptance')!='EXTERNALLY_ACCEPTED':continue
                if field=='actual_bar':
                    expected=sid in real_components['RAW_DAILY'];cap='RAW_DAILY' if expected else 'TRADING_STATUS'
                    if not expected and real_components['TRADING_STATUS'][sid]['status']!='SUSPENDED':raise ConfirmationError('ACTUAL_BAR_SOURCE_CONFLICT')
                elif field=='input_identity_compatible':
                    expected=all(real_components['IDENTITY_UNIVERSE'][sid]['source_security_key']==r[sid]['source_security_key'] for r in (real_components['TRADING_STATUS'],real_components['RAW_DAILY']) if sid in r);cap='IDENTITY_UNIVERSE'
                else:raise ConfirmationError('SOURCE_FIELD_NOT_ACCEPTED_FOR_TARGET')
                if fact['value'] is not expected or fact['source_publication_id']!=head['component_artifacts'][cap]['sha256']:raise ConfirmationError('SOURCE_FIELD_PAYLOAD_DIGEST_MISMATCH')
    expected=dict(publication);pid=expected.pop('publication_id',None);checksum=expected.pop('input_digest',None)
    if checksum!=digest(expected) or pid!='V4_11_INPUT:'+checksum:raise ConfirmationError('INPUT_DIGEST_OR_PUBLICATION_MISMATCH')
    return c,m,p,a,scanner
def detect_confirmation(publication):
    c,m,p,a,scanner=validate_publication(publication);results=[]
    for row in sorted(publication['rows'],key=lambda r:r['security_id']):
        values={};unavailable={}
        for field in m['input_fields']:
            fact=row['facts'].get(field)
            if not fact or fact.get('quality')!='KNOWN' or fact.get('acceptance') not in (('ENGINEERING_VECTOR',) if publication['mode']=='SYNTHETIC_ENGINEERING_VECTOR' else ('EXTERNALLY_ACCEPTED',)):
                values[field]=None;unavailable[field]=fact.get('reason','REQUIRED_FACT_UNAVAILABLE') if fact else 'REQUIRED_FACT_MISSING'
            else:values[field]=fact['value']
        values.update(security_id=row['security_id'],trade_date=row['trade_date']);legacy=scanner(values)
        evidences=[];matched=[];unknown=[];raw={}
        for scenario in a['scenario_priority']:
            branch=legacy[SCENARIO_KEYS[scenario]];checks=branch['checks'];raw[scenario]=deepcopy(checks)
            reasons=[k+':UNKNOWN' for k,v in checks.items() if v is None]
            if scenario in AMOUNT_BRANCHES:reasons.append('AUD-AMOUNT-A-06:FORMAL_BRANCH_DISABLED')
            if scenario=='TREND_CONTINUE':reasons.append('CURRENT_WITH_LOO_BREADTH_SUPPORT:SAME_DAY_DOWNSTREAM_DIAGNOSTIC_ONLY')
            # Legacy tri_and stays exact; the required-fact governance wrapper is UNKNOWN dominant.
            status='UNKNOWN' if reasons else 'TRUE' if branch['eligible'] is True else 'FALSE'
            if status=='TRUE':matched.append(scenario)
            unknown.extend(scenario+':'+r for r in reasons)
            evidences.append(dict(scenario=scenario,status=status,legacy_eligible=branch['eligible'],checks=deepcopy(checks),unknown_reasons=reasons,
                source_function='scan_today_research',source_sha256=m['legacy_source']['sha256'],parameter_set_id=PARAMETERS,scope='ENGINEERING_VECTOR' if publication['mode']=='SYNTHETIC_ENGINEERING_VECTOR' else 'REAL_INPUT_CANDIDATE'))
        # A missing required fact remains UNKNOWN even if another legacy branch is known FALSE.
        status='TRUE' if matched else 'UNKNOWN' if unknown else 'FALSE'
        results.append(dict(security_id=row['security_id'],trade_date=row['trade_date'],confirmation_status=status,
            matched_scenarios=matched,primary_scenario=matched[0] if matched else None,scenario_evidence=evidences,
            raw_predicates=raw,unknown_predicates=sorted(set(unknown)),unavailable_input_facts=unavailable,
            diagnostic_legacy_matches=[s for s in a['scenario_priority'] if legacy[SCENARIO_KEYS[s]]['eligible'] is True],
            producer_contract_id=MODEL,parameter_set_id=PARAMETERS,source_publication_ids=publication['source_publication_ids'],
            input_digest=publication['input_digest'],input_publication_id=publication['publication_id'],mode=publication['mode'],
            amount_A_formal_branch='DISABLED',knowledge_lineage='SYNTHETIC_ENGINEERING_VECTOR' if publication['mode']=='SYNTHETIC_ENGINEERING_VECTOR' else 'RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
    checksum=digest(results);pid='V4_11_CONFIRMATION:'+checksum
    return dict(contract_id='CONFIRMATION_FACT_V1',publication_id=pid,logical_digest=checksum,rows=[dict(r,publication_id=pid) for r in results],
        input_publication_id=publication['publication_id'],input_digest=publication['input_digest'],accepted=False,
        status='V4_11_CONFIRMATION_EVENTS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',permissions=c['permissions'])
