"""R4.1 corrected-source producer, preserving frozen kernels and live pointers."""
from __future__ import annotations
import bisect
import gzip
import hashlib
import json
import os
import struct
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq
from tdx.gbbq_reader import decode_gbbq_bytes
from v4.factors.core import Bar, Observation, compute_core, market_reference
from .market_source_acquisition import official_sessions, write, now, is_stock_code
from .tdx_official_daily_source import sha256_file, _atomic_write

CONTRACT = 'config/v4_r43_corrected_owner_replay_v3.json'
OUT = 'data/v4/workspaces/r43_owner_replay_v1'
_SOURCE_IDS = {
    'acquisition': '0ea5b6c8b6edc554398ebcfb36fda732958e1b9b40260f08efd125c28d0595f8',
    'capture_audit': '462c84b4c0f38c0bf8004b79d15adfb4f6be90a6dee2e234d17549b154d73c79',
    'core_replay': '7943e8d30b8c3ef4494ab69653d99da03f5541e75d17260c0be2fcdf0be1966e',
    'member_snapshot': '7eef000c2eaa7aef5aece5177516181bf293ae26575e102a433e8c30070bb0a7',
    'typed_receipt': '81e97c29fa72275c653d09cec6dc37ac89b0b3ea0f38aa456ca81839528fe6ab',
}


class _ZipReader:
    """Expose PG bytes as a seekable stream without path or byte-array copies."""
    def __init__(self, source):
        self.source = source

    def read(self, size=-1):
        return self.source.read(size)

    def seek(self, offset, whence=0):
        return self.source.seek(offset, whence)

    def tell(self):
        return self.source.tell()

    def seekable(self):
        return True

    def close(self):
        self.source.close()


def load(path):
    raw = path.read_bytes() if hasattr(path, 'read_bytes') else Path(path).read_bytes()
    return json.loads(raw)


def historical_source(root, key):
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_source
    return read_source(root, _SOURCE_IDS[key])


def pg_json_source(root, relative_path):
    """Read an exact, previously ingressed project source; never fall back to disk."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_path,read_latest_candidate_path
    relative=Path(relative_path).as_posix()
    try:source=read_path(root,relative)
    except ValueError as error:
        if str(error)!='HISTORICAL_SOURCE_INGRESS_NOT_UNIQUE':raise
        source=read_latest_candidate_path(root,relative,source_origin=(
            'V4_CORRECTED_OWNER_CANDIDATE_OUTPUT','V4_R43_OWNER_CANDIDATE_OUTPUT'))
    if not isinstance(source.get('value'), dict):
        raise ValueError('PG_JSON_SOURCE_NOT_OBJECT:' + str(relative_path))
    return source['value']


def pg_source_binding(root, relative_path):
    """Return the immutable path/SHA/size fact already registered in PostgreSQL."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_path,read_latest_candidate_path
    relative=Path(relative_path).as_posix()
    try:source=read_path(root,relative)
    except ValueError as error:
        if str(error)!='HISTORICAL_SOURCE_INGRESS_NOT_UNIQUE':raise
        source=read_latest_candidate_path(root,relative,source_origin=(
            'V4_CORRECTED_OWNER_CANDIDATE_OUTPUT','V4_R43_OWNER_CANDIDATE_OUTPUT'))
    record = source['record']
    return dict(path=record['source_path'], sha256=record['source_sha256'],
                bytes=record['source_bytes'])


def pg_text_source(root, relative_path):
    """Resolve registered text bytes, admitting a missing exact source only once."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import (
        read_path, read_bound, ingest_file, source_id_for_path,
    )
    relative=Path(relative_path).as_posix()
    try:
        source=read_path(root,relative)
    except ValueError as exc:
        if str(exc)!='HISTORICAL_SOURCE_INGRESS_NOT_FOUND':raise
        path=(Path(root).resolve()/relative).resolve()
        raw=path.read_bytes()
        import hashlib
        sha=hashlib.sha256(raw).hexdigest()
        ingest_file(root,source_id_for_path(relative),path,expected_sha256=sha)
        source=read_bound(root,relative,sha)
    return source['raw'].decode('utf-8')


def ref(root, path):
    p = Path(path).resolve()
    return dict(path=p.relative_to(Path(root).resolve()).as_posix(), sha256=sha256_file(p), bytes=p.stat().st_size)


def checked(root, binding):
    from workbench_db.v4_historical_source_ingress_pg_r1 import (
        PGSourceBytes, bound_bytes, read_package_bytes,
    )
    try:
        try:
            return bound_bytes(root, binding)
        except ValueError as exc:
            if str(exc) != 'HISTORICAL_SOURCE_INGRESS_NOT_FOUND':
                raise
            package = read_package_bytes(root, binding['path'], binding['sha256'])
            if binding.get('bytes') is not None and len(package['raw']) != binding['bytes']:
                raise ValueError('PG_BOUND_PACKAGE_SIZE_MISMATCH')
            return PGSourceBytes(package, root)
    except ValueError as exc:
        raise ValueError('CORRECTED_PG_INPUT_UNAVAILABLE:' + binding['path'] + ':' + str(exc)) from exc


def checked_pg(root, binding):
    """Read an already-ingressed exact source revision; do not admit disk bytes here."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import bound_bytes
    try:
        return bound_bytes(root,binding)
    except (OSError,ValueError) as exc:
        raise ValueError('PG_BOUND_INPUT_UNAVAILABLE:'+str(binding.get('path'))+':'+str(exc)) from exc


