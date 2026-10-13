"""Native PG membership reference; archive relation rows are producer inputs."""
import json
from pathlib import Path
from .v4_forward_pg_r1 import canonical,digest
from .v4_operational_owner_pg_closeout import prepare as append,read as read_fact
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

KEY='native_membership_reference'
CONTRACT='V4_NATIVE_MEMBERSHIP_REFERENCE_AUTHORITY_R1'

def prepare(root,candidate):
    root=Path(root).resolve();snapshot=json.loads(checked(root,candidate['membership_snapshot']).read_bytes())
    source=snapshot['memberships'];day=candidate['accepted_trade_date']
    token=digest(canonical(dict(contract_id=CONTRACT,T0=day,source=source,membership_snapshot=candidate['membership_snapshot'])))
    from workbench_analysis.r43_operational_publication import rows
    content=rows(root,source);descriptor=append(root,token,day,'reference_memberships',source,content)
    if canonical(read_fact(root,descriptor,token,day,'reference_memberships',source))!=canonical(content):raise ValueError('MEMBERSHIP_REFERENCE_FULL_PG_PAYLOAD_DIFFERENCE')
    authority=dict(contract_id=CONTRACT,T0=day,membership_snapshot=candidate['membership_snapshot'],source=source,descriptor=descriptor,
        fact_token=token,rows=len(content),AS_RECORDED=False,PIT_ELIGIBLE=False)
    path=root/'data/v4/membership_reference_pg_v1'/digest(canonical(authority))/'AUTHORITY.json';atomic_json(root,path,authority)
    candidate[KEY]=ref(root,path)
    return dict(contract_id=CONTRACT,T0=day,rows=len(content),publication=False)

def read(root,candidate):
    binding=candidate.get(KEY)
    if binding is None:raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_REQUIRED_NO_FALLBACK')
    authority=json.loads(checked(root,binding).read_bytes())
    if authority.get('contract_id')!=CONTRACT or authority.get('T0')!=candidate['accepted_trade_date'] or authority.get('membership_snapshot')!=candidate['membership_snapshot']:
        raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_SCOPE_MISMATCH')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED')):raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_PIT_ESCALATION')
    snapshot=json.loads(checked(root,candidate['membership_snapshot']).read_bytes())
    if snapshot['memberships']!=authority['source']:raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_SOURCE_MISMATCH')
    content=read_fact(root,authority['descriptor'],authority['fact_token'],authority['T0'],'reference_memberships',authority['source'])
    if len(content)!=authority['rows']:raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_ROW_DENOMINATOR')
    return content


def current_identity_binding(root,candidate):
    day=candidate['accepted_trade_date'];lifecycle=candidate['owners'][day]['lifecycle']
    document=json.loads(checked(root,lifecycle).read_bytes())
    if document.get('trade_date',document.get('target_session',day))!=day:raise ValueError('CURRENT_IDENTITY_LIFECYCLE_DATE_MISMATCH')
    source=document['identity'];checked(root,source)
    return source,lifecycle


def identity_source(root,candidate):
    authority=json.loads(checked(root,candidate[KEY]).read_bytes())
    entry=authority.get('current_identity')
    if entry:
        source,lifecycle=current_identity_binding(root,candidate)
        if entry.get('source_type')!='CURRENT_LIFECYCLE_IDENTITY_R1' or entry['source']!=source or entry['lifecycle']!=lifecycle:
            raise ValueError('CURRENT_IDENTITY_REFERENCE_SOURCE_MISMATCH')
        return source
    return json.loads(checked(root,candidate['membership_snapshot']).read_bytes())['identity_source']

