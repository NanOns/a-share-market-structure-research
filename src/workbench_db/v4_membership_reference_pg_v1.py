"""Native PG membership reference; archive relation rows are producer inputs."""
import json
from pathlib import Path
from .v4_forward_pg_r1 import canonical,digest,ForwardFactStore
from .v4_native import connection,workspace_schema
from .v4_operational_owner_pg_closeout import prepare as append,read as read_fact
from workbench_analysis.r43_owner_replay import checked

KEY='native_membership_reference'
CONTRACT='V4_NATIVE_MEMBERSHIP_REFERENCE_AUTHORITY_R1'
PG_AUTHORITY_CONTRACT='V4_NATIVE_MEMBERSHIP_REFERENCE_PG_AUTHORITY_R2'
AUTHORITY_KIND='native_membership_reference_authority'
FOLDER='data/v4/membership_reference_pg_v1'

def _persist_authority(root,authority):
    root=Path(root).resolve();store=ForwardFactStore(root,FOLDER)
    payload_sha256=digest(canonical(authority));fact_key=payload_sha256
    store.append(AUTHORITY_KIND,fact_key,authority,migration_timeout_seconds=120)
    return dict(contract_id=PG_AUTHORITY_CONTRACT,engine='postgresql',schema=store.schema,
        database_identity=store.database_identity,kind=AUTHORITY_KIND,fact_key=fact_key,
        payload_sha256=payload_sha256)

def _load_authority(root,candidate):
    binding=candidate.get(KEY)
    if binding is None:raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_REQUIRED_NO_FALLBACK')
    if not isinstance(binding,dict):
        raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_PG_AUTHORITY_IDENTITY_REQUIRED')
    root=Path(root).resolve();schema=workspace_schema(root/FOLDER,'forward')
    if (binding.get('contract_id'),binding.get('engine'),binding.get('schema'),binding.get('kind'))!=(
            PG_AUTHORITY_CONTRACT,'postgresql',schema,AUTHORITY_KIND):
        raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_PG_AUTHORITY_REQUIRED_NO_FILE_FALLBACK')
    fact_key=binding.get('fact_key');expected_sha=binding.get('payload_sha256')
    if (not isinstance(fact_key,str) or len(fact_key)!=64 or any(c not in '0123456789abcdef' for c in fact_key)
            or not isinstance(expected_sha,str) or len(expected_sha)!=64
            or any(c not in '0123456789abcdef' for c in expected_sha)):
        raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_PG_AUTHORITY_IDENTITY_REQUIRED')
    with connection(schema,read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=binding.get('database_identity'):
            raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_PG_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s',
            (AUTHORITY_KIND,fact_key)).fetchone()
    if row is None or row[1]!=expected_sha or digest(row[0].encode())!=expected_sha:
        raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_PG_AUTHORITY_DIGEST_MISMATCH')
    authority=json.loads(row[0])
    if digest(canonical(authority))!=fact_key:
        raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_PG_AUTHORITY_KEY_MISMATCH')
    return authority

def prepare(root,candidate):
    root=Path(root).resolve();snapshot=json.loads(checked(root,candidate['membership_snapshot']).read_bytes())
    source=snapshot['memberships'];day=candidate['accepted_trade_date']
    fact_key=digest(canonical(dict(contract_id=CONTRACT,T0=day,source=source,membership_snapshot=candidate['membership_snapshot'])))
    from workbench_analysis.r43_operational_publication import rows
    content=rows(root,source);descriptor=append(root,fact_key,day,'reference_memberships',source,content)
    if canonical(read_fact(root,descriptor,fact_key,day,'reference_memberships',source))!=canonical(content):raise ValueError('MEMBERSHIP_REFERENCE_FULL_PG_PAYLOAD_DIFFERENCE')
    metadata_fields=('membership_mode','taxonomy','membership_snapshot_id','membership_observed_at','member_set_asof',
        'knowledge_lineage','AS_RECORDED','PIT_ELIGIBLE','HISTORICAL_FIRST_AVAILABLE_PROVEN',
        'production_eligible_scope','survivorship_bias_risk')
    snapshot_metadata={key:snapshot[key] for key in metadata_fields}
    authority=dict(contract_id=CONTRACT,T0=day,membership_snapshot=candidate['membership_snapshot'],source=source,
        identity_source=snapshot.get('identity_source'),membership_snapshot_id=snapshot.get('membership_snapshot_id'),
        snapshot_metadata=snapshot_metadata,descriptor=descriptor,fact_token=fact_key,rows=len(content),AS_RECORDED=False,PIT_ELIGIBLE=False)
    candidate[KEY]=_persist_authority(root,authority)
    return dict(contract_id=CONTRACT,T0=day,rows=len(content),publication=False)

