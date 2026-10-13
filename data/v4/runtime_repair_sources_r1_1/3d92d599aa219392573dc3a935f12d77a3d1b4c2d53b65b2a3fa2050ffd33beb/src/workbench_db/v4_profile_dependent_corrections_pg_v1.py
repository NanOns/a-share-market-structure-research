"""Native D0/D2 thin updates; unchanged lifecycle business state is conserved."""
import json
from pathlib import Path
from v4.state_identity import digest as row_digest
from workbench_analysis.r43_operational_publication import digest
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from .v4_operational_owner_pg_closeout import prepare as append,read as read_fact,attest_cached

CONTRACT='V4_PROFILE_DEPENDENT_THIN_CORRECTIONS_R1'
KEY='native_profile_dependent_corrections'
BUSINESS=('entity_id','entity_type','trade_date','session_index','maturity','health','validity','tracking','scenario','scenario_status','state_freshness','final_eligibility','episode_id','parent_episode_id','exit_session_index','expiry_count','downgrade_candidate','downgrade_count','improvement_baseline','market_age','raw_qualification','detector_statuses','invalidation_contract_id','preserved_followup_episode_ids','transition_reasons','boundary_event')

def validate_replacement(domain,original,replacement):
    if domain=='prewatch':
        if set(original)!=set(replacement) or any(original[k]!=replacement[k] for k in original if k!='prewatch'):raise ValueError('DEPENDENT_PREWATCH_UNRELATED_VALUE_CHANGED')
        if original['prewatch']['raw_qualification']!=replacement['prewatch']['raw_qualification']:raise ValueError('DEPENDENT_PREWATCH_RAW_QUALIFICATION_CHANGED')
    elif domain=='focus':
        if set(original)!=set(replacement):raise ValueError('DEPENDENT_D2_ROW_SCHEMA_CHANGED')
        if any(original.get(k)!=replacement.get(k) for k in BUSINESS):raise ValueError('DEPENDENT_D2_BUSINESS_STATE_CHANGED')
        if any(original.get(k)!=replacement.get(k) for k in ('interface_contract_id','model_contract_id','parameter_set_id','mode','canonicalization_contract_id','calendar_binding','calendar_publication_id')):raise ValueError('DEPENDENT_D2_AUTHORITY_CHANGED')
        before=original['input_provenance'];after=replacement['input_provenance']
        if set(before)!=set(after):raise ValueError('DEPENDENT_D2_FIELD_SCOPE_CHANGED')
        for name,cell in before.items():
            if cell['value']!=after[name]['value'] and not (name=='risk' and cell['value']=='UNKNOWN' and after[name]['value'] in ('LOW','MEDIUM')):raise ValueError('DEPENDENT_D2_UNRELATED_INPUT_VALUE_CHANGED')
    else:raise ValueError('DEPENDENT_CORRECTION_DOMAIN_FORBIDDEN')

def prepare(root,candidate,patches):
    root=Path(root);entries={}
    if set(patches)!=set(candidate['owners']):raise ValueError('DEPENDENT_CORRECTION_DATES_REQUIRED')
    for day,domains in patches.items():
        if set(domains)!={'focus','prewatch'}:raise ValueError('DEPENDENT_CORRECTION_DOMAINS_REQUIRED')
        entries[day]={}
        for domain,source in domains.items():
            document=json.loads(checked(root,source).read_bytes())
            if document.get('contract_id')!=CONTRACT or document.get('T0')!=day or document.get('domain')!=domain or document.get('original')!=candidate['owners'][day][domain] or document.get('publication_ready') is not False:raise ValueError('DEPENDENT_CORRECTION_CONTEXT_MISMATCH')
            token=digest(dict(contract_id=CONTRACT,T0=day,domain=domain,source=source));kind='reference_profile_dependent_'+domain
            descriptor=append(root,token,day,kind,source,document['rows'])
            if read_fact(root,descriptor,token,day,kind,source)!=document['rows']:raise ValueError('DEPENDENT_CORRECTION_FULL_PG_PAYLOAD_DIFFERENCE')
            entries[day][domain]=dict(source=source,descriptor=descriptor,fact_token=token,original=document['original'],entity_ids=[r['entity_id'] for r in document['rows']])
    authority=dict(contract_id=CONTRACT,dates=entries,source_owners={d:{k:o[k] for k in ('focus','prewatch')} for d,o in candidate['owners'].items()},profile_correction=candidate['native_profile_semantic_corrections'],PIT_ELIGIBLE=False,AS_RECORDED=False)
    path=root/'data/v4/profile_dependent_corrections_pg_v1'/digest(authority)/'AUTHORITY.json';atomic_json(root,path,authority);candidate[KEY]=ref(root,path)

def load(root,candidate):
    authority=json.loads(checked(root,candidate[KEY]).read_bytes())
    expected={d:{k:o[k] for k in ('focus','prewatch')} for d,o in candidate['owners'].items()}
    from .v4_profile_semantic_corrections_pg_v1 import conserved_dates,load as load_profile
    dates=conserved_dates(root,candidate,KEY,authority.get('source_owners',{}),expected)
    load_profile(root,candidate)
    if authority.get('contract_id')!=CONTRACT or authority.get('profile_correction')!=candidate['native_profile_semantic_corrections'] or set(authority.get('dates',{}))!=dates:raise ValueError('DEPENDENT_CORRECTION_OWNER_CONSERVATION_REQUIRED')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED')):raise ValueError('DEPENDENT_CORRECTION_PIT_ESCALATION')
    for day,entries in authority['dates'].items():
        if set(entries)!={'focus','prewatch'} or any(e['original']!=expected[day][k] for k,e in entries.items()):raise ValueError('DEPENDENT_CORRECTION_OWNER_CONSERVATION_REQUIRED')
    return authority

def apply(root,candidate,day,domain,original):
    entry=load(root,candidate)['dates'].get(day)
    if entry is None:return original
    entry=entry[domain];kind='reference_profile_dependent_'+domain
    patches=read_fact(root,entry['descriptor'],entry['fact_token'],day,kind,entry['source']);index={r['entity_id']:r for r in patches};seen=set();result=[]
    if len(index)!=len(patches) or set(index)!=set(entry['entity_ids']):raise ValueError('DEPENDENT_CORRECTION_DENOMINATOR')
    for row in original:
        entity=row['entity_id'] if domain=='focus' else row['security_id'];patch=index.get(entity)
        if patch is None:result.append(row);continue
        if row_digest(row)!=patch['original_row_digest']:raise ValueError('DEPENDENT_CORRECTION_ORIGINAL_ROW_CHANGED')
        validate_replacement(domain,row,patch['replacement']);result.append(patch['replacement']);seen.add(entity)
    if seen!=set(index):raise ValueError('DEPENDENT_CORRECTION_ORIGINAL_ROW_MISSING')
    return result

def attest(root,candidate,day,domain):
    entry=load(root,candidate)['dates'].get(day)
    if entry is None:return
    entry=entry[domain]
    attest_cached(root,entry['descriptor'],'reference_profile_dependent_'+domain,entry['source'])
