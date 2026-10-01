"""Candidate projection, with explicit reconstructed and synthetic namespaces."""
from datetime import datetime,timezone
from src.v4.confirmation import package,bound,digest

def seal(x):
    x={k:v for k,v in x.items() if k not in ('input_digest','publication_id')}
    checksum=digest(x)
    return dict(x,input_digest=checksum,publication_id='V4_11_INPUT:'+checksum)

def projection(values=None,*,real=False,cutoff=None):
    c,m,p,a,scanner=package();head=bound(c['accepted_data_head']);art=head['component_artifacts']
    refs=[art[k] for k in ('IDENTITY_UNIVERSE','RAW_DAILY','TRADING_STATUS')]
    identity={r['security_id']:r for r in bound(art['IDENTITY_UNIVERSE'])['rows']}
    raw={r['security_id']:r for r in bound(art['RAW_DAILY'])['rows']}
    status={r['security_id']:r for r in bound(art['TRADING_STATUS'])['rows']}
    cutoff=cutoff or datetime.now(timezone.utc).isoformat();rows=[]
    ids=sorted(identity) if real else ['synthetic-entity']
    for sid in ids:
        facts={}
        for field in m['input_fields']:
            role=m['input_time_roles'][field]
            if role=='SAME_DAY_DOWNSTREAM':continue
            cap='IDENTITY_UNIVERSE';quality='UNKNOWN';acceptance='UNAVAILABLE';value=None;reason='TARGET_PRODUCER_FACT_NOT_EXTERNALLY_ACCEPTED'
            if real and field=='actual_bar':
                value=sid in raw;cap='RAW_DAILY' if value else 'TRADING_STATUS';quality='KNOWN';acceptance='EXTERNALLY_ACCEPTED';reason=None
            elif real and field=='input_identity_compatible':
                value=all(identity[sid]['source_security_key']==source[sid]['source_security_key'] for source in (raw,status) if sid in source)
                quality='KNOWN';acceptance='EXTERNALLY_ACCEPTED';reason=None
            elif not real and field in (values or {}):
                value=values[field];quality='KNOWN' if value is not None else 'UNKNOWN';acceptance='ENGINEERING_VECTOR';reason='EXPLICIT_SYNTHETIC_VECTOR' if value is None else None
            facts[field]=dict(value=value,quality=quality,acceptance=acceptance,reason=reason,unit=m['input_units'][field],time_role=role,
                trade_date='2026-09-29' if role=='PRIOR_SESSION_WINDOW' else '2026-09-30',system_available_at=cutoff,source_publication_id=art[cap]['sha256'])
        rows.append(dict(security_id=sid,trade_date='2026-09-30',facts=facts))
    return seal(dict(contract_id='LEGACY_ADAPTER_V1',producer_contract_id=c['input_producer_contract_id'],parameter_set_id=c['input_parameter_set_id'],
        accepted_data_head=c['accepted_data_head'],trade_date='2026-09-30',cutoff_timestamp=cutoff,
        mode='REAL_ACCEPTED_INPUT_CANDIDATE' if real else 'SYNTHETIC_ENGINEERING_VECTOR',source_bindings=refs,
        source_publication_ids=[r['sha256'] for r in refs],rows=rows))

def positive_values():
    _,m,_,_,_=package()
    v={f:True if m['input_units'][f]=='boolean' else 1.0 for f in m['input_fields']}
    v.update(structure_break_v3=False,extended_v3=False,first_day_damage=False,severe_drop=False,intraday_reject_high20=False,
        amr20_mean_prior=1.3,prior5_below_ma20_count=2,clv=.6,rps20=.7,rps5_delta3=.01,ret1_adj=.01)
    return v
