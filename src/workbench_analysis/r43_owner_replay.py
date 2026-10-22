"""R4.1 corrected-source producer, preserving frozen kernels and live pointers."""
from __future__ import annotations
import bisect
import gzip
import hashlib
import json
import os
import struct
import zipfile
from collections import Counter, defaultdict, deque
from dataclasses import asdict
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq
from tdx.gbbq_reader import read_gbbq
from v4.factors.core import Bar, Observation, compute_core, market_reference
from .market_source_acquisition import official_sessions, write, now, is_stock_code
from .tdx_official_daily_source import sha256_file, _atomic_write

CONTRACT = 'config/v4_r43_corrected_owner_replay_v3.json'
OUT = 'docs/evidence/r4_3_four_session_closeout_20261009/owner_v3'
_DAY_RECORD_FORMAT = '<IIIIIfII'


class _PackedDayRows:
    """Re-iterable compact view of a bounded TDX .day history window."""

    def __init__(self, payload):
        self.payload = payload

    def __iter__(self):
        return struct.iter_unpack(_DAY_RECORD_FORMAT, self.payload)

    def __len__(self):
        return len(self.payload) // struct.calcsize(_DAY_RECORD_FORMAT)


def load(path):
    return json.loads(Path(path).read_bytes())


def ref(root, path):
    p = Path(path).resolve()
    return dict(path=p.relative_to(Path(root).resolve()).as_posix(), sha256=sha256_file(p), bytes=p.stat().st_size)


def checked(root, binding):
    p = (Path(root) / binding['path']).resolve()
    p.relative_to(Path(root).resolve())
    if sha256_file(p) != binding['sha256']:
        raise ValueError('CORRECTED_INPUT_DIGEST_MISMATCH:' + binding['path'])
    return p