def prepare_identity(root,candidate):
    """Extend an existing immutable reference without rebuilding memberships."""
    root=Path(root).resolve();authority=json.loads(checked(root,candidate[KEY]).read_bytes())
    if authority['T0']!=candidate['accepted_trade_date'] or authority['membership_snapshot']!=candidate['membership_snapshot']:
        raise ValueError('NATIVE_REFERENCE_EXTENSION_SCOPE_MISMATCH')
    snapshot=json.loads(checked(root,candidate['membership_snapshot']).read_bytes());source=snapshot['identity_source'];day=authority['T0']
    token=digest(canonical(dict(contract_id=CONTRACT,domain='identity',T0=day,source=source,membership_snapshot=candidate['membership_snapshot'])))
    from workbench_analysis.r43_operational_publication import rows
    content=rows(root,source);descriptor=append(root,token,day,'reference_identity',source,content)
    if canonical(read_fact(root,descriptor,token,day,'reference_identity',source))!=canonical(content):raise ValueError('IDENTITY_REFERENCE_FULL_PG_PAYLOAD_DIFFERENCE')
    authority['identity']=dict(source=source,descriptor=descriptor,fact_token=token,rows=len(content))
    current,lifecycle=current_identity_binding(root,candidate)
    current_content=rows(root,current)
    prior={r['security_id']:r for r in content};now={r['security_id']:r for r in current_content}
    if len(now)!=len(current_content) or any(now.get(sid)!=row for sid,row in prior.items()):raise ValueError('CURRENT_IDENTITY_PREDECESSOR_CHANGED')
    current_token=digest(canonical(dict(contract_id=CONTRACT,domain='current_identity',T0=day,source=current,lifecycle=lifecycle)))
    current_descriptor=append(root,current_token,day,'reference_current_identity',current,current_content)
    if canonical(read_fact(root,current_descriptor,current_token,day,'reference_current_identity',current))!=canonical(current_content):raise ValueError('CURRENT_IDENTITY_FULL_PG_PAYLOAD_DIFFERENCE')
    authority['current_identity']=dict(source_type='CURRENT_LIFECYCLE_IDENTITY_R1',source=current,lifecycle=lifecycle,descriptor=current_descriptor,fact_token=current_token,rows=len(current_content))
    path=root/'data/v4/membership_reference_pg_v1'/digest(canonical(authority))/'AUTHORITY.json';atomic_json(root,path,authority);candidate[KEY]=ref(root,path)
    return dict(contract_id=CONTRACT,domain='identity',rows=len(content),membership_fact_recomputed=False,publication=False)

def read_identity(root,candidate):
    binding=candidate.get(KEY)
    if binding is None:raise ValueError('NATIVE_IDENTITY_REFERENCE_REQUIRED_NO_FALLBACK')
    authority=json.loads(checked(root,binding).read_bytes())
    if authority.get('contract_id')!=CONTRACT or authority.get('T0')!=candidate['accepted_trade_date'] or authority.get('membership_snapshot')!=candidate['membership_snapshot']:
        raise ValueError('NATIVE_IDENTITY_REFERENCE_SCOPE_MISMATCH')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED')):raise ValueError('NATIVE_REFERENCE_PIT_ESCALATION')
    entry=authority.get('identity')
    if entry is None:raise ValueError('NATIVE_IDENTITY_REFERENCE_REQUIRED_NO_FALLBACK')
    snapshot=json.loads(checked(root,candidate['membership_snapshot']).read_bytes())
    if entry['source']!=snapshot['identity_source']:raise ValueError('NATIVE_IDENTITY_REFERENCE_SOURCE_MISMATCH')
    content=read_fact(root,entry['descriptor'],entry['fact_token'],authority['T0'],'reference_identity',entry['source'])
    if len(content)!=entry['rows']:raise ValueError('NATIVE_IDENTITY_REFERENCE_ROW_DENOMINATOR')
    current=authority.get('current_identity')
    if current:
        source=identity_source(root,candidate)
        current_content=read_fact(root,current['descriptor'],current['fact_token'],authority['T0'],'reference_current_identity',source)
        now={r['security_id']:r for r in current_content}
        if len(current_content)!=current['rows'] or len(now)!=len(current_content) or any(now.get(r['security_id'])!=r for r in content):raise ValueError('CURRENT_IDENTITY_PREDECESSOR_CHANGED')
        return current_content
    return content

