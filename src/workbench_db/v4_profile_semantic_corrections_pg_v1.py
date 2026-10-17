"""Native thin Profile corrections with immutable original row conservation."""
import json
from pathlib import Path
from workbench_analysis.r43_owner_replay import checked
from workbench_analysis.r43_operational_publication import digest
from v4.state_identity import digest as row_digest
from .v4_operational_owner_pg_closeout import (
    append_authority_manifest, descriptor_metadata, inline_descriptor, prepare as append,
    read as read_fact, read_authority_manifest,
)

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
        checked(root,document['source']);fact_identity=digest(dict(contract_id=CONTRACT,T0=day,source=source))
        domain='reference_profile_semantic_corrections';descriptor=append(root,fact_identity,day,domain,source,document['rows'])
        if read_fact(root,descriptor,fact_identity,day,domain,source)!=document['rows']:raise ValueError('PROFILE_CORRECTION_FULL_PG_PAYLOAD_DIFFERENCE')
        descriptor=inline_descriptor(root,descriptor)
        entries[day]=dict(source=source,descriptor=descriptor,fact_token=fact_identity,original_profile=document['original_profile'],security_ids=[r['security_id'] for r in document['rows']],producing_source=document['source'])
    authority=dict(contract_id=CONTRACT,dates=entries,source_profiles={d:o['profile'] for d,o in candidate['owners'].items()},PIT_ELIGIBLE=False,AS_RECORDED=False)
    candidate[KEY]=append_authority_manifest(root,authority)
    return dict(rows=sum(len(e['security_ids']) for e in entries.values()),dates=len(entries),publication=False)

def conserved_dates(root,candidate,key,actual,expected):
    """Follow exact immutable append ancestry back to the fully scoped patch."""
    original=candidate;current=candidate;visited=set()
    for _ in range(4096):
        current_expected={d:expected[d] for d in current['owners'] if d in expected}
        if actual==current_expected and set(actual)==set(current['owners']):return set(actual)
        binding=current.get('predecessor')
        if not binding:raise ValueError('PROFILE_CORRECTION_OWNER_CONSERVATION_REQUIRED')
        marker=(binding.get('path'),binding.get('sha256'))
        if marker in visited:raise ValueError('PROFILE_CORRECTION_PREDECESSOR_CYCLE')
        visited.add(marker)
        prior=json.loads(checked(root,binding).read_bytes())
        if current.get(key)!=prior.get(key) or current.get(key)!=original.get(key) or not current.get(key):
            raise ValueError('PROFILE_CORRECTION_INHERITANCE_BINDING_REQUIRED')
        old_days=set(prior['owners']);new_days=set(current['owners'])-old_days
        if len(new_days)!=1 or new_days!={current['accepted_trade_date']} or current['accepted_trade_date']<=prior['accepted_trade_date']:
            raise ValueError('PROFILE_CORRECTION_SINGLE_APPEND_REQUIRED')
        if any(current['owners'].get(d)!=o for d,o in prior['owners'].items()):raise ValueError('PROFILE_CORRECTION_PREDECESSOR_OWNER_CHANGED')
        current=prior
    raise ValueError('PROFILE_CORRECTION_PREDECESSOR_BOUND_EXCEEDED')


def load(root,candidate):
    binding=candidate.get(KEY)
    if not isinstance(binding,dict):raise ValueError('PROFILE_CORRECTION_PG_AUTHORITY_REQUIRED_NO_FILE_FALLBACK')
    authority=read_authority_manifest(root,binding)
    expected={d:o['profile'] for d,o in candidate['owners'].items()}
    dates=conserved_dates(root,candidate,KEY,authority.get('source_profiles',{}),expected)
    if authority.get('contract_id')!=CONTRACT or set(authority.get('dates',{}))!=dates:
        raise ValueError('PROFILE_CORRECTION_OWNER_CONSERVATION_REQUIRED')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED')):raise ValueError('PROFILE_CORRECTION_PIT_ESCALATION')
    for day,entry in authority['dates'].items():
        if entry['original_profile']!=expected[day]:raise ValueError('PROFILE_CORRECTION_OWNER_CONSERVATION_REQUIRED')
        descriptor_metadata(root,entry['descriptor'])
    return authority

def apply(root,candidate,day,original,*,workspace_root=None):
    entry=load(root,candidate)['dates'].get(day)
    if entry is None:return original
    patches=read_fact(root,entry['descriptor'],entry['fact_token'],day,'reference_profile_semantic_corrections',
                      entry['source'],workspace_root=workspace_root)
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
    entry=load(root,candidate)['dates'].get(day)
    if entry is None:return None
    return entry['source'] if security_id in entry['security_ids'] else None

def attest(root,candidate,day,*,workspace_root=None):
    from .v4_operational_owner_pg_closeout import attest_cached
    entry=load(root,candidate)['dates'].get(day)
    if entry is None:return
    attest_cached(root,entry['descriptor'],'reference_profile_semantic_corrections',entry['source'],
                  workspace_root=workspace_root)