def source_ingress(root, binding):
    """Explicitly admit one bounded historical/provider source, then return PG bytes."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import ingress_path, PGSourceBytes
    try:
        admitted=ingress_path(root,binding['path'],expected_sha256=binding['sha256'])
        return PGSourceBytes(admitted, root)
    except ValueError as exc:
        raise ValueError('SOURCE_INGRESS_UNAVAILABLE:' + binding['path'] + ':' + str(exc)) from exc


def gzwrite(root, path, rows, *, pg_ingress=False):
    raw = b''.join((json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode() for r in rows)
    compressed = gzip.compress(raw, mtime=0)
    from common.paths import resolve_tdx_root
    _atomic_write(path, compressed, tdx_root=resolve_tdx_root(root))
    if pg_ingress:
        _ingress_candidate_bytes(root, path, compressed)
    return ref(root, path)


def _ingress_candidate_bytes(root, path, raw):
    """Publish producer bytes to immutable PG ingress before downstream reads."""
    import hashlib
    from workbench_db.v4_historical_source_ingress_pg_r1 import (
        MAX_INLINE_SOURCE_BYTES, ingest_captured_bytes, ingest_package_bytes,
        read_bound, read_package_bytes,
    )
    project = Path(root).resolve()
    relative = Path(path).resolve().relative_to(project).as_posix()
    sha = hashlib.sha256(raw).hexdigest()
    if len(raw) > MAX_INLINE_SOURCE_BYTES:
        try:
            existing = read_package_bytes(project, relative, sha)
        except ValueError as error:
            if str(error) != 'HISTORICAL_SOURCE_PACKAGE_NOT_FOUND': raise
            result = ingest_package_bytes(project, relative, raw, expected_sha256=sha,
                source_revision=sha, source_origin='V4_R43_OWNER_CANDIDATE_OUTPUT')
            actual = read_package_bytes(project, relative, sha)['raw']
        else:
            # A prior exact-byte package may already have been admitted under a
            # broader corrected-owner source origin. Its immutable chunk key is
            # content-addressed, so verify/reuse those bytes instead of trying to
            # rewrite provenance metadata under the same chunk identity.
            result = existing['record']
            actual = existing['raw']
    else:
        result = ingest_captured_bytes(project, relative, raw, source_revision=sha,
            source_origin='V4_R43_OWNER_CANDIDATE_OUTPUT')
        actual = read_bound(project, relative, sha)['raw']
    if (actual != raw or result['source_sha256'] != sha
            or result['source_bytes'] != len(raw)):
        raise ValueError('R43_OWNER_OUTPUT_PG_READBACK_MISMATCH:' + relative)


def write_candidate_json(root, path, value):
    """Atomically write one candidate receipt and register its exact PG bytes."""
    write(path, value, project_root=root)
    raw = Path(path).read_bytes()
    _ingress_candidate_bytes(root, path, raw)
    return ref(root, path)


def gzrows(path):
    if hasattr(path, 'read_bytes'):
        stream = gzip.decompress(path.read_bytes()).decode('utf8').splitlines()
        return [json.loads(line) for line in stream if line.strip()]
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
    root = Path(root).resolve(); policy = pg_json_source(root, CONTRACT)
    dates = dates or policy['target_sessions']; out = root/OUT; out.mkdir(parents=True, exist_ok=True)
    from workbench_db.dm01_data_accepted_head_pg_r1 import read_current
    head_state = read_current(root)
    head = head_state['candidate']
    protected = {'config/v4_joint_release_authority_v1.json': sha256_file(root/'config/v4_joint_release_authority_v1.json'),
                 'data/v4/V4_DATA_ACCEPTED_HEAD.json': head_state['head_sha256']}
    write_candidate_json(root,out/'ENTRY.json', dict(contract=ref(root,root/CONTRACT), upgrade_document='R4.3', phase0='DEGRADED_PASS',
          acceptance='IN_PROGRESS', observed_at=now(), protected=protected, next_stage='CORRECTED_STRUCTURE_AND_MEMBER_OWNERS'))
    identity_binding = identity_binding or head['component_artifacts']['IDENTITY_UNIVERSE']
    identity = identity_rows if identity_rows is not None else load(checked(root,identity_binding))['rows']
    required_active_ids = set(required_active_ids or ())
    ids = {r['source_security_key'].lower():r for r in identity}
    sessions = official_sessions(root)
    required = sorted(set(dates) | {sessions[sessions.index(d)-k] for d in dates for k in (1,3,4,5)})
    acquisition = historical_source(root,'acquisition')['value']
    batches = {}; universes = {}; bao_queries=[]
    for q in acquisition['queries']:
        if q.get('path') and q['method'] in ('query_daily_history_k_AStock','query_all_stock','validated_daily_universe'):
            payload=pg_json_source(root, Path(q['path']).resolve().relative_to(root).as_posix()); rows=payload.get('rows',[]); day=q['params'].get('date',q['params'].get('day'))
            if q['method']=='query_daily_history_k_AStock':batches[day]={r['code'].lower():r for r in rows}
            else:universes[day]={r['code'].lower():r for r in rows if is_stock_code(r['code'])}
            bao_queries.append(q)
    source_pointer=historical_source(root,'capture_audit')['value']
    capture=load(checked(root,source_pointer['capture_receipt'])); package=checked(root,capture['package'])
    if capture['official_publication_date'] < max(dates):raise ValueError('OFFICIAL_PACKAGE_STALE')
    frozen_previous=historical_source(root,'core_replay')['value']['owners'][0]
    gbbq_binding=frozen_previous['sources']['gbbq']
    source_gbbq=checked(root,gbbq_binding); blob=source_gbbq.read_bytes()
    events=defaultdict(list)
    for e in decode_gbbq_bytes(blob,source=gbbq_binding['path']):events[e.security_id.lower()].append(e)
    dispositions=pg_json_source(root,'config/v4_02_gbbq_price_impact_classification_v1.json')['dispositions']
    sources=dict(package=capture['package'],receipt=source_pointer['capture_receipt'],gbbq=gbbq_binding,
                 identity=identity_binding,contract=ref(root,root/CONTRACT),
                 core_kernel=ref(root,root/'src/v4/factors/core.py'),adjustment_kernel=ref(root,root/'src/adjustment/tdx_adjustment.py'))
    snapshot_source=historical_source(root,'member_snapshot')['record']
    sources['latest_tdx_member_snapshot']=dict(path=snapshot_source['source_path'],sha256=snapshot_source['source_sha256'],bytes=snapshot_source['source_bytes'])
    sources['r43_producer']=ref(root,Path(__file__))
    typed_source=historical_source(root,'typed_receipt')['record']
    sources['typed_delta_v2']=dict(path=typed_source['source_path'],sha256=typed_source['source_sha256'],bytes=typed_source['source_bytes'])
    source_digest=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest()
    status=defaultdict(dict)
    historical=pg_json_source(root,'config/v4_sector_operational_authority_v1.json')['sources']['historical_status']
    for r in gzrows(checked(root,historical)):
        if r['status']=='SUSPENDED':status[r['security_id']][r['trade_date']]='SUSPENDED'
    chain=load(checked(root,head['accepted_chain']))
    dated_identity={}
    for node in chain['nodes']:
        d=node['trade_date'];component=node['components']['IDENTITY_UNIVERSE']
        rs=load(checked(root,dict(path=component['artifact_path'],sha256=component['artifact_sha256'])))['rows']
        dated_identity[d]={r['security_id'] for r in rs}
        component=node['components']['TRADING_STATUS']
        for r in load(checked(root,dict(path=component['artifact_path'],sha256=component['artifact_sha256'])))['rows']:
            status[r['security_id']][d]=r['status']
    market_authority=pg_json_source(root,'config/v4_market_operational_authority_v1.json')
    historical_universe=load(checked(root,market_authority['market']))['sources']['historical_universe']
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
    with zipfile.ZipFile(_ZipReader(package)) as z:
        for name in z.namelist():
            parts=name.lower().replace('\\','/').split('/');leaf=parts[-1]
            market=next((p for p in parts if p in ('sh','sz','bj')),None)
            if not market or not leaf.endswith('.day'):continue
            code=market+'.'+leaf[-10:-4]
            if not is_stock_code(code):continue
            if code not in ids:
                unknown_codes.append(code);continue
            raw=[v for v in struct.iter_unpack('<IIIIIfII',z.read(name)) if v[0]<=int(max(dates).replace('-',''))]
            # Preserve enough actual bars for the original 250-bar Profile and period windows.
            cache[ids[code]['security_id']]=(code,raw[-420:])
    if accepted_history:
        # A normal append may add a new bar, but cannot silently borrow an old
        # acceptance after a provider corrects an overlapping historical bar.
        from .operational_increment_plan_v1 import verify_history_overlap
        verify_history_overlap(cache,gzrows(checked(root,accepted_history)),active_security_ids=dated_identity.get(max(dates)))
    write_candidate_json(root,out/'SOURCE_BINDINGS.json',dict(sources=sources,unknown_canonical_identity=unknown_codes,
          query_receipts=bao_queries,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
    rps={}; receipts=[]; oracle=[]
    for target in required:
        rows=[]; histories={}; prior_rows=[]; checks=Counter(); errors=[]; sample=[]; raw_rows=[]; adjusted_rows=[]
        previous=sessions[sessions.index(target)-1]
        members=dated_identity.get(target)
        if members is None:raise ValueError('NO_DATED_IDENTITY_UNIVERSE:'+target)
        for i in progress_items(identity,progress_counter,coordinate_endpoint=target,phase='CORE'):
            sid=i['security_id']
            if sid not in members:continue
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
            rows.append(dict(security_id=sid,source_security_key=code.upper(),board_scope=i['board_scope'],
                 trade_date=target,price_basis_id=basis,fields=values,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
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
            scores=midrank({s:r['fields'][f'ret{h}']['value'] for s,r in factorby.items()},members)
            rps[target,h]=scores
            for sid,row in factorby.items():row['fields'][f'rps{h}']=dict(value=scores.get(sid),quality_state='OBSERVED' if scores.get(sid) is not None else 'UNKNOWN',unknown_reason=None if scores.get(sid) is not None else 'RETURN_OR_UNIVERSE_UNKNOWN',contract_id='RPS_MIDRANK_V1',denominator=sum(v is not None for v in scores.values()))
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
             core=gzwrite(root,folder/'core.jsonl.gz',rows,pg_ingress=True),prior_core=gzwrite(root,folder/'prior_core_target_coordinate.jsonl.gz',prior_rows,pg_ingress=True),
             history=gzwrite(root,folder/'history.jsonl.gz',[dict(security_id=sid,bars=bs) for sid,bs in histories.items()],pg_ingress=True),
             raw=gzwrite(root,folder/'raw.jsonl.gz',raw_rows,pg_ingress=True),adjusted=gzwrite(root,folder/'adjusted.jsonl.gz',adjusted_rows,pg_ingress=True),
             actual_raw_rows=len(raw_rows),adjustment_current_ready=sum(r['adjustment_readiness']=='READY' for r in adjusted_rows),
             known_fields=dict(Counter(k for r in rows for k,v in r['fields'].items() if v.get('value') is not None)),
             knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,publication_state='STAGING_NOT_ACCEPTED')
        write_candidate_json(root,folder/'OWNER.json',receipt);receipts.append(receipt)
        oracle.append(dict(trade_date=target,checks=dict(checks),errors=errors,samples=sample,result='PASS' if not errors else 'FAIL'))
        print(json.dumps(dict(stage='CORE',date=target,rows=len(rows),raw=len(raw_rows),known=receipt['known_fields'],errors=len(errors))),flush=True)
        if errors:raise ValueError('INDEPENDENT_CORE_ORACLE_FAILED:'+target)
    write_candidate_json(root,out/'CORE_REPLAY.json',dict(contract='V4_R43_CORRECTED_OWNER_REPLAY_V3',owners=receipts,oracle=oracle,
          protected=protected,heads_unchanged=all(sha256_file(root/p)==h for p,h in protected.items()),
          acceptance='PASS_CORRECTED_CORE_NUMERIC_ORACLE',next_stage='PROFILE_STRUCTURE_SECTOR_FOCUS_FORWARD'))
    return receipts