def read(root,candidate,*,workspace_root=None):
    authority=_load_authority(root,candidate)
    if authority.get('contract_id')!=CONTRACT or authority.get('T0')!=candidate['accepted_trade_date'] or authority.get('membership_snapshot')!=candidate['membership_snapshot']:
        raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_SCOPE_MISMATCH')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED')):raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_PIT_ESCALATION')
    content=read_fact(root,authority['descriptor'],authority['fact_token'],authority['T0'],'reference_memberships',authority['source'],
        workspace_root=workspace_root)
    if len(content)!=authority['rows']:raise ValueError('NATIVE_MEMBERSHIP_REFERENCE_ROW_DENOMINATOR')
    return content


def context_metadata(root,candidate):
    """Return dated membership context metadata from the Head-bound PG authority."""
    authority=_load_authority(root,candidate)
    if (authority.get('contract_id')!=CONTRACT or authority.get('T0')!=candidate['accepted_trade_date']
            or authority.get('membership_snapshot')!=candidate['membership_snapshot']
            or authority.get('membership_snapshot_id')!=candidate.get('membership_snapshot_id')):
        raise ValueError('NATIVE_MEMBERSHIP_CONTEXT_SCOPE_MISMATCH')
    metadata=authority.get('snapshot_metadata')
    required={'membership_mode','taxonomy','membership_snapshot_id','membership_observed_at','member_set_asof',
        'knowledge_lineage','AS_RECORDED','PIT_ELIGIBLE','HISTORICAL_FIRST_AVAILABLE_PROVEN',
        'production_eligible_scope','survivorship_bias_risk'}
    if not isinstance(metadata,dict) or set(metadata)!=required:
        raise ValueError('NATIVE_MEMBERSHIP_CONTEXT_METADATA_REQUIRED')
    if (metadata.get('membership_snapshot_id')!=candidate.get('membership_snapshot_id')
            or metadata.get('AS_RECORDED') is not False or metadata.get('PIT_ELIGIBLE') is not False
            or authority.get('AS_RECORDED') is not False or authority.get('PIT_ELIGIBLE') is not False):
        raise ValueError('NATIVE_MEMBERSHIP_CONTEXT_LINEAGE_MISMATCH')
    return metadata


def current_identity_binding(root,candidate):
    day=candidate['accepted_trade_date'];lifecycle=candidate['owners'][day]['lifecycle']
    document=json.loads(checked(root,lifecycle).read_bytes())
    if document.get('trade_date',document.get('target_session',day))!=day:raise ValueError('CURRENT_IDENTITY_LIFECYCLE_DATE_MISMATCH')
    source=document['identity'];checked(root,source)
    return source,lifecycle


def identity_source(root,candidate):
    authority=_load_authority(root,candidate)
    entry=authority.get('current_identity')
    if entry:
        lifecycle=candidate.get('owners',{}).get(authority['T0'],{}).get('lifecycle')
        if entry.get('source_type')!='CURRENT_LIFECYCLE_IDENTITY_R1' or entry.get('lifecycle')!=lifecycle:
            raise ValueError('CURRENT_IDENTITY_REFERENCE_SOURCE_MISMATCH')
        return entry['source']
    source=authority.get('identity_source')
    if not isinstance(source,dict):raise ValueError('NATIVE_IDENTITY_SOURCE_BINDING_REQUIRED')
    return source