def gzwrite(root, path, rows):
    raw = b''.join((json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode() for r in rows)
    _atomic_write(path, gzip.compress(raw, mtime=0), tdx_root=Path('D:/new_tdx'))
    return ref(root, path)


def gzrows(path):
    with gzip.open(path, 'rt', encoding='utf8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def transform_window(raw, events, dispositions, target):
    """Unsupported events affect crossing bars, not every later window forever."""
    cutoff = int(target.replace('-', ''))
    relevant = [e for e in events if e.event_date <= cutoff]
    blocked = [e for e in relevant if dispositions.get(str(e.category), {}).get(
        'formal_disposition', 'UNKNOWN_PRICE_IMPACT') in ('PRICE_AFFECTING_UNSUPPORTED', 'UNKNOWN_PRICE_IMPACT')]
    factors = build_affine_factors([r[0] for r in raw] + [cutoff],
                                  [xrxd_from_gbbq(e) for e in relevant if e.category == 1])
    result = []
    for day, o, h, l, c, amount, volume, _ in raw:
        if day > cutoff:
            continue
        barriers = [e for e in blocked if day < e.event_date]
        factor = factors[day]
        q = None if barriers else [float(factor.qfq_price(Decimal(v) / 100)) for v in (o, h, l, c)]
        s = str(day)
        result.append(dict(trade_date=s[:4]+'-'+s[4:6]+'-'+s[6:], raw_ohlc=[v/100 for v in (o,h,l,c)],
                           qfq_ohlc=q, amount=amount, volume=volume, qfq_mul=str(factor.qfq_mul),
                           qfq_add=str(factor.qfq_add), blocked_events=[dict(date=e.event_date, category=e.category) for e in barriers]))
    return result


def independent_affine(raw_price, bar_date, events, target):
    """Independent chronological event-price recurrence, no factor-builder calls."""
    value = Decimal(str(raw_price))
    with localcontext() as ctx:
        ctx.prec = 40
        for e in sorted(events, key=lambda x:(x.event_date, x.source_record_index)):
            if e.category != 1 or not bar_date < e.event_date <= target:
                continue
            cash, rights_price, bonus, rights = [Decimal(str(v)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                                                for v in (e.c1,e.c2,e.c3,e.c4)]
            value = (value*10-cash+rights*rights_price)/(10+bonus+rights)
        return float(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


def midrank(returns, members):
    """Same frozen midrank formula, sorted cross-section avoids quadratic loops."""
    values = sorted(v for s,v in returns.items() if s in members and v is not None)
    n = len(values)
    return {s: None if n < 2 or returns.get(s) is None else
            100*(bisect.bisect_left(values,returns[s]) +
                 .5*(bisect.bisect_right(values,returns[s])-bisect.bisect_left(values,returns[s])-1))/(n-1) for s in members}


def rank_exact_endpoint_rps(returns, endpoint_members):
    """Rank endpoint returns against that endpoint's exact dated membership."""
    return midrank(returns, set(endpoint_members))


def progress_items(rows, callback, *, coordinate_endpoint=None, phase=None, clock=None):
    """Report completed loop work in bounded batches; never alter numeric rows."""
    if callback is None:
        yield from rows
        return
    import time
    clock=clock or time.monotonic
    total=len(rows);last_at=clock();last_count=0
    base=dict(total=total,unit='securities',coordinate_endpoint=coordinate_endpoint,phase=phase)
    callback(dict(base,processed=0,message=f'{phase or "处理"} 证券对象开始；计算坐标端点 {coordinate_endpoint or "未指定"}'))
    for processed,row in enumerate(rows,1):
        yield row
        now=clock()
        if processed-last_count>=200 or now-last_at>=2 or processed==total:
            callback(dict(base,processed=processed,message=f'{phase or "处理"} 已处理证券对象（含不足/缺源）；计算坐标端点 {coordinate_endpoint or "未指定"}'))
            last_at=now;last_count=processed


PROFILE_LIFECYCLE_CONSERVATION_CONTRACT = "DYNAMIC_PROFILE_LIFECYCLE_CONSERVATION_R1"


def complete_target_universe(snapshot_ids, active_lifecycle_ids):
    """Union the target-day lifecycle into any older or narrower snapshot."""
    return set(snapshot_ids or ()) | set(active_lifecycle_ids or ())


def unknown_active_core_row(identity_row, target, sessions, basis_namespace):
    """Materialize an active identity with quality-local UNKNOWN fields and no bars."""
    from dataclasses import asdict
    start=max(str(identity_row.get('list_date') or target),min(sessions))
    unknown_sessions=[d for d in sessions if start<=d<=target] or [target]
    observations=[Observation(d,'UNKNOWN',None) for d in unknown_sessions]
    fields={key:asdict(value) for key,value in compute_core(observations,identity_row['security_id'],asof=target).items()}
    return dict(security_id=identity_row['security_id'],source_security_key=identity_row['source_security_key'].upper(),
        board_scope=identity_row['board_scope'],trade_date=target,price_basis_id=basis_namespace+':NO_PRICE_HISTORY',
        fields=fields,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
        profile_quality='INSUFFICIENT_HISTORY',quality_codes=['UNKNOWN','INSUFFICIENT_HISTORY'])


def materialize_core(root, dates=None, *, basis_namespace='TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE', accepted_history=None, progress_counter=None,
                     identity_binding=None, identity_rows=None, required_active_ids=None):
    if basis_namespace not in ('TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE','TDX_NATIVE_AFFINE_QFQ_V0_3_EXACT_TARGET_COORDINATE'):
        raise ValueError('UNSUPPORTED_CORE_BASIS_NAMESPACE')
    root = Path(root).resolve(); policy = load(root/CONTRACT)
    dates = dates or policy['target_sessions']; out = root/OUT; out.mkdir(parents=True, exist_ok=True)
    protected = {p: sha256_file(root/p) for p in ('config/v4_joint_release_authority_v1.json','data/v4/V4_DATA_ACCEPTED_HEAD.json')}
    write(out/'ENTRY.json', dict(contract=ref(root,root/CONTRACT), upgrade_document='R4.3', phase0='DEGRADED_PASS',
          acceptance='IN_PROGRESS', observed_at=now(), protected=protected, next_stage='CORRECTED_STRUCTURE_AND_MEMBER_OWNERS'))
    head = load(root/'data/v4/V4_DATA_ACCEPTED_HEAD.json')
    identity_binding = identity_binding or head['component_artifacts']['IDENTITY_UNIVERSE']
    identity = identity_rows if identity_rows is not None else load(checked(root,identity_binding))['rows']
    required_active_ids = set(required_active_ids or ())
    ids = {r['source_security_key'].lower():r for r in identity}
    sessions = official_sessions(root)
    required = sorted(set(dates) | {sessions[sessions.index(d)-k] for d in dates for k in (1,3,4,5)})
    acquisition = load(root/'docs/evidence/source_acquisition_r4_20261009/capture/acquisition.json')
    batches = {}; universes = {}; bao_queries=[]
    for q in acquisition['queries']:
        if q.get('path') and q['method'] in ('query_daily_history_k_AStock','query_all_stock','validated_daily_universe'):
            payload=load(q['path']); rows=payload.get('rows',[]); day=q['params'].get('date',q['params'].get('day'))
            if q['method']=='query_daily_history_k_AStock':batches[day]={r['code'].lower():r for r in rows}
            else:universes[day]={r['code'].lower():r for r in rows if is_stock_code(r['code'])}
            bao_queries.append(q)
    source_pointer=load(root/'reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json')
    capture=load(checked(root,source_pointer['capture_receipt'])); package=checked(root,capture['package'])
    if capture['official_publication_date'] < max(dates):raise ValueError('OFFICIAL_PACKAGE_STALE')
    frozen_previous=load(root/'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/CORE_REPLAY.json')['owners'][0]
    source_gbbq=checked(root,frozen_previous['sources']['gbbq']); blob=source_gbbq.read_bytes()
    gpath=root/'data/v4/corrected_owner_sources'/hashlib.sha256(blob).hexdigest()/'gbbq'
    _atomic_write(gpath,blob,tdx_root=Path('D:/new_tdx'))
    events=defaultdict(list)
    for e in read_gbbq(gpath):events[e.security_id.lower()].append(e)
    dispositions=load(root/'config/v4_02_gbbq_price_impact_classification_v1.json')['dispositions']
    sources=dict(package=capture['package'],receipt=source_pointer['capture_receipt'],gbbq=ref(root,gpath),
                 identity=identity_binding,contract=ref(root,root/CONTRACT),
                 core_kernel=ref(root,root/'src/v4/factors/core.py'),adjustment_kernel=ref(root,root/'src/adjustment/tdx_adjustment.py'))
    snapshot=root/'docs/evidence/r4_3_four_session_closeout_20261009/MEMBER_SNAPSHOT_S.json'
    sources['latest_tdx_member_snapshot']=ref(root,snapshot)
    sources['r43_producer']=ref(root,Path(__file__))
    sources['typed_delta_v2']=ref(root,root/'docs/evidence/r4_2_1_20261009/TDX_A_STOCK_DELTA_V2_RUNTIME_RECEIPT.json')
    source_digest=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest()
    status=defaultdict(dict)
    historical=load(root/'config/v4_sector_operational_authority_v1.json')['sources']['historical_status']
    for r in gzrows(checked(root,historical)):
        if r['status']=='SUSPENDED':status[r['security_id']][r['trade_date']]='SUSPENDED'
    chain=load(checked(root,head['accepted_chain']))
    dated_identity={}
    for node in chain['nodes']:
        d=node['trade_date']; rs=load(root/node['components']['IDENTITY_UNIVERSE']['artifact_path'])['rows']
        dated_identity[d]={r['security_id'] for r in rs}
        for r in load(root/node['components']['TRADING_STATUS']['artifact_path'])['rows']:status[r['security_id']][d]=r['status']
    historical_universe=load(checked(root,load(root/'config/v4_market_operational_authority_v1.json')['market']))['sources']['historical_universe']
    for r in gzrows(checked(root,historical_universe)):
        if r['trade_date'] in required and r['board_scope'] in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT'):
            dated_identity.setdefault(r['trade_date'],set()).add(r['security_id'])
    for day,rows in batches.items():
        for code,r in rows.items():
            if code in ids:status[ids[code]['security_id']][day]='SUSPENDED' if r.get('tradestatus')=='0' else 'ACTUAL_TRADED'
    for day,rows in universes.items():dated_identity[day]={ids[c]['security_id'] for c in rows if c in ids}
    # The target-dated lifecycle is complete; older snapshots cannot exclude a new listing.
    if required_active_ids:dated_identity[max(dates)]=complete_target_universe(dated_identity.get(max(dates)),required_active_ids)
    cache={}; unknown_codes=[]
    with zipfile.ZipFile(package) as z:
        for name in z.namelist():
            parts=name.lower().replace('\\','/').split('/');leaf=parts[-1]
            market=next((p for p in parts if p in ('sh','sz','bj')),None)
            if not market or not leaf.endswith('.day'):continue
            code=market+'.'+leaf[-10:-4]
            if not is_stock_code(code):continue
            if code not in ids:
                unknown_codes.append(code);continue
            # Retain the same last 420 eligible records, but pack them per code
            # instead of holding millions of Python tuples for the whole market.
            # This keeps incremental full-universe replay within bounded memory.
            cutoff=int(max(dates).replace('-',''));window=deque(maxlen=420)
            for row in struct.iter_unpack(_DAY_RECORD_FORMAT,z.read(name)):
                if row[0]<=cutoff:window.append(row)
            packed=b''.join(struct.pack(_DAY_RECORD_FORMAT,*row) for row in window)
            cache[ids[code]['security_id']]=(code,_PackedDayRows(packed))
    if accepted_history:
        # A normal append may add a new bar, but cannot silently borrow an old
        # acceptance after a provider corrects an overlapping historical bar.
        from .operational_increment_plan_v1 import verify_history_overlap
        verify_history_overlap(cache,gzrows(checked(root,accepted_history)),active_security_ids=dated_identity.get(max(dates)))
    write(out/'SOURCE_BINDINGS.json',dict(sources=sources,unknown_canonical_identity=unknown_codes,
          query_receipts=bao_queries,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
    rps={}; receipts=[]; oracle=[]
    for target in required:
        rows=[]; histories={}; prior_rows=[]; checks=Counter(); errors=[]; sample=[]; raw_rows=[]; adjusted_rows=[]
        previous=sessions[sessions.index(target)-1]
        members=dated_identity.get(target)
        if members is None:raise ValueError('NO_DATED_IDENTITY_UNIVERSE:'+target)
        # Delta endpoints must be ranked in the target's affine QFQ coordinate.
        # Reusing an endpoint score cached from its own target coordinate makes
        # cross-date deltas incomparable after corporate actions.
        endpoint_dates=({sessions[sessions.index(target)-k] for k in (1,3)} if target in dates else set())
        endpoint_members={d:set(dated_identity[d]) for d in endpoint_dates if d in dated_identity}
        if endpoint_dates-set(endpoint_members):
            raise ValueError('NO_EXACT_DATED_RPS_MEMBERSHIP:'+','.join(sorted(endpoint_dates-set(endpoint_members))))
        endpoint_returns={(d,h):{} for d in endpoint_dates for h in (5,20)}
        source_members=set(members).union(*(endpoint_members.values() or [set()]))
        for i in progress_items(identity,progress_counter,coordinate_endpoint=target,phase='CORE'):
            sid=i['security_id']
            if sid not in source_members:continue
            code=i['source_security_key'].lower()
            raw=cache[sid][1] if sid in cache else []
            bs=transform_window(raw,events[code],dispositions,target) if raw else []
            if not bs:
                if sid not in required_active_ids or target != max(dates):continue
                # Preserve active lifecycle rows without fabricating price history.
                unknown_row=unknown_active_core_row(i,target,sessions,basis_namespace)
                rows.append(unknown_row)
                if target in dates:
                    histories[sid]=[]
                    prior_values={k:asdict(v) for k,v in compute_core(
                        [Observation(d,'UNKNOWN',None) for d in sessions if str(i.get('list_date') or target)<=d<=previous],
                        sid,asof=previous).items()} if str(i.get('list_date') or target)<=previous else {}
                    prior_rows.append(dict(security_id=sid,trade_date=previous,coordinate_target=target,
                        price_basis_id=basis_namespace+':NO_PRICE_HISTORY',fields=prior_values))
                continue
            code,raw=cache[sid];bs=transform_window(raw,events[code],dispositions,target)
            revision=hashlib.sha256(json.dumps(dict(code=code,gbbq=sources['gbbq']['sha256'],
                events=[(e.event_date,e.category,e.c1,e.c2,e.c3,e.c4) for e in events[code]
                        if e.event_date<=int(target.replace('-','')) and e.category==1]),sort_keys=True).encode()).hexdigest()
            basis=basis_namespace+':'+revision
            by={b['trade_date']:b for b in bs};obs=[]
            for day in sessions:
                if not bs[0]['trade_date']<=day<=target:continue
                b=by.get(day);q=b['qfq_ohlc'] if b else None
                state='ACTUAL' if q else 'ADJUSTMENT_UNKNOWN' if b else 'CONFIRMED_SUSPENSION' if status[sid].get(day)=='SUSPENDED' else 'UNKNOWN'
                obs.append(Observation(day,state,Bar(*q,float(b['amount']),float(b['volume']),basis,source_digest) if q else None))
            values={k:asdict(v) for k,v in compute_core(obs,sid,asof=target).items()}
            if sid in members:
                rows.append(dict(security_id=sid,source_security_key=code.upper(),board_scope=i['board_scope'],
                     trade_date=target,price_basis_id=basis,fields=values,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
            for endpoint in endpoint_dates:
                if sid not in endpoint_members[endpoint]:continue
                endpoint_values=compute_core(obs,sid,asof=endpoint)
                for h in (5,20):endpoint_returns[(endpoint,h)][sid]=endpoint_values[f'ret{h}'].value
            if sid not in members:continue
            if target not in dates:continue
            histories[sid]=bs
            pv={k:asdict(v) for k,v in compute_core(obs,sid,asof=previous).items()} if obs[0].trade_date<=previous else {}
            prior_rows.append(dict(security_id=sid,trade_date=previous,coordinate_target=target,price_basis_id=basis,fields=pv))
            b=by.get(target)
            if b:
                raw_rows.append(dict(security_id=sid,trade_date=target,**dict(zip(('open','high','low','close'),b['raw_ohlc'])),amount=b['amount'],volume=b['volume']))
                adjusted_rows.append(dict(security_id=sid,trade_date=target,**dict(zip(('open','high','low','close'),b['qfq_ohlc'] or [None]*4)),qfq_mul=b['qfq_mul'],qfq_add=b['qfq_add'],price_basis=basis_namespace,adjustment_source_revision=revision,adjustment_readiness='READY' if b['qfq_ohlc'] else 'UNKNOWN'))
            for n in ('ma20','atr20'):
                cell=values[n]
                if cell['value'] is None:continue
                window=[o for o in obs if cell['window_start_trade_date']<=o.trade_date<=cell['window_end_trade_date'] and o.bar]
                expected=sum(o.bar.close for o in window)/20 if n=='ma20' else sum(max(b.bar.high-b.bar.low,abs(b.bar.high-a.bar.close),abs(b.bar.low-a.bar.close)) for a,b in zip(window,window[1:]))/20
                checks[n]+=1
                if abs(expected-cell['value'])>1e-9:errors.append(dict(security_id=sid,field=n,expected=expected,actual=cell['value']))
            # Real coefficient oracle on all four OHLC, including ex-right boundaries.
            for b in bs[-75:]:
                if not b['qfq_ohlc']:continue
                expected=[independent_affine(v,int(b['trade_date'].replace('-','')),events[code],int(target.replace('-',''))) for v in b['raw_ohlc']]
                checks['independent_affine_ohlc']+=4
                if expected!=b['qfq_ohlc']:errors.append(dict(security_id=sid,field='OHLC_AFFINE',date=b['trade_date'],expected=expected,actual=b['qfq_ohlc']))
            if len(sample)<30 and (any(e.event_date>=int(bs[-75]['trade_date'].replace('-','')) for e in events[code]) if len(bs)>=75 else True):
                sample.append(dict(security_id=sid,code=code,bars=bs[-22:],events=[dict(date=e.event_date,category=e.category) for e in events[code] if e.event_date<=int(target.replace('-',''))][-10:]))
        factorby={r['security_id']:r for r in rows}
        for h in (5,20):
            scores=rank_exact_endpoint_rps({s:r['fields'][f'ret{h}']['value'] for s,r in factorby.items()},members)
            rps[target,h]=scores
            for sid,row in factorby.items():row['fields'][f'rps{h}']=dict(value=scores.get(sid),quality_state='OBSERVED' if scores.get(sid) is not None else 'UNKNOWN',unknown_reason=None if scores.get(sid) is not None else 'RETURN_OR_UNIVERSE_UNKNOWN',contract_id='RPS_MIDRANK_V1',denominator=sum(v is not None for v in scores.values()))
            for endpoint in endpoint_dates:
                rps[endpoint,h]=rank_exact_endpoint_rps(endpoint_returns[(endpoint,h)],endpoint_members[endpoint])
        if target not in dates:continue
        for h in (1,3,5):
            start=sessions[sessions.index(target)-h];start_members=dated_identity.get(start,set())
            reference,meta=market_reference({s:r['fields'][f'ret{h}']['value'] for s,r in factorby.items()},sorted(start_members))
            for sid,row in factorby.items():
                v=row['fields'][f'ret{h}']['value'];v=v-reference if v is not None and reference is not None else None
                row['fields'][f'rel_market_{h}']=dict(value=v,quality_state='OBSERVED' if v is not None else 'UNKNOWN',unknown_reason=None if v is not None else 'DATED_MARKET_REFERENCE_UNPROVEN',start_universe_date=start,reference=meta)
        for sid,row in factorby.items():
            for h,k in ((5,1),(5,3),(20,3)):
                prior=sessions[sessions.index(target)-k];a=rps.get((prior,h),{}).get(sid);b=rps[target,h].get(sid);v=b-a if a is not None and b is not None else None
                row['fields'][f'rps{h}_delta{k}']=dict(value=v,quality_state='OBSERVED' if v is not None else 'UNKNOWN',unknown_reason=None if v is not None else 'EXACT_DATED_RPS_ENDPOINT_UNKNOWN',prior_endpoint=prior,contract_id='RPS_MIDRANK_V1')
        folder=out/'owners'/target
        receipt=dict(trade_date=target,rows=len(rows),source_digest=source_digest,sources=sources,
             core=gzwrite(root,folder/'core.jsonl.gz',rows),prior_core=gzwrite(root,folder/'prior_core_target_coordinate.jsonl.gz',prior_rows),
             history=gzwrite(root,folder/'history.jsonl.gz',[dict(security_id=sid,bars=bs) for sid,bs in histories.items()]),
             raw=gzwrite(root,folder/'raw.jsonl.gz',raw_rows),adjusted=gzwrite(root,folder/'adjusted.jsonl.gz',adjusted_rows),
             actual_raw_rows=len(raw_rows),adjustment_current_ready=sum(r['adjustment_readiness']=='READY' for r in adjusted_rows),
             known_fields=dict(Counter(k for r in rows for k,v in r['fields'].items() if v.get('value') is not None)),
             knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,publication_state='STAGING_NOT_ACCEPTED')
        write(folder/'OWNER.json',receipt);receipts.append(receipt)
        oracle.append(dict(trade_date=target,checks=dict(checks),errors=errors,samples=sample,result='PASS' if not errors else 'FAIL'))
        print(json.dumps(dict(stage='CORE',date=target,rows=len(rows),raw=len(raw_rows),known=receipt['known_fields'],errors=len(errors))),flush=True)
        if errors:raise ValueError('INDEPENDENT_CORE_ORACLE_FAILED:'+target)
    write(out/'CORE_REPLAY.json',dict(contract='V4_R43_CORRECTED_OWNER_REPLAY_V3',owners=receipts,oracle=oracle,
          protected=protected,heads_unchanged=all(sha256_file(root/p)==h for p,h in protected.items()),
          acceptance='PASS_CORRECTED_CORE_NUMERIC_ORACLE',next_stage='PROFILE_STRUCTURE_SECTOR_FOCUS_FORWARD'))
    return receipts
