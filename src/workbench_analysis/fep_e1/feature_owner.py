"""FEP_FEATURE_OWNER_V1: exact accepted V4-03 envelopes, no factor formulas.

Historical owner values support reconstruction engineering only. Field presence
and value availability are distinct; UNKNOWN envelopes remain represented.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path

from .contracts import digest, exact

CONTRACT = 'FEP_FEATURE_OWNER_V1'


def verify_file(root, binding):
    root = Path(root).resolve()
    path = (root / binding['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('FEP_OWNER_PATH_ESCAPE')
    sha = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            sha.update(chunk)
            size += len(chunk)
    if size != binding['bytes'] or sha.hexdigest() != binding['sha256']:
        raise ValueError('FEP_OWNER_EXACT_BYTES_MISMATCH')
    return path


def validate_contract(root, contract):
    if contract['contract_id'] != CONTRACT or contract['evidence_origin'] != 'RECONSTRUCTED_ASOF':
        raise ValueError('FEP_OWNER_ENGINEERING_CONTRACT_REQUIRED')
    if any(contract[k] is not False for k in ('AS_RECORDED','FIRST_OBSERVED','production','shadow')):
        raise ValueError('FEP_OWNER_REAL_PERMISSION_FORBIDDEN')
    head = exact(root, contract['owner_head'])
    if head['external_acceptance'] != 'EXTERNALLY_ACCEPTED' or any(
            head['capabilities'][k] != 'PASS' for k in ('STOCK_CORE','RELATIVE_RPS','MARKET_REFERENCE','MARKET_REGIME')):
        raise ValueError('FEP_OWNER_CAPABILITY_NOT_ACCEPTED')
    receipt = exact(root, contract['owner_receipt'])
    if not any(ref['path'] == contract['owner_receipt']['path'] and ref['sha256'] == contract['owner_receipt']['sha256']
               for ref in head['evidence_bindings'].values()):
        raise ValueError('FEP_OWNER_RECEIPT_NOT_ACCEPTED_BY_HEAD')
    artifact = contract['owner_artifact']
    if receipt['hashes']['artifacts'].get(artifact['path']) != artifact['sha256']:
        raise ValueError('FEP_OWNER_ARTIFACT_NOT_ACCEPTED')
    registry = exact(root, contract['field_registry'])
    schema = exact(root, contract['output_schema'])
    exact(root, contract['algorithm_contract'])
    exact(root, contract['parameter_contract'])
    for key in ('output_schema','algorithm_contract','parameter_contract'):
        ref=contract[key]
        expected=receipt['hashes']['contracts'].get(ref['path'])
        if expected != ref['sha256']:
            raise ValueError('FEP_OWNER_CONTRACT_NOT_ACCEPTED')
    names=[f['field_name'] for f in contract['fields']]
    if (len(names)!=47 or len(set(names))!=47 or set(names)!={f['field_id'] for f in registry['fields']}
            or set(names)!={f['field_id'] for f in schema['fields']}):
        raise ValueError('FEP_OWNER_47_FIELD_CONTRACT_REQUIRED')
    fields={f['field_id']:f for f in schema['fields']}
    registry_fields={f['field_id']:f for f in registry['fields']}
    for mapping in contract['fields']:
        name=mapping['field_name']; output=fields[name]
        if (mapping['value_path']!=['fields',name,'value']
                or mapping['quality_path']!=['fields',name,'quality_state']
                or mapping['source_digest_path']!=['fields',name,'output_digest']
                or mapping['window_identity_path']!=['fields',name,'window_identity']
                or mapping['unit']!=output['unit'] or mapping['data_type']!=output['type']
                or registry_fields[name]['unit']!=output['unit'] or registry_fields[name]['data_type']!=output['type']
                or mapping['nullable']!=output['nullable'] or mapping['required'] is not True):
            raise ValueError('FEP_OWNER_ALIAS_OR_SCHEMA_MISMATCH')
        if (mapping['owner_head']!=contract['owner_head'] or mapping['owner_artifact']!=contract['owner_artifact']
                or mapping['trade_date']!=contract['trade_date']
                or mapping['owner_publication_identity']['receipt']!=contract['owner_receipt']):
            raise ValueError('FEP_OWNER_FIELD_LINEAGE_MISMATCH')
    for key in ('calendar','universe','adjustment_identity'):
        ref=contract[key]
        if receipt['hashes']['source'].get(ref['path']) != ref['sha256']:
            raise ValueError('FEP_OWNER_UPSTREAM_NOT_ACCEPTED')
        verify_file(root,ref)
    return fields


def project_row(row, contract):
    names={f['field_name'] for f in contract['fields']}
    if set(row['fields']) != names or row['trade_date'] != contract['trade_date']:
        raise ValueError('FEP_OWNER_ROW_SCOPE_OR_FIELD_INVENTORY_MISMATCH')
    values={}
    for mapping in contract['fields']:
        name=mapping['field_name']; envelope=row['fields'][name]
        value=envelope['value']; quality=envelope['quality_state']
        if quality not in ('OBSERVED','UNKNOWN'):
            raise ValueError('FEP_OWNER_QUALITY_NOT_REGISTERED')
        if value is None and (not mapping['nullable'] or quality!='UNKNOWN' or not envelope.get('unknown_reason')):
            raise ValueError('FEP_OWNER_UNKNOWN_ENVELOPE_INCOMPLETE')
        if value is not None and quality != 'OBSERVED':
            raise ValueError('FEP_OWNER_VALUE_QUALITY_MISMATCH')
        dtype=mapping['data_type']
        if value is not None and ((dtype=='float64' and type(value) not in (int,float))
                                  or (dtype=='boolean' and type(value) is not bool)):
            raise ValueError('FEP_OWNER_VALUE_TYPE_MISMATCH')
        if isinstance(value,float) and not math.isfinite(value):
            raise ValueError('FEP_OWNER_NONFINITE_VALUE')
        for key in ('output_digest','input_digest','window_identity','contract_id','parameter_set_id'):
            if not envelope.get(key):
                raise ValueError('FEP_OWNER_ENVELOPE_IDENTITY_MISSING')
        values[name]=dict(value=value,quality=quality,unknown_reason=envelope.get('unknown_reason'),
                          source_digest=envelope['output_digest'],input_digest=envelope['input_digest'],
                          window_identity=envelope['window_identity'],unit=mapping['unit'],
                          producer_contract_id=envelope['contract_id'],parameter_set_id=envelope['parameter_set_id'])
    return dict(contract_id=CONTRACT,entity_id=row['security_id'],trade_date=row['trade_date'],
                source_row_digest=digest(row),owner_artifact=contract['owner_artifact'],
                owner_head=contract['owner_head'],values=values,source_row=row,
                evidence_origin='RECONSTRUCTED_ASOF',execution_mode='REPLAY',
                AS_RECORDED=False,FIRST_OBSERVED=False,production=False,shadow=False)


def read(root, contract, *, entity_id, trade_date):
    validate_contract(root,contract)
    if trade_date != contract['trade_date']:
        raise ValueError('FEP_OWNER_DATE_MISMATCH')
    path=verify_file(root,contract['owner_artifact'])
    matches=[]
    with gzip.open(path,'rt',encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line)
            if (row['security_id'],row['trade_date']) == (entity_id,trade_date):
                matches.append(row)
    if len(matches)!=1:
        raise ValueError('FEP_OWNER_EXACT_ROW_NOT_UNIQUE')
    verify_file(root,contract['owner_artifact'])
    return project_row(matches[0],contract)