def prepare_identity(root,candidate):
    """Extend an existing immutable reference without rebuilding memberships."""
    root=Path(root).resolve();authority=_load_authority(root,candidate)
    if authority['T0']!=candidate['accepted_trade_date'] or authority['membership_snapshot']!=candidate['membership_snapshot']:
        raise ValueError('NATIVE_REFERENCE_EXTENSION_SCOPE_MISMATCH')
    source=authority.get('identity_source');day=authority['T0']
    if not isinstance(source,dict):raise ValueError('NATIVE_IDENTITY_SOURCE_BINDING_REQUIRED')
    fact_key=digest(canonical(dict(contract_id=CONTRACT,domain='identity',T0=day,source=source,membership_snapshot=candidate['membership_snapshot'])))
    from workbench_analysis.r43_operational_publication import rows
    content=rows(root,source);descriptor=append(root,fact_key,day,'reference_identity',source,content)
    if canonical(read_fact(root,descriptor,fact_key,day,'reference_identity',source))!=canonical(content):raise ValueError('IDENTITY_REFERENCE_FULL_PG_PAYLOAD_DIFFERENCE')
    authority['identity']=dict(source=source,descriptor=descriptor,fact_token=fact_key,rows=len(content))
    current,lifecycle=current_identity_binding(root,candidate)
    current_content=rows(root,current)
    prior={r['security_id']:r for r in content};now={r['security_id']:r for r in current_content}
    if len(now)!=len(current_content) or any(now.get(sid)!=row for sid,row in prior.items()):raise ValueError('CURRENT_IDENTITY_PREDECESSOR_CHANGED')
    current_token=digest(canonical(dict(contract_id=CONTRACT,domain='current_identity',T0=day,source=current,lifecycle=lifecycle)))
    current_descriptor=append(root,current_token,day,'reference_current_identity',current,current_content)
    if canonical(read_fact(root,current_descriptor,current_token,day,'reference_current_identity',current))!=canonical(current_content):raise ValueError('CURRENT_IDENTITY_FULL_PG_PAYLOAD_DIFFERENCE')
    authority['current_identity']=dict(source_type='CURRENT_LIFECYCLE_IDENTITY_R1',source=current,lifecycle=lifecycle,descriptor=current_descriptor,fact_token=current_token,rows=len(current_content))
    candidate[KEY]=_persist_authority(root,authority)
    return dict(contract_id=CONTRACT,domain='identity',rows=len(content),membership_fact_recomputed=False,publication=False)

def read_identity(root,candidate,*,workspace_root=None):
    authority=_load_authority(root,candidate)
    if authority.get('contract_id')!=CONTRACT or authority.get('T0')!=candidate['accepted_trade_date'] or authority.get('membership_snapshot')!=candidate['membership_snapshot']:
        raise ValueError('NATIVE_IDENTITY_REFERENCE_SCOPE_MISMATCH')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED')):raise ValueError('NATIVE_REFERENCE_PIT_ESCALATION')
    entry=authority.get('identity')
    if entry is None:raise ValueError('NATIVE_IDENTITY_REFERENCE_REQUIRED_NO_FALLBACK')
    if entry['source']!=authority.get('identity_source'):raise ValueError('NATIVE_IDENTITY_REFERENCE_SOURCE_MISMATCH')
    content=read_fact(root,entry['descriptor'],entry['fact_token'],authority['T0'],'reference_identity',entry['source'],
        workspace_root=workspace_root)
    if len(content)!=entry['rows']:raise ValueError('NATIVE_IDENTITY_REFERENCE_ROW_DENOMINATOR')
    current=authority.get('current_identity')
    if current:
        source=identity_source(root,candidate)
        current_content=read_fact(root,current['descriptor'],current['fact_token'],authority['T0'],'reference_current_identity',source,
            workspace_root=workspace_root)
        now={r['security_id']:r for r in current_content}
        if len(current_content)!=current['rows'] or len(now)!=len(current_content) or any(now.get(r['security_id'])!=r for r in content):raise ValueError('CURRENT_IDENTITY_PREDECESSOR_CHANGED')
        return current_content
    return content

