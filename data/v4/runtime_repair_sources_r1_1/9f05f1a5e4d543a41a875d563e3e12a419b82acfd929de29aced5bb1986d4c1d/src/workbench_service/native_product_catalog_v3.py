"""Head embedded dated PG read catalogue with explicit immutable fact tokens."""
import json
from workbench_db.v4_forward_pg_r1 import canonical,digest
from workbench_analysis.r43_owner_replay import checked

KEY='native_product_read_authority'
CONTRACT='V4_HEAD_EMBEDDED_PRODUCT_READ_CATALOG_V3'

def load(root,candidate):
    binding=candidate.get(KEY)
    if binding is None:raise ValueError('EMBEDDED_PRODUCT_CATALOG_REQUIRED_NO_FALLBACK')
    authority=json.loads(checked(root,binding).read_bytes())
    if authority.get('contract_id')!=CONTRACT:raise ValueError('EMBEDDED_PRODUCT_CATALOG_CONTRACT_REQUIRED')
    if authority.get('source_owners')!=candidate['owners'] or authority.get('owner_source_digest')!=digest(canonical(candidate['owners'])):
        raise ValueError('EMBEDDED_PRODUCT_CATALOG_SOURCE_MISMATCH')
    if set(authority.get('dates',{}))!=set(candidate['published_sessions']):raise ValueError('EMBEDDED_PRODUCT_CATALOG_DATE_DENOMINATOR')
    if any(authority.get(k) is not False for k in ('PIT_ELIGIBLE','AS_RECORDED','historical_PIT_permission')):raise ValueError('EMBEDDED_PRODUCT_CATALOG_PIT_ESCALATION')
    for day,entry in authority['dates'].items():
        manifest=json.loads(checked(root,entry).read_bytes())
        if manifest.get('T0')!=day:raise ValueError('EMBEDDED_PRODUCT_CATALOG_MANIFEST_DATE')
        fact_token=manifest.get('fact_token')
        if not isinstance(fact_token,str) or len(fact_token)!=64:raise ValueError('EMBEDDED_PRODUCT_CATALOG_FACT_TOKEN')
        if (manifest['history_index'].get('T0'),manifest['history_index'].get('head_token'))!=(day,fact_token):
            raise ValueError('EMBEDDED_PRODUCT_CATALOG_HISTORY_SCOPE')
        for name,binding in manifest.get('source_bindings',{}).items():
            checked(root,binding)
            if name in candidate['owners'][day] and binding!=candidate['owners'][day][name]:raise ValueError('EMBEDDED_PRODUCT_CATALOG_OWNER_SCOPE')
    return authority
