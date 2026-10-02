"""Out-of-band R5 D2 authority resolver; no raw/calculation fallback."""
from .confirmation import digest

FIELDS=('SEED','PREWATCH','core_price_damage','risk','delta3','suspended','CONFIRMED','scenario')

def tri(value):return 'UNKNOWN' if value is None else 'TRUE' if value is True else 'FALSE' if value is False else value

def resolve_sources(config,bound,policy):
    seal=bound(config['r5a_seal'])
    if seal.get('status')!='V4_11_R5A_OWNER_INPUT_AUTHORITY_PARITY_CANDIDATE_READY' or seal.get('sealed') is not True or seal.get('accepted') is not False:
        raise ValueError('R5A_SEALED_OWNER_AUTHORITY_REQUIRED')
    bound(seal['contract']);parity=bound(seal['parity']);oracle=bound(seal['independent_oracle'])
    if parity['status']!='PASS' or oracle['status']!='PASS' or oracle['formal_t_minus_1_known_count']:
        raise ValueError('R5A_OWNER_PARITY_OR_ORACLE_NOT_PASS')
    r4a=bound(config['r4a_seal']);r3b=bound(config['r3b_seal'])
    result={}
    for day,refs in config['authoritative_by_date'].items():
        if refs['owners']!=seal['publications'][day]:raise ValueError('R5_OWNER_PUBLICATION_OUTSIDE_SEAL')
        owners=bound(refs['owners']);profiles=bound(owners['profile']);confirmation=bound(refs['confirmation']);statuses=bound(refs['status'])
        # D0 is the frozen external-audited R4 publication, never a new detector.
        if refs['confirmation'] not in config['frozen_R4_D0_publications'].values():raise ValueError('D0_FROZEN_AUTHORITY_REQUIRED')
        if owners['trade_date']!=day or confirmation['trade_date']!=day or statuses['trade_date']!=day:raise ValueError('OWNER_TARGET_DATE_MISMATCH')
        material=dict(owners);pid=material.pop('publication_id')
        if pid!='V4_11_R5A_OWNERS:'+digest(material):raise ValueError('OWNER_PUBLICATION_IDENTITY_MISMATCH')
        px={r['core']['security_id']:r for r in profiles['rows']};cx={r['security_id']:r for r in confirmation['rows']};sx={r['security_id']:r for r in statuses['rows']}
        rows={}
        for owner in owners['rows']:
            sid=owner['security_id'];out={k:v for k,v in owner.items() if k not in ('security_id','trade_date','producer_contract_id','source_output_digest')}
            if digest(out)!=owner['source_output_digest']:raise ValueError('OWNER_OUTPUT_DIGEST_MISMATCH')
            for f in ('close_t_minus_1','ma20_t_minus_1'):
                if owner['seed_facts'][f]!=dict(value=None,reason='ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE'):raise ValueError('UNAUTHORIZED_T_MINUS_1_OWNER_CAPABILITY')
            d0=cx[sid];sr=sx.get(sid,{});status=sr.get('status',sr.get('trading_status'))
            if sr.get('status_conflict') or sr.get('provider_conflicts'):status='UNKNOWN'
            vals=dict(SEED=owner['seed']['base_seed_state'],PREWATCH=owner['prewatch']['raw_qualification'],core_price_damage=tri(owner['seed_facts']['core_price_damage']['value']),risk=px[sid]['core']['states']['core_extension_risk']['value'],delta3=owner['seed_facts']['delta3']['value'],suspended='FALSE' if status=='ACTUAL_TRADED' else 'TRUE' if status=='SUSPENDED' else 'UNKNOWN',CONFIRMED=d0['confirmation_status'],scenario=d0['primary_scenario'] or ('NONE' if d0['confirmation_status']=='FALSE' else 'UNKNOWN'))
            vals={f:'UNKNOWN' if v is None else v for f,v in vals.items()}
            fields={}
            for field,value in vals.items():
                if field in ('CONFIRMED','scenario'):parent=refs['confirmation'];publication=confirmation['publication_id'];output_digest=digest(d0)
                elif field=='suspended':parent=refs['status'];publication=statuses.get('publication_id',statuses.get('logical_digest',parent['sha256']));output_digest=digest(sr)
                else:parent=refs['owners'];publication=owners['publication_id'];output_digest=owner['source_output_digest']
                definition=policy['fields'][field]
                fields[field]=dict(entity_id=sid,trade_date=day,field=field,value=value,quality='UNKNOWN' if value=='UNKNOWN' else 'KNOWN',producer_contract_id=definition['producer_contract_id'],parameter_set_id=definition['producer_parameter_set_id'],publication_id=publication,source_output_digest=output_digest,publication_binding=parent)
            rows[sid]=fields
        result[day]=rows
    return result

def verify_manifest_sources(manifest,authority):
    day=manifest['trade_date'];expected=authority[day]
    if {r['entity_id'] for r in manifest['rows']}!=set(expected):raise ValueError('OWNER_EXACT_UNIVERSE_REQUIRED')
    for row in manifest['rows']:
        for field,source in expected[row['entity_id']].items():
            envelope=row['fields'][field]
            if envelope['value']!=source['value'] or envelope['quality']!=source['quality'] or envelope['source_field_payload'].get('authoritative_source')!=source:
                raise ValueError('D2_INPUT_NOT_FROM_SEALED_OWNER_PUBLICATION:'+field)