def prepare_search_identity(root,candidate):
    """Copy the candidate's verified PG identity Owner into search authority."""
    root=Path(root).resolve();authority=_load_authority(root,candidate)
    day=candidate['accepted_trade_date']
    if authority.get('T0')!=day:raise ValueError('NATIVE_SEARCH_IDENTITY_AUTHORITY_T0_MISMATCH')
    source=identity_source(root,candidate)
    content=read_identity(root,candidate)
    if not isinstance(source,dict) or not isinstance(content,list) or not content:
        raise ValueError('NATIVE_SEARCH_IDENTITY_PG_OWNER_REQUIRED_NO_FILE_FALLBACK')
    fact_key=digest(canonical(dict(contract_id=CONTRACT,domain='search_identity',T0=day,source=source)))
    descriptor=append(root,fact_key,day,'reference_search_identity',source,content)
    if canonical(read_fact(root,descriptor,fact_key,day,'reference_search_identity',source))!=canonical(content):raise ValueError('SEARCH_IDENTITY_FULL_PG_PAYLOAD_DIFFERENCE')
    authority['search_identity']=dict(source=source,descriptor=descriptor,fact_token=fact_key,rows=len(content))
    candidate[KEY]=_persist_authority(root,authority)
    return dict(contract_id=CONTRACT,domain='search_identity',rows=len(content),prior_reference_facts_recomputed=False,publication=False)

def read_search_identity(root,candidate,*,workspace_root=None):
    authority=_load_authority(root,candidate)
    if authority.get('contract_id')!=CONTRACT or authority.get('T0')!=candidate['accepted_trade_date'] or authority.get('membership_snapshot')!=candidate['membership_snapshot']:
        raise ValueError('NATIVE_SEARCH_IDENTITY_SCOPE_MISMATCH')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED')):raise ValueError('NATIVE_REFERENCE_PIT_ESCALATION')
    entry=authority.get('search_identity')
    if entry is None:raise ValueError('NATIVE_SEARCH_IDENTITY_REQUIRED_NO_FALLBACK')
    content=read_fact(root,entry['descriptor'],entry['fact_token'],authority['T0'],'reference_search_identity',entry['source'],
        workspace_root=workspace_root)
    if len(content)!=entry['rows']:raise ValueError('NATIVE_SEARCH_IDENTITY_ROW_DENOMINATOR')
    return content,entry['source']

def prepare_research(root,candidate,input_candidate,index):
    """Store already frozen research sidecars; never recalculate their facts."""
    root=Path(root);authority=_load_authority(root,candidate);day=candidate['accepted_trade_date']
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
        fact_key=digest(canonical(dict(contract_id=CONTRACT,domain='research_'+name,T0=day,source=source)))
        descriptor=append(root,fact_key,day,'reference_research_'+name,source,content)
        if canonical(read_fact(root,descriptor,fact_key,day,'reference_research_'+name,source))!=canonical(content):raise ValueError('NATIVE_RESEARCH_FULL_PAYLOAD_DIFFERENCE')
        documents[name]=dict(source=source,descriptor=descriptor,fact_token=fact_key)
    authority['research']=dict(input_candidate=input_candidate,T0=day,documents=documents,
        source_owner_bindings={name:candidate.get(name) for name in ('owners','source_registry','day_receipt','exact_daily_generation_scope','membership_snapshot')})
    candidate[KEY]=_persist_authority(root,authority)
    return dict(documents=sorted(documents),numeric_producers_reexecuted=False,publication=False)

def research_authority(root,candidate,day):
    authority=_load_authority(root,candidate)
    if authority.get('contract_id')!=CONTRACT or authority.get('T0')!=candidate['accepted_trade_date'] or authority.get('membership_snapshot')!=candidate['membership_snapshot']:
        raise ValueError('NATIVE_RESEARCH_AUTHORITY_SCOPE_MISMATCH')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED')):raise ValueError('NATIVE_REFERENCE_PIT_ESCALATION')
    research=authority.get('research')
    if not research or research['T0']!=day:raise ValueError('NATIVE_RESEARCH_DATED_AUTHORITY_REQUIRED')
    for name,value in research.get('source_owner_bindings',{}).items():
        if value!=candidate.get(name):raise ValueError('NATIVE_RESEARCH_OWNER_CONSERVATION_REQUIRED:'+name)
    return research

def read_research(root,candidate,day,source):
    research=research_authority(root,candidate,day)
    matches=[(name,entry) for name,entry in research['documents'].items() if entry['source']==source]
    if len(matches)!=1:raise ValueError('NATIVE_RESEARCH_SOURCE_NOT_BOUND_NO_FALLBACK')
    name,entry=matches[0]
    return read_fact(root,entry['descriptor'],entry['fact_token'],day,'reference_research_'+name,source)
