"""Explicit append scope and immutable predecessor state, without new kernels."""
from copy import deepcopy
from collections import Counter
import gzip
import json
from pathlib import Path
from .r43_owner_replay import checked, load, gzrows

CONTRACT = 'V4_OPERATIONAL_INCREMENT_PLAN_V1'


def plan(parent, day, sessions, *, revisions=(), replay_current=False):
    previous = parent['accepted_trade_date']
    if day not in sessions or previous not in sessions:
        raise ValueError('INCREMENT_OFFICIAL_SESSION_REQUIRED')
    if replay_current:
        if day != previous:
            raise ValueError('CURRENT_REPLAY_TARGET_REQUIRED')
        mode = 'FULL_REBUILD'
    else:
        if sessions.index(day) != sessions.index(previous) + 1:
            raise ValueError('OWNER_NEXT_OFFICIAL_SESSION_REQUIRED')
        mode = 'RANGE_REPAIR' if revisions else 'APPEND_DAY'
    published = list(parent.get('published_sessions', parent['dates']))
    if len(published) != len(set(published)) or published != sorted(published):
        raise ValueError('INCREMENT_PUBLISHED_SESSIONS_INVALID')
    if previous not in published or any(d > previous for d in published):
        raise ValueError('INCREMENT_PARENT_CUTOFF_INVALID')
    compute = [day] if mode == 'APPEND_DAY' else sorted(set(published + [day]))
    index = sessions.index(day)
    if index < 5:
        raise ValueError('INCREMENT_ENDPOINT_HISTORY_REQUIRED')
    return dict(contract_id=CONTRACT, mode=mode, target_trade_date=day,
                previous_trade_date=previous, compute_sessions=compute,
                history_dependencies=[sessions[index-k] for k in (1,3,4,5)],
                published_sessions=sorted(set(published+[day])),
                revisions=list(revisions), historical_owners=deepcopy(parent['owners']),
                acceptance='PLANNED_NOT_NUMERICALLY_ACCEPTED')


def assert_old_owners_unchanged(parent, candidate):
    for day, bindings in parent['owners'].items():
        if day != candidate['accepted_trade_date'] and candidate['owners'].get(day) != bindings:
            raise ValueError('INCREMENT_IMMUTABLE_OWNER_CHANGED:'+day)


def verify_history_overlap(cache, saved_rows, *, active_security_ids=None):
    for saved in saved_rows:
        sid=saved['security_id']
        if sid not in cache:
            if active_security_ids is not None and sid not in active_security_ids:continue
            raise ValueError('INCREMENT_PREDECESSOR_HISTORY_MISSING:'+sid)
        dated={str(r[0])[:4]+'-'+str(r[0])[4:6]+'-'+str(r[0])[6:]:r for r in cache[sid][1]}
        for bar in saved['bars']:
            raw=dated.get(bar['trade_date'])
            if raw is None:
                if dated and bar['trade_date']>=min(dated):raise ValueError('RANGE_REPAIR_REQUIRED:SOURCE_HISTORY_REVISION:'+sid+':'+bar['trade_date'])
                continue
            if ([v/100 for v in raw[1:5]]!=bar['raw_ohlc'] or raw[5]!=bar['amount'] or raw[6]!=bar['volume']):
                raise ValueError('RANGE_REPAIR_REQUIRED:SOURCE_HISTORY_REVISION:'+sid+':'+bar['trade_date'])


def predecessor_documents(root, parent):
    """Read accepted references; never copy or rewrite historical Owner artifacts."""
    root = Path(root)
    profiles, sectors = [], []
    for day in parent.get('published_sessions', parent['dates']):
        bindings = parent['owners'][day]
        profile = load(checked(root, bindings['diagnostic']))
        if profile['owner']['trade_date'] != day:
            raise ValueError('INCREMENT_PROFILE_DATE_MISMATCH')
        sector_doc = load(checked(root, bindings['sector_receipt']))
        matches = [r for r in sector_doc['owners'] if r['trade_date'] == day]
        if len(matches) != 1:
            raise ValueError('INCREMENT_SECTOR_DATE_MISMATCH')
        profiles.append(profile)
        sectors.append(matches[0])
    return dict(profiles=profiles, sectors=sectors, accepted_days=deepcopy(parent['owners']))


