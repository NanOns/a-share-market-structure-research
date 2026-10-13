"""Native thin Profile corrections with immutable original row conservation."""
import json
from pathlib import Path
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.r43_operational_publication import digest
from v4.state_identity import digest as row_digest
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from .v4_operational_owner_pg_closeout import prepare as append,read as read_fact

CONTRACT='V4_PROFILE_BRANCH_SEMANTIC_THIN_CORRECTION_R1'
KEY='native_profile_semantic_corrections'

def validate_replacement(original,replacement):
    permitted={'states','output_digest','profile_component_status','profile_quality'}
    if set(original)!=set(replacement) or any(original[k]!=replacement[k] for k in original if k not in permitted):raise ValueError('PROFILE_CORRECTION_UNRELATED_FIELD_CHANGED')
    if set(original['states'])!=set(replacement['states']) or any(original['states'][k]!=replacement['states'][k] for k in original['states'] if k not in ('core_extension_risk','severe_extension')):raise ValueError('PROFILE_CORRECTION_UNRELATED_STATE_CHANGED')
    old=original['states']['core_extension_risk'];new=replacement['states']['core_extension_risk'];severe=replacement['states']['severe_extension']
    if old['value']!='UNKNOWN' or original['states']['severe_extension']['value'] is not None or new['value'] not in ('LOW','MEDIUM') or severe['value'] is not False or new.get('evidence')!=old.get('evidence') or new.get('unknown_reason') is not None or severe.get('unknown_reason') is not None:
        raise ValueError('PROFILE_CORRECTION_BRANCH_SCOPE_INVALID')
    if severe.get('evidence')!={'core_extension_risk':new['value']}:raise ValueError('PROFILE_CORRECTION_SEVERE_DEPENDENCY_INVALID')
    for name in ('core_extension_risk','severe_extension'):
        before=original['states'][name];after=replacement['states'][name]
        if set(before)!=set(after) or any(before[k]!=after[k] for k in before if k not in ('value','evidence','unknown_reason','input_digest','output_digest')):raise ValueError('PROFILE_CORRECTION_CELL_PROVENANCE_CHANGED')
        if after['input_digest']!=row_digest(after['evidence']) or after['output_digest']!=row_digest({k:v for k,v in after.items() if k!='output_digest'}):raise ValueError('PROFILE_CORRECTION_CELL_DIGEST_INVALID')
    if replacement['output_digest']!=row_digest({k:v for k,v in replacement.items() if k!='output_digest'}):raise ValueError('PROFILE_CORRECTION_ROW_DIGEST_INVALID')

def prepare(root,candidate,patches):
    root=Path(root);entries={}
    if set(patches)!=set(candidate['owners']):raise ValueError('PROFILE_CORRECTION_DATE_SCOPE_REQUIRED')
    for day,source in patches.items():
        document=json.loads(checked(root,source).read_bytes())
        if document.get('contract_id')!=CONTRACT or document.get('T0')!=day or document.get('original_profile')!=candidate['owners'][day]['profile']:
            raise ValueError('PROFILE_CORRECTION_SOURCE_SCOPE_MISMATCH')
        if any(document.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED','publication_ready')):raise ValueError('PROFILE_CORRECTION_CAPABILITY_ESCALATION')
        checked(root,document['source']);token=digest(dict(contract_id=CONTRACT,T0=day,source=source))
        domain='reference_profile_semantic_corrections';descriptor=append(root,token,day,domain,source,document['rows'])
        if read_fact(root,descriptor,token,day,domain,source)!=document['rows']:raise ValueError('PROFILE_CORRECTION_FULL_PG_PAYLOAD_DIFFERENCE')
        entries[day]=dict(source=source,descriptor=descriptor,fact_token=token,original_profile=document['original_profile'],security_ids=[r['security_id'] for r in document['rows']],producing_source=document['source'])
    authority=dict(contract_id=CONTRACT,dates=entries,source_profiles={d:o['profile'] for d,o in candidate['owners'].items()},PIT_ELIGIBLE=False,AS_RECORDED=False)
    target=root/'data/v4/profile_semantic_corrections_pg_v1'/digest(authority)/'AUTHORITY.json';atomic_json(root,target,authority);candidate[KEY]=ref(root,target)
    return dict(rows=sum(len(e['security_ids']) for e in entries.values()),dates=len(entries),publication=False)

def load(root,candidate):
    authority=json.loads(checked(root,candidate[KEY]).read_bytes())
    if authority.get('contract_id')!=CONTRACT or authority.get('source_profiles')!={d:o['profile'] for d,o in candidate['owners'].items()} or set(authority.get('dates',{}))!=set(candidate['owners']):
        raise ValueError('PROFILE_CORRECTION_OWNER_CONSERVATION_REQUIRED')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED')):raise ValueError('PROFILE_CORRECTION_PIT_ESCALATION')
    return authority

def apply(root,candidate,day,original):
    entry=load(root,candidate)['dates'][day]
    patches=read_fact(root,entry['descriptor'],entry['fact_token'],day,'reference_profile_semantic_corrections',entry['source'])
    index={p['security_id']:p for p in patches}
    if len(index)!=len(patches) or set(index)!=set(entry['security_ids']):raise ValueError('PROFILE_CORRECTION_PG_DENOMINATOR')
    result=[];seen=set()
    for row in original:
        sid=row['security_id'];patch=index.get(sid)
        if patch is None:result.append(row);continue
        if row_digest(row)!=patch['original_row_digest'] or patch['replacement']['security_id']!=sid or patch['replacement']['trade_date']!=day:
            raise ValueError('PROFILE_CORRECTION_ORIGINAL_ROW_CHANGED')
        validate_replacement(row,patch['replacement'])
        result.append(patch['replacement']);seen.add(sid)
    if seen!=set(index):raise ValueError('PROFILE_CORRECTION_ORIGINAL_ROW_MISSING')
    return result

def field_binding(root,candidate,day,security_id):
    entry=load(root,candidate)['dates'][day]
    return entry['source'] if security_id in entry['security_ids'] else None

def attest(root,candidate,day):
    from .v4_operational_owner_pg_closeout import attest_cached
    entry=load(root,candidate)['dates'][day]
    attest_cached(root,entry['descriptor'],'reference_profile_semantic_corrections',entry['source'])
