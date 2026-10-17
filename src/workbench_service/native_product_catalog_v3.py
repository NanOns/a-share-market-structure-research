"""Head embedded dated PG read catalogue with explicit immutable fact tokens."""
import json
from workbench_db.v4_forward_pg_r1 import canonical,digest
from workbench_analysis.r43_owner_replay import checked

KEY='native_product_read_authority'
PG_KEY='native_product_read_authority_pg'
CONTRACT='V4_HEAD_EMBEDDED_PRODUCT_READ_CATALOG_V3'
PG_CONTRACT='V4_HEAD_EMBEDDED_PRODUCT_READ_CATALOG_PG_R1'
MANIFEST_DOMAIN='product_manifest'
SCOPE_DOMAIN='product_manifest_scope'


def _fact_token(day, kind, source_binding, owner_source_digest):
    return digest(canonical(dict(contract_id=PG_CONTRACT, T0=day, kind=kind,
        source_binding=source_binding, owner_source_digest=owner_source_digest)))


def prepare_pg(root, candidate, authority):
    """Copy dated product manifests and their exact Head scopes into PG facts."""
    from workbench_db.v4_operational_owner_pg_closeout import prepare as append, read as read_fact

    owner_digest=digest(canonical(candidate['owners']))
    if (authority.get('contract_id')!=CONTRACT or authority.get('source_owners')!=candidate['owners']
            or authority.get('owner_source_digest')!=owner_digest
            or set(authority.get('dates',{}))!=set(candidate['published_sessions'])
            or any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED','historical_PIT_permission'))):
        raise ValueError('PRODUCT_CATALOG_SOURCE_SCOPE_MISMATCH')
    entries={}
    for day,binding in authority['dates'].items():
        manifest=json.loads(checked(root,binding).read_bytes())
        if manifest.get('T0')!=day:raise ValueError('PRODUCT_CATALOG_MANIFEST_DATE_MISMATCH')
        # The legacy Focus projection was produced into a local snapshot even
        # though its contract called it PG. Re-ingest that exact, digest-bound
        # source once into the operational Owner relation before the manifest
        # itself is sealed into the Head-bound catalogue.
        if manifest.get('contract_id')=='CORE_PRODUCT_FOCUS_READ_MANIFEST_R2':
            from workbench_db.v4_focus_projection_pg_closeout import build as build_focus_pg
            projection_binding=manifest.get('projection')
            scope_binding=manifest.get('head')
            if not isinstance(scope_binding,dict) or not isinstance(scope_binding.get('sha256'),str):
                raise ValueError('FOCUS_PG_PROJECTION_HEAD_SCOPE_REQUIRED')
            focus_binding,focus_receipt=build_focus_pg(
                root,projection_binding,t0=day,head_token=scope_binding['sha256'])
            if focus_receipt.get('whole_payload_difference')!=0:
                raise ValueError('FOCUS_PG_PROJECTION_FULL_READBACK_REQUIRED')
            manifest=dict(manifest,contract_id='CORE_PRODUCT_FOCUS_READ_MANIFEST_R3_NATIVE_PG',
                          projection=focus_binding,
                          projection_source=projection_binding,
                          projection_pg_receipt=focus_receipt)
        for name,source in manifest.get('source_bindings',{}).items():
            if name in candidate['owners'][day] and source!=candidate['owners'][day][name]:
                raise ValueError('PRODUCT_CATALOG_MANIFEST_OWNER_MISMATCH')
        scope_binding=manifest['head']
        scope=json.loads(checked(root,scope_binding).read_bytes())
        facts={}
        for kind,source_binding,value,domain in (
                ('manifest',binding,manifest,MANIFEST_DOMAIN),
                ('scope',scope_binding,scope,SCOPE_DOMAIN)):
            fact_token=_fact_token(day,kind,source_binding,owner_digest)
            descriptor=append(root,fact_token,day,domain,source_binding,[value])
            if read_fact(root,descriptor,fact_token,day,domain,source_binding)!=[value]:
                raise ValueError('PRODUCT_CATALOG_PG_PAYLOAD_DIFFERENCE:'+kind)
            facts[kind]=dict(source_binding=source_binding,fact_token=fact_token,descriptor=descriptor)
        entries[day]=facts
    candidate[PG_KEY]=dict(contract_id=PG_CONTRACT,T0=candidate['accepted_trade_date'],
        owner_source_digest=owner_digest,
        catalog_source_binding=candidate[KEY],dates=entries,PIT_ELIGIBLE=False,
        AS_RECORDED=False,historical_PIT_permission=False)
    return dict(contract_id=PG_CONTRACT,dates=len(entries),publication=False)


def _load_pg(root,candidate):
    authority=candidate[PG_KEY]
    if (authority.get('contract_id')!=PG_CONTRACT or authority.get('T0')!=candidate.get('accepted_trade_date')
            or authority.get('owner_source_digest')!=digest(canonical(candidate['owners']))
            or authority.get('catalog_source_binding')!=candidate.get(KEY)
            or set(authority.get('dates',{}))!=set(candidate['published_sessions'])
            or any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED','historical_PIT_permission'))):
        raise ValueError('EMBEDDED_PRODUCT_PG_CATALOG_SCOPE_MISMATCH')
    from workbench_db.v4_operational_owner_pg_closeout import read as read_fact
    manifests={};scopes={}
    for day,facts in authority['dates'].items():
        for kind,domain,target in (('manifest',MANIFEST_DOMAIN,manifests),('scope',SCOPE_DOMAIN,scopes)):
            fact=facts.get(kind)
            if not isinstance(fact,dict) or fact.get('fact_token')!=_fact_token(day,kind,fact.get('source_binding'),authority['owner_source_digest']):
                raise ValueError('EMBEDDED_PRODUCT_PG_FACT_TOKEN_MISMATCH')
            rows=read_fact(root,fact['descriptor'],fact['fact_token'],day,domain,fact['source_binding'])
            if not isinstance(rows,list) or len(rows)!=1 or not isinstance(rows[0],dict):
                raise ValueError('EMBEDDED_PRODUCT_PG_FACT_SHAPE_INVALID')
            target[day]=rows[0]
        manifest=manifests[day]
        if manifest.get('T0')!=day or manifest.get('head')!=facts['scope']['source_binding']:
            raise ValueError('EMBEDDED_PRODUCT_PG_MANIFEST_SCOPE_MISMATCH')
        if (manifest.get('fact_token')!=manifest.get('history_index',{}).get('head_token')
                or manifest.get('history_index',{}).get('T0')!=day):
            raise ValueError('EMBEDDED_PRODUCT_PG_HISTORY_SCOPE_MISMATCH')
        for name,binding in manifest.get('source_bindings',{}).items():
            if name in candidate['owners'][day] and binding!=candidate['owners'][day][name]:
                raise ValueError('EMBEDDED_PRODUCT_PG_OWNER_SCOPE_MISMATCH')
    return dict(authority,dates=manifests,scopes=scopes)

def load(root,candidate):
    if PG_KEY not in candidate:
        raise ValueError('EMBEDDED_PRODUCT_PG_CATALOG_REQUIRED_NO_FILE_FALLBACK')
    return _load_pg(root,candidate)