def sector_history(root, profiles, sectors, dates):
    """Restore the exact nonnumeric driver state saved in predecessor artifacts."""
    history = {}
    for item, sector in zip(profiles, sectors):
        owner = item['owner']; day = owner['trade_date']
        if day not in dates:
            continue
        factors = {r['security_id']:r for r in gzrows(checked(root, owner['core']))}
        prof = {r['security_id']:r for r in gzrows(checked(root, owner['profiles']))}
        raw = {r['security_id']:r for r in gzrows(checked(root, owner['raw']))}
        adjusted = {r['security_id']:r for r in gzrows(checked(root, owner['adjusted']))}
        current = {}
        for sid, f in factors.items():
            fields = {k:dict(value=v.get('value'),quality='ACCEPTED' if v.get('quality_state')=='OBSERVED' else 'UNKNOWN',max_source_date=day) for k,v in f['fields'].items()}
            close=adjusted.get(sid,{}).get('close');ma=f['fields']['ma20']['value']
            for key,value in [('amount',raw.get(sid,{}).get('amount')),('close',close),('close_minus_ma20',close-ma if close is not None and ma is not None else None),('mdd20',prof[sid]['derived_fields'].get('mdd20',{}).get('value'))]:
                fields[key]=dict(value=value,quality='ACCEPTED' if value is not None else 'UNKNOWN',max_source_date=day)
            current[sid]=dict(trade_date=day,fields=fields,price_basis_id=f['price_basis_id'])
        natives=gzrows(checked(root,sector['native']))
        groups={n['sector_id']:list(n['member_ids']) for n in natives}
        for n in natives:
            for field in n['fields'].values():
                if field['value'] is not None:field['quality']='ACCEPTED'
        seeds=gzrows(checked(root,sector['seed']))
        history[day]=dict(current=current,groups=groups,native={n['sector_id']:n for n in natives},
            seed={r['security_id']:True if r['base_seed_state']=='TRUE' else False if r['base_seed_state']=='FALSE' else None for r in seeds},
            rotation={r['sector_id']:r['rotation'] for r in gzrows(checked(root,sector['rotation']))})
    return history


def focus_predecessor(root, accepted_days):
    days={};receipts=[];mainline={}
    for day,bindings in sorted(accepted_days.items()):
        publication=json.loads(gzip.decompress(checked(root,bindings['focus']).read_bytes()))
        rows=publication['rows']
        if any(r['trade_date']!=day for r in rows):raise ValueError('INCREMENT_D2_DATE_MISMATCH')
        days[day]=rows
        calculations=gzrows(checked(root,bindings['prewatch']))
        mainline[day]={r['security_id']:r.get('research_mainline_context') for r in calculations}
        # Derive the compact receipt only from the exact, independently bound PG facts.
        receipt=dict(trade_date=day,rows=len(rows),D2=bindings['focus'],calculations=bindings['prewatch'],
            D0=dict(Counter(r['confirmation']['confirmation_status'] for r in calculations)),
            PREWATCH=dict(Counter(r['prewatch']['raw_qualification'] for r in calculations)),
            D2_freshness=dict(Counter(r['state_freshness'] for r in rows)),
            contract_id='V4_ACCEPTED_FOCUS_REFERENCE_RECEIPT_R1')
        receipts.append(dict(receipt,reused=True,publication_id=publication['publication_id']))
    last=max(accepted_days)
    projection=json.loads(gzip.decompress(checked(root,accepted_days[last]['forward']).read_bytes()))
    bindings=projection['source_bindings']
    # Stream the prior immutable PG series once, preserving every saved bar byte.
    from workbench_db.v4_series_pg_r1 import verified_series_read
    descriptor=load(checked(root,bindings['series']));allbars={}
    with verified_series_read(descriptor) as db:
        for sid,day,payload in db.execute('SELECT security,day::text,payload FROM bars ORDER BY security,day').fetchall():
            if day>last:raise ValueError('INCREMENT_FOCUS_FUTURE_BAR')
            allbars[(sid,day)]=json.loads(payload)
    return dict(days=days,receipts=receipts,mainline_context=mainline,allbars=allbars,
        pathstatus=deepcopy(bindings['status']),native=deepcopy(bindings['native_core']),
        prior={r['entity_id']:r for r in days[last]},prior_pid=receipts[-1]['publication_id'])