def prepare_search_identity(root,candidate):
    """Preserve the complete accepted identity universe for search explanations."""
    root=Path(root).resolve();authority=json.loads(checked(root,candidate[KEY]).read_bytes())
    head=json.loads((root/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes());source=head['identity']
    content=json.loads(checked(root,source).read_bytes())['records'];day=candidate['accepted_trade_date']
    token=digest(canonical(dict(contract_id=CONTRACT,domain='search_identity',T0=day,source=source)))
    descriptor=append(root,token,day,'reference_search_identity',source,content)
    if canonical(read_fact(root,descriptor,token,day,'reference_search_identity',source))!=canonical(content):raise ValueError('SEARCH_IDENTITY_FULL_PG_PAYLOAD_DIFFERENCE')
    authority['search_identity']=dict(source=source,descriptor=descriptor,fact_token=token,rows=len(content))
    path=root/'data/v4/membership_reference_pg_v1'/digest(canonical(authority))/'AUTHORITY.json';atomic_json(root,path,authority);candidate[KEY]=ref(root,path)
    return dict(contract_id=CONTRACT,domain='search_identity',rows=len(content),prior_reference_facts_recomputed=False,publication=False)

def read_search_identity(root,candidate):
    binding=candidate.get(KEY)
    if binding is None:raise ValueError('NATIVE_SEARCH_IDENTITY_REQUIRED_NO_FALLBACK')
    authority=json.loads(checked(root,binding).read_bytes())
    if authority.get('contract_id')!=CONTRACT or authority.get('T0')!=candidate['accepted_trade_date'] or authority.get('membership_snapshot')!=candidate['membership_snapshot']:
        raise ValueError('NATIVE_SEARCH_IDENTITY_SCOPE_MISMATCH')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED')):raise ValueError('NATIVE_REFERENCE_PIT_ESCALATION')
    entry=authority.get('search_identity')
    if entry is None:raise ValueError('NATIVE_SEARCH_IDENTITY_REQUIRED_NO_FALLBACK')
    content=read_fact(root,entry['descriptor'],entry['fact_token'],authority['T0'],'reference_search_identity',entry['source'])
    if len(content)!=entry['rows']:raise ValueError('NATIVE_SEARCH_IDENTITY_ROW_DENOMINATOR')
    return content,entry['source']

def prepare_research(root,candidate,input_candidate,index):
    """Store already frozen research sidecars; never recalculate their facts."""
    root=Path(root);authority=json.loads(checked(root,candidate[KEY]).read_bytes());day=candidate['accepted_trade_date']
    entry=index.get('sessions',{}).get(day)
    if not entry or entry['head']!=input_candidate or entry.get('production') is not False:raise ValueError('NATIVE_RESEARCH_INPUT_CANDIDATE_REQUIRED')
    original=json.loads(checked(root,input_candidate).read_bytes())
    for name in ('owners','source_registry','day_receipt','exact_daily_generation_scope','membership_snapshot'):
        if original.get(name)!=candidate.get(name):raise ValueError('NATIVE_RESEARCH_OWNER_CONSERVATION_REQUIRED:'+name)
    documents={}
    for name in ('sector','full_state','strict_source','source_capture'):
        source=entry.get(name)
        if not source:continue
        content=json.loads(checked(root,source).read_bytes())
        if content.get('production') is not False:raise ValueError('NATIVE_RESEARCH_PERMISSION_ESCALATION')
        token=digest(canonical(dict(contract_id=CONTRACT,domain='research_'+name,T0=day,source=source)))
        descriptor=append(root,token,day,'reference_research_'+name,source,content)
        if canonical(read_fact(root,descriptor,token,day,'reference_research_'+name,source))!=canonical(content):raise ValueError('NATIVE_RESEARCH_FULL_PAYLOAD_DIFFERENCE')
        documents[name]=dict(source=source,descriptor=descriptor,fact_token=token)
    authority['research']=dict(input_candidate=input_candidate,T0=day,documents=documents)
    path=root/'data/v4/membership_reference_pg_v1'/digest(canonical(authority))/'AUTHORITY.json';atomic_json(root,path,authority);candidate[KEY]=ref(root,path)
    return dict(documents=sorted(documents),numeric_producers_reexecuted=False,publication=False)

def research_authority(root,candidate,day):
    authority=json.loads(checked(root,candidate[KEY]).read_bytes())
    if authority.get('contract_id')!=CONTRACT or authority.get('T0')!=candidate['accepted_trade_date'] or authority.get('membership_snapshot')!=candidate['membership_snapshot']:
        raise ValueError('NATIVE_RESEARCH_AUTHORITY_SCOPE_MISMATCH')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED')):raise ValueError('NATIVE_REFERENCE_PIT_ESCALATION')
    research=authority.get('research')
    if not research or research['T0']!=day:raise ValueError('NATIVE_RESEARCH_DATED_AUTHORITY_REQUIRED')
    original=json.loads(checked(root,research['input_candidate']).read_bytes())
    for name in ('owners','source_registry','day_receipt','exact_daily_generation_scope','membership_snapshot'):
        if original.get(name)!=candidate.get(name):raise ValueError('NATIVE_RESEARCH_OWNER_CONSERVATION_REQUIRED:'+name)
    return research

def read_research(root,candidate,day,source):
    research=research_authority(root,candidate,day)
    matches=[(name,entry) for name,entry in research['documents'].items() if entry['source']==source]
    if len(matches)!=1:raise ValueError('NATIVE_RESEARCH_SOURCE_NOT_BOUND_NO_FALLBACK')
    name,entry=matches[0]
    return read_fact(root,entry['descriptor'],entry['fact_token'],day,'reference_research_'+name,source)
