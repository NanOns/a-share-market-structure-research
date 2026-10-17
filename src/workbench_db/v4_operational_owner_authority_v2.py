"""Immutable Owner authority embedded in one Head, without circular tokens.

HTTP uses the full accepted Head fact_key. Stored facts bind exact dated source
owners; their immutable fact fact_key can be reused across successive Heads.
This module prepares candidates only and never moves an accepted pointer.
"""
import json
from pathlib import Path
from .v4_forward_pg_r1 import ForwardFactStore,canonical,digest
from .v4_operational_owner_pg_closeout import prepare as append,read as read_fact,read_authority_manifest,attest_cached,descriptor_metadata,inline_descriptor,OWNER,FOLDER
from workbench_analysis.r43_owner_replay import checked

CONTRACT='V4_HEAD_EMBEDDED_NATIVE_PG_OWNER_AUTHORITY_V2'
KEY='native_pg_owner_authority'

def prepare_successor(root,candidate,*,predecessor_authority_binding=None):
    """Append dated facts and bind their authority before the single Head CAS."""
    root=Path(root).resolve()
    predecessor=json.loads(checked(root,candidate['predecessor']).read_bytes())
    if KEY in predecessor:
        prior=load(root,predecessor)
    else:
        from .v4_operational_owner_pg_closeout import load_authority
        prior=load_authority(root,predecessor,candidate['predecessor']['sha256'],
                             authority_binding=predecessor_authority_binding)
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

def attest(root,authority,day,domain,source_binding,*,workspace_root=None):
    if authority['source_owners'].get(day,{}).get(domain)!=source_binding:
        raise ValueError('PG_OWNER_EMBEDDED_READ_SOURCE_MISMATCH')
    attest_cached(root,authority['owners'][day][domain]['descriptor'],domain,source_binding,
        workspace_root=workspace_root)

def prepare(root,candidate,predecessor=None):
    root=Path(root).resolve();owners={};counts=dict(reused=0,created=0)
    if predecessor and predecessor.get('contract_id') not in (CONTRACT,OWNER):
        raise ValueError('PG_OWNER_PREDECESSOR_CONTRACT_REQUIRED')
    from workbench_analysis.r43_operational_publication import rows
    for day,domains in candidate['owners'].items():
        owners[day]={}
        for domain,binding in domains.items():
            checked(root,binding)
            if predecessor and predecessor['source_owners'].get(day,{}).get(domain)==binding:
                old=predecessor['owners'][day][domain]
                entry=old if predecessor['contract_id']==CONTRACT else dict(descriptor=old,fact_token=predecessor['head_token'])
                # Read validates live cluster, whole payload SHA, exact date,
                # domain, source binding and original fact fact_key before reuse.
                read_fact(root,entry['descriptor'],entry['fact_token'],day,domain,binding)
                counts['reused']+=1
            else:
                fact_key=digest(canonical(dict(contract_id=CONTRACT,T0=day,domain=domain,source_binding=binding)))
                content=rows(root,binding)
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
