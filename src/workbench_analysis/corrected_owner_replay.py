"""R4.1 corrected-source producer, preserving frozen kernels and live pointers."""
from __future__ import annotations
import bisect
import gzip
import hashlib
from io import BytesIO
import json
import os
import struct
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq
from v4.factors.core import Bar, Observation, compute_core, market_reference
from .market_source_acquisition import (official_sessions, write, now, is_stock_code,
    load_source_acquisition_pg, load_source_query_pg, load_json_source_pg, load_json_binding_pg,
    load_bytes_binding_pg)
from .tdx_official_daily_source import sha256_file, _atomic_write

CONTRACT = 'config/v4_corrected_owner_replay_v1.json'
OUT = 'data/v4/workspaces/owner_repair_v1'


def load(path):
    raw=path.read_bytes() if hasattr(path,'read_bytes') else Path(path).read_bytes()
    return json.loads(raw)


def ref(root, path):
    p = Path(path).resolve()
    return dict(path=p.relative_to(Path(root).resolve()).as_posix(), sha256=sha256_file(p), bytes=p.stat().st_size)


def checked(root, binding):
    from workbench_db.v4_historical_source_ingress_pg_r1 import (
        PGSourceBytes,admit_source_binding_bytes,bound_bytes,read_package_bytes,
    )
    normalized=dict(binding)
    if 'bytes' not in normalized and type(normalized.get('byte_count')) is int:
        normalized['bytes']=normalized['byte_count']
    try:
        admit_source_binding_bytes(root,normalized,source_origin='V4_CORRECTED_OWNER_CANDIDATE')
        try:return bound_bytes(root,normalized)
        except ValueError as error:
            if str(error)!='HISTORICAL_SOURCE_INGRESS_NOT_FOUND':raise
            return PGSourceBytes(read_package_bytes(root,normalized['path'],normalized['sha256']),root)
    except (OSError,KeyError,ValueError) as error:
        raise ValueError('CORRECTED_PG_INPUT_UNAVAILABLE:'+str(binding.get('path',''))+':'+str(error)) from error


def checked_pg(root, binding):
    """Resolve an exact historical input from PG; this replay has no disk fallback."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import bound_bytes, read_package_bytes
    try:
        return bound_bytes(root, binding)
    except (OSError, KeyError, ValueError) as error:
        if not isinstance(error, ValueError) or str(error) != 'HISTORICAL_SOURCE_INGRESS_NOT_FOUND':
            raise ValueError('CORRECTED_PG_INPUT_UNAVAILABLE:'+str(binding.get('path',''))+':'+str(error)) from error
        try:
            package = read_package_bytes(root, binding['path'], binding['sha256'])
            if binding.get('bytes') is not None and len(package['raw']) != binding['bytes']:
                raise ValueError('CORRECTED_PG_PACKAGE_SIZE_MISMATCH')
            return package['raw']
        except (OSError, KeyError, ValueError) as package_error:
            error = package_error
        raise ValueError('CORRECTED_PG_INPUT_UNAVAILABLE:'+str(binding.get('path',''))+':'+str(error)) from error


def pg_json_source(root, relative_path):
    """Read an exact, previously ingressed project source; never fall back to disk."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_path, read_latest_candidate_path
    relative=Path(relative_path).as_posix()
    try:
        source=read_path(root,relative)
    except ValueError as error:
        if str(error)!='HISTORICAL_SOURCE_INGRESS_NOT_UNIQUE':raise
        source=read_latest_candidate_path(root,relative,
            source_origin='V4_CORRECTED_OWNER_CANDIDATE_OUTPUT')
    if not isinstance(source.get('value'), dict):
        raise ValueError('PG_JSON_SOURCE_NOT_OBJECT:' + str(relative_path))
    return source['value']


