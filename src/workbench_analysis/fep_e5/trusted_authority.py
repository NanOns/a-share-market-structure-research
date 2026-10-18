"""FEP authority status without querying the retired standalone schema."""

import hashlib
from pathlib import Path

VERSION = 'FEP_CANONICAL_AUTHORITY_READ_R2'
STORAGE_NOT_READY = 'V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'
IDENTITY = ('scope_id','target_id','horizon','feature_contract_id','model_set_id','capability')


def _empty():
    return dict(contract_id=VERSION,status='TRUSTED_AUTHORITY_UNAVAILABLE',production_authorized=False,
        db_facts_status='NOT_VERIFIED',candidate_complete=False,
        formal_owner=None,registry_verified=False,first_asof_verified=False,deployment_head_verified=False,
        cas_receipt_verified=False,independent_approval_verified=False,errors=[],sources={})


def resolve_current_sources(root):
    """Discover real design/engineering artifacts, never implicitly select a DSN."""
    root=Path(root).resolve();result=_empty()
    for relative in ('reports/fep_e5_r1/MODEL_CATALOG.json','config/fep_scope_registry_v1.json',
                     'config/fep_target_registry_v1.json','config/fep_e5_model_evidence_class_v1.json'):
        path=root/relative
        if path.is_file():
            raw=path.read_bytes()
            result['sources'][relative]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                evidence_role='DESIGN_OR_HISTORICAL_ENGINEERING_ONLY')
    result['errors']=['FORMAL_PRODUCTION_DB_OWNER_NOT_ADMITTED',
        'CURRENT_INDEPENDENT_CAPABILITY_APPROVAL_SOURCE_MISSING',
        'MODEL_REVISION_PRODUCTION_REGISTRY_MISSING','AS_RECORDED_MATURE_PREDICTION_OWNER_MISSING']
    return result


def read_canonical_candidate(pg,request,*,at):
    """Fail closed until fixed versioned FEP tables exist under schema v4."""
    result=_empty();result['evidence_trust']='ACTUAL_DB_READ_ENGINEERING_CANDIDATE'
    if any(request.get(k) is None for k in IDENTITY) or type(request.get('model_revision')) is not int or request['model_revision']<=0:
        result['errors']=['EXACT_REQUEST_AND_MODEL_REVISION_REQUIRED'];return result
    if request['capability'] not in ('MODEL_DISPLAY','PRIORITY_USE'):
        result['errors']=['SHADOW_CAPABILITY_CANNOT_AUTHORIZE_PRODUCTION'];return result
    result.update(status='STORAGE_NOT_READY',errors=[STORAGE_NOT_READY],
                  missing_inputs=['V4_FIXED_FEP_TABLE_MIGRATION'])
    return result
