"""Immutable Owner authority embedded in one Head, without circular tokens.

HTTP uses the full accepted Head fact_key. Stored facts bind exact dated source
owners; their immutable fact fact_key can be reused across successive Heads.
This module prepares candidates only and never moves an accepted pointer.
"""
from pathlib import Path
from io import BytesIO,TextIOWrapper
import gzip,json
from .v4_forward_pg_r1 import ForwardFactStore,canonical,digest
from .v4_operational_owner_pg_closeout import prepare as append,read as read_fact,read_authority_manifest,attest_cached,descriptor_metadata,inline_descriptor,OWNER,FOLDER

CONTRACT='V4_HEAD_EMBEDDED_NATIVE_PG_OWNER_AUTHORITY_V2'
KEY='native_pg_owner_authority'

def _rows_from_source_ingress(root,binding):
    """Ingest an explicitly Head-bound source once, then parse bytes read from PG."""
    from .v4_historical_source_ingress_pg_r1 import read_bound,ingest_file,source_id_for_path
    try:
        source=read_bound(root,binding['path'],binding['sha256'])
    except ValueError as exc:
        if str(exc)!='HISTORICAL_SOURCE_INGRESS_NOT_FOUND':raise
        path=Path(root).resolve()/binding['path']
        ingest_file(root,source_id_for_path(binding['path']),path,expected_sha256=binding['sha256'])
        source=read_bound(root,binding['path'],binding['sha256'])
    if len(source['raw'])!=binding.get('bytes'):
        raise ValueError('PG_OWNER_SOURCE_INGRESS_SIZE_MISMATCH')
    name=Path(binding['path']).name
    raw=source['raw']
    if name.endswith('.gz'):
        with gzip.GzipFile(fileobj=BytesIO(raw),mode='rb') as compressed:
            text=TextIOWrapper(compressed,encoding='utf-8')
            if '.jsonl.' in name:return [json.loads(line) for line in text if line.strip()]
            value=json.load(text)
    elif name.endswith('.jsonl'):
        value=[json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    else:
        value=json.loads(raw)
    if isinstance(value,dict):
        for key in ('rows','target_bars','sectors'):
            if isinstance(value.get(key),list):return value[key]
    return value

def prepare_successor(root,candidate,*,predecessor_authority_binding=None):
    """Append dated facts and bind their authority before the single Head CAS."""
    root=Path(root).resolve()
    # Import the predecessor exactly once through the dedicated PG ingress if
    # this candidate has not already been bound to its PG fact. All subsequent
    # selection and reads use that immutable fact, not the mutable Head path.
    from .v4_operational_predecessor_pg_v1 import KEY as PREDECESSOR_KEY, prepare as prepare_predecessor, read_predecessor
    if PREDECESSOR_KEY not in candidate:
        prepare_predecessor(root,candidate)
    predecessor=read_predecessor(root,candidate)
    if KEY in predecessor:
        prior=load(root,predecessor)
    else:
        # Older operational Heads bind Owner payload files directly and have
        # no separate authority JSON. The Head's exact bindings are the
        # one-time ingress selectors; materialize payloads as PG Owner facts
        # before producing the successor authority manifest.
        legacy_owners=predecessor.get('owners')
        if not isinstance(legacy_owners,dict) or not legacy_owners:
            from .v4_operational_owner_pg_closeout import load_authority
            prior=load_authority(root,predecessor,candidate['predecessor']['sha256'],
                                 authority_binding=predecessor_authority_binding)
        else:
            prior=dict(contract_id=OWNER,source_owners=legacy_owners,owners=legacy_owners)
    binding,receipt=prepare(root,candidate,prior)
    candidate[KEY]=binding
    if KEY not in predecessor:
        receipt["legacy_authority_ingress"] = dict(
            path=predecessor_authority_binding["path"],
            sha256=predecessor_authority_binding["sha256"],
            disposition="EXACT_BOUND_ONE_TIME_INGRESS_THEN_PG_MANIFEST",
        )
    return receipt

def validate(candidate,authority):
    if authority.get('contract_id')!=CONTRACT:raise ValueError('PG_OWNER_EMBEDDED_CONTRACT_REQUIRED')
    if any(authority.get(key) is not False for key in ('historical_PIT_permission','AS_RECORDED','PIT_ELIGIBLE')):
        raise ValueError('PG_OWNER_EMBEDDED_PIT_ESCALATION')
    sources=candidate['owners']
    if authority.get('source_owners')!=sources or authority.get('owner_source_digest')!=digest(canonical(sources)):
        raise ValueError('PG_OWNER_EMBEDDED_SOURCE_MISMATCH')
    if set(authority.get('owners',{}))!=set(sources):raise ValueError('PG_OWNER_EMBEDDED_DATES_INCOMPLETE')
    for day,domains in sources.items():
        if set(authority['owners'][day])!=set(domains):raise ValueError('PG_OWNER_EMBEDDED_DOMAINS_INCOMPLETE')
        for entry in authority['owners'][day].values():
            if set(entry)!={'descriptor','fact_token'} or not isinstance(entry['fact_token'],str) or len(entry['fact_token'])!=64:
                raise ValueError('PG_OWNER_EMBEDDED_FACT_IDENTITY_REQUIRED')
    return authority

def load(root,candidate):
    binding=candidate.get(KEY)
    if binding is None:raise ValueError('PG_OWNER_EMBEDDED_AUTHORITY_REQUIRED_NO_FALLBACK')
    authority=validate(candidate,read_authority_manifest(root,binding))
    for domains in authority['owners'].values():
        for entry in domains.values():descriptor_metadata(root,entry['descriptor'])
    return authority

def read(root,authority,day,domain,source_binding,*,workspace_root=None):
    if authority['source_owners'].get(day,{}).get(domain)!=source_binding:
        raise ValueError('PG_OWNER_EMBEDDED_READ_SOURCE_MISMATCH')
    entry=authority['owners'][day][domain]
    return read_fact(root,entry['descriptor'],entry['fact_token'],day,domain,source_binding,
        workspace_root=workspace_root)

def read_domain(root,candidate,day,domain,*,workspace_root=None):
    """Resolve a typed Owner payload from the candidate's embedded PG authority."""
    binding=candidate.get('owners',{}).get(day,{}).get(domain)
    if not isinstance(binding,dict):raise ValueError('PG_OWNER_DOMAIN_BINDING_REQUIRED:'+domain)
    authority=load(root,candidate)
    return read(root,authority,day,domain,binding,workspace_root=workspace_root)

def attest(root,authority,day,domain,source_binding,*,workspace_root=None):
    if authority['source_owners'].get(day,{}).get(domain)!=source_binding:
        raise ValueError('PG_OWNER_EMBEDDED_READ_SOURCE_MISMATCH')
    attest_cached(root,authority['owners'][day][domain]['descriptor'],domain,source_binding,
        workspace_root=workspace_root)

def prepare(root,candidate,predecessor=None):
    root=Path(root).resolve();owners={};counts=dict(reused=0,created=0)
    if predecessor and predecessor.get('contract_id') not in (CONTRACT,OWNER):
        raise ValueError('PG_OWNER_PREDECESSOR_CONTRACT_REQUIRED')
    for day,domains in candidate['owners'].items():
        owners[day]={}
        for domain,binding in domains.items():
            if predecessor and predecessor['source_owners'].get(day,{}).get(domain)==binding:
                old=predecessor['owners'][day][domain]
                if predecessor['contract_id']==OWNER and isinstance(old,dict) and set(old)=={'path','sha256','bytes'}:
                    # Import legacy Head-bound rows into immutable PG facts;
                    # never treat the old workspace payload as a live Owner.
                    from .v4_operational_owner_pg_closeout import validate_source_binding
                    validate_source_binding(old)
                    content=_rows_from_source_ingress(root,old)
                    fact_key=digest(canonical(dict(contract_id=CONTRACT,T0=day,domain=domain,source_binding=binding)))
                    descriptor=append(root,fact_key,day,domain,binding,content)
                    if canonical(read_fact(root,descriptor,fact_key,day,domain,binding))!=canonical(content):
                        raise ValueError('PG_OWNER_EMBEDDED_FULL_PAYLOAD_DIFFERENCE')
                    owners[day][domain]=dict(descriptor=descriptor,fact_token=fact_key)
                    counts['created']+=1
                    continue
                entry=old if predecessor['contract_id']==CONTRACT else dict(descriptor=old,fact_token=predecessor['head_token'])
                # Read validates live cluster, whole payload SHA, exact date,
                # domain, source binding and original fact fact_key before reuse.
                read_fact(root,entry['descriptor'],entry['fact_token'],day,domain,binding)
                counts['reused']+=1
            else:
                # A new source payload is a deliberate ingress operation. A
                # reused PG Owner only needs its immutable source binding and
                # live PG digest; it must remain readable after workspace files
                # are moved or retired.
                from .v4_operational_owner_pg_closeout import validate_source_binding
                validate_source_binding(binding)
                fact_key=digest(canonical(dict(contract_id=CONTRACT,T0=day,domain=domain,source_binding=binding)))
                content=_rows_from_source_ingress(root,binding)
                descriptor=append(root,fact_key,day,domain,binding,content)
                if canonical(read_fact(root,descriptor,fact_key,day,domain,binding))!=canonical(content):
                    raise ValueError('PG_OWNER_EMBEDDED_FULL_PAYLOAD_DIFFERENCE')
                entry=dict(descriptor=descriptor,fact_token=fact_key);counts['created']+=1
            owners[day][domain]=entry
    authority=dict(contract_id=CONTRACT,owner_source_digest=digest(canonical(candidate['owners'])),
        source_owners=candidate['owners'],owners=owners,historical_PIT_permission=False,AS_RECORDED=False,PIT_ELIGIBLE=False)
    validate(candidate,authority)
    manifest_key=digest(canonical(authority))
    manifest_binding=ForwardFactStore(root,FOLDER).append('authority_manifest',manifest_key,authority)
    manifest_binding=inline_descriptor(root,manifest_binding)
    return manifest_binding,dict(contract_id=CONTRACT,scope='FULL_OWNER_PAYLOAD_READBACK_ONLY',counts=counts,publication=False)