def gzwrite(root, path, rows, *, pg_ingress=False):
    raw = b''.join((json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode() for r in rows)
    compressed = gzip.compress(raw, mtime=0)
    from common.paths import resolve_tdx_root
    _atomic_write(path, compressed, tdx_root=resolve_tdx_root(root))
    if pg_ingress:
        from .r43_owner_replay import _ingress_candidate_bytes
        _ingress_candidate_bytes(root, path, compressed)
    return ref(root, path)


def _ingress_candidate_bytes(root, path, raw):
    """Register corrected-owner candidate bytes in PG and verify the exact readback."""
    import hashlib
    from workbench_db.v4_historical_source_ingress_pg_r1 import (
        MAX_INLINE_SOURCE_BYTES, ingest_captured_bytes, ingest_package_bytes,
        read_bound, read_package_bytes,
    )
    project = Path(root).resolve()
    relative = Path(path).resolve().relative_to(project).as_posix()
    sha = hashlib.sha256(raw).hexdigest()
    source_origin = 'V4_CORRECTED_OWNER_CANDIDATE_OUTPUT'
    if len(raw) > MAX_INLINE_SOURCE_BYTES:
        result = ingest_package_bytes(project, relative, raw, expected_sha256=sha,
            source_revision=sha, source_origin=source_origin)
        actual = read_package_bytes(project, relative, sha)['raw']
    else:
        result = ingest_captured_bytes(project, relative, raw, source_revision=sha,
            source_origin=source_origin)
        actual = read_bound(project, relative, sha)['raw']
    if (actual != raw or result['source_sha256'] != sha
            or result['source_bytes'] != len(raw)):
        raise ValueError('CORRECTED_OWNER_OUTPUT_PG_READBACK_MISMATCH:' + relative)


def write_candidate_json(root, path, value):
    """Write a local diagnostic copy and make the exact candidate receipt PG-readable."""
    write(path, value, project_root=root)
    _ingress_candidate_bytes(root, path, Path(path).read_bytes())
    return ref(root, path)


def gzrows(path):
    if hasattr(path,'read_bytes'):
        with gzip.GzipFile(fileobj=BytesIO(path.read_bytes()),mode='rb') as stream:
            for line in stream:
                if line.strip():yield json.loads(line)
    elif isinstance(path,(bytes,bytearray,memoryview)):
        with gzip.GzipFile(fileobj=BytesIO(path),mode='rb') as stream:
            for line in stream:
                if line.strip():yield json.loads(line)
    else:
        with gzip.open(path,'rb') as stream:
            for line in stream:
                if line.strip():yield json.loads(line)


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


def materialize_core(root, dates=None):
    root = Path(root).resolve(); policy = pg_json_source(root, CONTRACT)
    dates = dates or policy['target_sessions']; out = root/OUT; out.mkdir(parents=True, exist_ok=True)
    from workbench_db.dm01_data_accepted_head_pg_r1 import read_current
    head_state = read_current(root)
    head = head_state['candidate']
    protected = {'config/v4_joint_release_authority_v1.json': sha256_file(root/'config/v4_joint_release_authority_v1.json'),
                 'data/v4/V4_DATA_ACCEPTED_HEAD.json': head_state['head_sha256']}
    write_candidate_json(root,out/'ENTRY.json', dict(contract=ref(root,root/CONTRACT), upgrade_document='R4.1', phase0='DEGRADED_PASS',
          acceptance='IN_PROGRESS', observed_at=now(), protected=protected, next_stage='CORRECTED_STRUCTURE_AND_MEMBER_OWNERS'))
    identity = load(checked_pg(root,head['component_artifacts']['IDENTITY_UNIVERSE']))['rows']
    ids = {r['source_security_key'].lower():r for r in identity}
    sessions = official_sessions(root)
    required = sorted(set(dates) | {sessions[sessions.index(d)-k] for d in dates for k in (1,3,4,5)})
    from .r43_owner_replay import historical_source, _ZipReader, checked as checked_r43
    acquisition = historical_source(root,'acquisition')['value']
    batches = {}; universes = {}; bao_queries=[]
    for q in acquisition['queries']:
        if q.get('path') and q['method'] in ('query_daily_history_k_AStock','query_all_stock'):
            from workbench_db.v4_historical_source_ingress_pg_r1 import read_path
            payload=read_path(root,Path(q['path']).resolve().relative_to(root).as_posix())['value']; rows=payload.get('rows',[]); day=q['params'].get('date',q['params'].get('day'))
            if q['method']=='query_daily_history_k_AStock':batches[day]={r['code'].lower():r for r in rows}
            else:universes[day]={r['code'].lower():r for r in rows if is_stock_code(r['code'])}
            bao_queries.append(q)
    source_pointer=historical_source(root,'capture_audit')['value']
    capture=load(checked_pg(root,source_pointer['capture_receipt']))
    from io import BytesIO
    from workbench_db.v4_historical_source_ingress_pg_r1 import bound_bytes
    package=checked_r43(root,capture['package'])
    if capture['official_publication_date'] < max(dates):raise ValueError('OFFICIAL_PACKAGE_STALE')
    frozen_previous=historical_source(root,'core_replay')['value']['owners'][0]
    gbbq_binding=frozen_previous['sources']['gbbq']
    exact_gbbq=bound_bytes(root,gbbq_binding)
    blob=exact_gbbq.read_bytes()
    if hashlib.sha256(blob).hexdigest()!=gbbq_binding['sha256']:
        raise ValueError('CORRECTED_GBBQ_PG_INGRESS_READBACK_MISMATCH')
    from tdx.gbbq_reader import decode_gbbq_bytes
    events=defaultdict(list)
    for e in decode_gbbq_bytes(blob,source=gbbq_binding['path']):events[e.security_id.lower()].append(e)
    dispositions=pg_json_source(root,'config/v4_02_gbbq_price_impact_classification_v1.json')['dispositions']
    sources=dict(package=capture['package'],receipt=source_pointer['capture_receipt'],gbbq=gbbq_binding,
                 identity=head['component_artifacts']['IDENTITY_UNIVERSE'],contract=ref(root,root/CONTRACT),
                 core_kernel=ref(root,root/'src/v4/factors/core.py'),adjustment_kernel=ref(root,root/'src/adjustment/tdx_adjustment.py'))
    source_digest=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest()
    status=defaultdict(dict)
    historical=pg_json_source(root,'config/v4_sector_operational_authority_v1.json')['sources']['historical_status']
    historical_status_bytes=checked_pg(root,historical)
    for r in gzrows(historical_status_bytes):
        if r['status']=='SUSPENDED':status[r['security_id']][r['trade_date']]='SUSPENDED'
    chain=load(checked_pg(root,head['accepted_chain']))
    dated_identity={}
    for node in chain['nodes']:
        d=node['trade_date'];component=node['components']['IDENTITY_UNIVERSE']
        rs=load(checked_pg(root,dict(path=component['artifact_path'],sha256=component['artifact_sha256'])))['rows']
        dated_identity[d]={r['security_id'] for r in rs}
        component=node['components']['TRADING_STATUS']
        for r in load(checked_pg(root,dict(path=component['artifact_path'],sha256=component['artifact_sha256'])))['rows']:
            status[r['security_id']][d]=r['status']
    historical_universe=load(checked_pg(root,pg_json_source(root,'config/v4_market_operational_authority_v1.json')['market']))['sources']['historical_universe']
    historical_universe_bytes=checked_pg(root,historical_universe)
    for r in gzrows(historical_universe_bytes):
        if r['trade_date'] in required and r['board_scope'] in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT'):
            dated_identity.setdefault(r['trade_date'],set()).add(r['security_id'])
    for day,rows in batches.items():
        for code,r in rows.items():
            if code in ids:status[ids[code]['security_id']][day]='SUSPENDED' if r.get('tradestatus')=='0' else 'ACTUAL_TRADED'
    for day,rows in universes.items():dated_identity[day]={ids[c]['security_id'] for c in rows if c in ids}
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
            packed=z.read(name)
            eligible=0
            for bar in struct.iter_unpack('<IIIIIfII',packed):
                if bar[0]>int(max(dates).replace('-','')):break
                eligible+=1
            # Retain compact fixed-width source bytes; decode one security at a time.
            # Preserve enough actual bars for the original 250-bar Profile and period windows.
            start=max(0,eligible-420)*struct.calcsize('<IIIIIfII')
            cache[ids[code]['security_id']]=(code,packed[start:eligible*struct.calcsize('<IIIIIfII')])
    write_candidate_json(root,out/'SOURCE_BINDINGS.json',dict(sources=sources,unknown_canonical_identity=unknown_codes,
          query_receipts=bao_queries,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
    rps={}; receipts=[]; oracle=[]
    for target in required:
        rows=[]; prior_rows=[]; checks=Counter(); errors=[]; sample=[]; raw_rows=[]; adjusted_rows=[]
        previous=sessions[sessions.index(target)-1]
        members=dated_identity.get(target)
        if members is None:raise ValueError('NO_DATED_IDENTITY_UNIVERSE:'+target)
        for i in identity:
            sid=i['security_id']
            if sid not in members or sid not in cache:continue
            code,packed=cache[sid];raw=list(struct.iter_unpack('<IIIIIfII',packed));bs=transform_window(raw,events[code],dispositions,target)
            if not bs:continue
            revision=hashlib.sha256(json.dumps(dict(code=code,gbbq=sources['gbbq']['sha256'],
                events=[(e.event_date,e.category,e.c1,e.c2,e.c3,e.c4) for e in events[code]
                        if e.event_date<=int(target.replace('-','')) and e.category==1]),sort_keys=True).encode()).hexdigest()
            basis='TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE:'+revision
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
            pv={k:asdict(v) for k,v in compute_core(obs,sid,asof=previous).items()} if obs[0].trade_date<=previous else {}
            prior_rows.append(dict(security_id=sid,trade_date=previous,coordinate_target=target,price_basis_id=basis,fields=pv))
            b=by.get(target)
            if b:
                raw_rows.append(dict(security_id=sid,trade_date=target,**dict(zip(('open','high','low','close'),b['raw_ohlc'])),amount=b['amount'],volume=b['volume']))
                adjusted_rows.append(dict(security_id=sid,trade_date=target,**dict(zip(('open','high','low','close'),b['qfq_ohlc'] or [None]*4)),qfq_mul=b['qfq_mul'],qfq_add=b['qfq_add'],price_basis='TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE',adjustment_source_revision=revision,adjustment_readiness='READY' if b['qfq_ohlc'] else 'UNKNOWN'))
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
        def history_rows():
            for identity_row in identity:
                sid=identity_row['security_id']
                if sid not in members or sid not in cache:continue
                code,packed=cache[sid]
                bars=transform_window(list(struct.iter_unpack('<IIIIIfII',packed)),events[code],dispositions,target)
                if bars:yield dict(security_id=sid,bars=bars)
        receipt=dict(trade_date=target,rows=len(rows),source_digest=source_digest,sources=sources,
             core=gzwrite(root,folder/'core.jsonl.gz',rows,pg_ingress=True),prior_core=gzwrite(root,folder/'prior_core_target_coordinate.jsonl.gz',prior_rows,pg_ingress=True),
             history=gzwrite(root,folder/'history.jsonl.gz',history_rows(),pg_ingress=True),
             raw=gzwrite(root,folder/'raw.jsonl.gz',raw_rows,pg_ingress=True),adjusted=gzwrite(root,folder/'adjusted.jsonl.gz',adjusted_rows,pg_ingress=True),
             actual_raw_rows=len(raw_rows),adjustment_current_ready=sum(r['adjustment_readiness']=='READY' for r in adjusted_rows),
             known_fields=dict(Counter(k for r in rows for k,v in r['fields'].items() if v.get('value') is not None)),
             knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,publication_state='STAGING_NOT_ACCEPTED')
        write_candidate_json(root,folder/'OWNER.json',receipt);receipts.append(receipt)
        oracle.append(dict(trade_date=target,checks=dict(checks),errors=errors,samples=sample,result='PASS' if not errors else 'FAIL'))
        print(json.dumps(dict(stage='CORE',date=target,rows=len(rows),raw=len(raw_rows),known=receipt['known_fields'],errors=len(errors))),flush=True)
        if errors:raise ValueError('INDEPENDENT_CORE_ORACLE_FAILED:'+target)
    write_candidate_json(root,out/'CORE_REPLAY.json',dict(contract='V4_CORRECTED_OWNER_REPLAY_V1',owners=receipts,oracle=oracle,
          protected=protected,heads_unchanged=all(sha256_file(root/p)==h for p,h in protected.items()),
          acceptance='PASS_CORRECTED_CORE_NUMERIC_ORACLE',next_stage='PROFILE_STRUCTURE_SECTOR_FOCUS_FORWARD'))
    return receipts
