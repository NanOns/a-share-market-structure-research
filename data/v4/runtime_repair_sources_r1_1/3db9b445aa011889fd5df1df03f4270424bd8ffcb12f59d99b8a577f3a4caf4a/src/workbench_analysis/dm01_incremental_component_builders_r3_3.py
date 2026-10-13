from __future__ import annotations

"""Nine static, target-session adapters around exact-bound accepted domain kernels.

This module only writes immutable candidate artifacts. It has no accepted-head writer.
All filesystem inputs are digest-bound; parent aggregates are consumed without replaying
the historical daily series. Candidate and accepted publication namespaces are separate.
"""
from collections import Counter, namedtuple
from copy import deepcopy
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.v4_02_build_raw_selected_v2 import date_identity, check_raw_quality
from scripts.build_v4_02_formal_periods import period_key, natural_period_end
from scripts.build_v4_02_price_limits_generic import apply_row_runtime
from adjustment.tdx_adjustment import build_affine_factors, adjust_ohlc, xrxd_from_gbbq
from tdx.gbbq_reader import read_gbbq
from workbench_analysis.daily_data_head import CAPABILITIES
from workbench_analysis.daily_increment_builder import _atomic_bytes
from workbench_analysis.daily_source_freeze import ensure_outside_tdx, source_freeze_complete_v2
from workbench_analysis.daily_source_manifests import build_current_lifecycle_snapshot
from workbench_analysis.dm01_extracted_domain_r1 import (
    classify_dated_status, dated_isst_fact, accumulate_period_bar, evaluate_price_base)
from workbench_analysis.limit_rules import LimitStateService
from workbench_analysis.price_reference_state import PreviousCloseState
from workbench_analysis.v4_02_closure import ex_right_reference_price
from workbench_analysis.special_price_phases import SpecialPhaseEventStore, PhasePolicyRegistry

ROOT=Path(__file__).resolve().parents[2]
CONTRACT_PATH='config/dm01_incremental_builders_contract_r3_3.json'
TDX_ROOT=Path('D:/new_tdx')

class ComponentBuildError(ValueError):
    pass

def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def artifact_reference_path(path):
    try:return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:return str(Path(path).resolve())

def bound_path(ref):
    path=Path(ref['path'])
    if not path.is_absolute():path=ROOT/path
    if not path.is_file() or sha(path)!=ref.get('sha256'):
        raise ComponentBuildError('INPUT_PUBLICATION_DIGEST_MISMATCH:'+str(ref.get('path')))
    return path

def load(ref):
    return json.loads(bound_path(ref).read_text(encoding='utf8'))

def _write_immutable(path,value,tdx_roots=()):
    for root in (TDX_ROOT,*tdx_roots):ensure_outside_tdx(path,Path(root))
    data=canonical(value)+b'\n'
    if path.exists():
        if path.read_bytes()!=data:raise ComponentBuildError('IMMUTABLE_CANDIDATE_COLLISION')
    else:_atomic_bytes(path,data,tdx_root=TDX_ROOT)
    return hashlib.sha256(data).hexdigest()

def resolve_target_session(parent_date,calendar_binding,observed_at,requested_target=None):
    now=datetime.fromisoformat(observed_at.replace('Z','+00:00'))
    if now.tzinfo is None:raise ComponentBuildError('OBSERVATION_TIMEZONE_REQUIRED')
    local=now.astimezone(ZoneInfo('Asia/Shanghai'))
    sessions=calendar_binding['session_dates']
    if sessions!=sorted(set(sessions)):raise ComponentBuildError('CALENDAR_SESSIONS_NOT_CANONICAL')
    for d in sessions:date.fromisoformat(d)
    target=next((d for d in sessions if d>parent_date),None)
    if not target:raise ComponentBuildError('BLOCKED_CALENDAR_COVERAGE')
    if requested_target and requested_target!=target:
        raise ComponentBuildError('BLOCKED_MISSING_INTERMEDIATE_SESSION:'+target)
    if target>local.date().isoformat() or (target==local.date().isoformat() and local.time()<time(15)):
        raise ComponentBuildError('WAIT_MARKET_CLOSE')
    return target

def _context(cap,target,parent,freeze,calendar,identity,staging):
    from .dm01_chain_contract_r3_3 import validate_context
    return validate_context(cap,target,parent,freeze,calendar,identity,staging)

def _input(c,name):
    ref=c['freeze']['inputs'].get(name)
    if not ref:raise ComponentBuildError('REQUIRED_INPUT_MISSING:'+name)
    return load(ref)

def _dependency(c,cap):
    ref_path=c['staging']/cap/'receipt.json'
    if not ref_path.exists():raise ComponentBuildError('DEPENDENCY_NOT_BUILT:'+cap)
    r=json.loads(ref_path.read_text(encoding='utf8'))
    if r['parent_data_head_digest']!=c['parent']['binding']['sha256'] or r['source_revision']!=c['freeze']['manifest_sha256']:
        raise ComponentBuildError('DEPENDENCY_PUBLICATION_MISMATCH:'+cap)
    rows=load(dict(path=r['artifact_path'],sha256=r['artifact_sha256']))['rows']
    if digest(rows)!=r['logical_digest'] or len(rows)!=r['row_count']:
        raise ComponentBuildError('DEPENDENCY_LOGICAL_DIGEST_MISMATCH:'+cap)
    return rows,r

def _parent_component(c,cap):
    ref=c['parent']['components'].get(cap)
    if not ref:raise ComponentBuildError('PARENT_COMPONENT_MISSING:'+cap)
    manifest=load(c['parent']['component_manifest_binding'])
    if manifest.get('parent_data_head_digest')!=c['parent']['binding']['sha256'] or manifest.get('components',{}).get(cap)!=ref:
        raise ComponentBuildError('PARENT_COMPONENT_PUBLICATION_MISMATCH:'+cap)
    value=load(ref)
    if value.get('trade_date')!=c['parent']['head']['accepted_trade_date']:
        raise ComponentBuildError('PARENT_COMPONENT_DATE_MISMATCH:'+cap)
    return value,ref

def _key(row):
    return str(row.get('security_id') or 'SOURCE:'+str(row.get('source_security_key','')))

def _unique(rows,period=False):
    keys=[(_key(r),r.get('period_type'),r.get('period_key')) if period else (_key(r),r.get('trade_date')) for r in rows]
    if len(keys)!=len(set(keys)):raise ComponentBuildError('DUPLICATE_COMPONENT_KEY')

def _finish(c,rows,extra=None):
    _unique(rows,c['cap'].startswith('PERIOD_'))
    rows=sorted(rows,key=lambda r:(_key(r),r.get('period_type',''),r.get('period_key','')))
    for r in rows:
        if c['cap'].startswith('PERIOD_') and r.get('period_view')=='CLOSED_ONLY' and r.get('as_of_date')!=c['target']: continue
        r['knowledge_lineage']='RECONSTRUCTED_CORRECTED'; r['AS_RECORDED']=False; r['first_available_at_target_proven']=False
    row_digest=digest(rows)
    payload=dict(contract_id='DM01_'+c['cap']+'_ARTIFACT_R3_3',trade_date=c['target'],rows=rows,**(extra or {}))
    path=c['staging']/c['cap']/'artifact.json'
    file_sha=_write_immutable(path,payload,c['freeze'].get('tdx_roots',[]))
    unknown=Counter(str(r['unknown_reason']) for r in rows if r.get('unknown_reason'))
    quality=Counter(str(r.get('quality') or r.get('status') or 'READY') for r in rows)
    receipt=dict(component_id=c['cap'],contract_id='DM01_'+c['cap']+'_INCREMENT_R3_3',version='3.2.0',
        status='DEGRADED_PASS' if unknown else 'FULL_PASS',target_trade_date=c['target'],trade_date=c['target'],
        parent_data_head_digest=c['parent']['binding']['sha256'],source_revision=c['freeze']['manifest_sha256'],
        calendar_publication_id=c['calendar']['publication_id'],identity_publication_id=c['identity']['publication_id'],
        runtime_bindings=c['contract']['capabilities'][c['cap']]['runtime_bindings'],
        accepted_owner_stage=c['contract']['capabilities'][c['cap']]['owner_stage'],
        accepted_algorithm_contract=c['contract']['capabilities'][c['cap']]['accepted_algorithm_contract'],
        input_publication_ids=sorted(set([c['parent']['binding']['sha256'],c['freeze']['manifest_sha256'],
            c['calendar']['publication_id'],c['identity']['publication_id'],
            *[ref['sha256'] for ref in c['freeze']['inputs'].values()]])),
        artifact_path=artifact_reference_path(path),artifact_sha256=file_sha,artifact_bytes=path.stat().st_size,logical_digest=row_digest,row_count=len(rows),
        quality_counts=dict(quality),unknown_reason_counts=dict(unknown),
        parent_component_bindings=c['parent']['components'],candidate_only=True,
        fixture_scope=c['freeze'].get('fixture_scope'),market_acceptance_claim=False)
    from workbench_analysis.dm01_independent_postcheck_r3_3 import check_component
    post=check_component(receipt,payload,c['freeze'],c['parent'],c['calendar'],c['identity'])
    if post['status']!='PASS':raise ComponentBuildError('INDEPENDENT_COMPONENT_POSTCHECK:'+str(post['errors']))
    receipt['postcheck_digest']=digest(post)
    _write_immutable(c['staging']/c['cap']/'postcheck.json',post,c['freeze'].get('tdx_roots',[]))
    _write_immutable(c['staging']/c['cap']/'receipt.json',receipt,c['freeze'].get('tdx_roots',[]))
    return receipt

def build_identity_universe(target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root):
    c=_context('IDENTITY_UNIVERSE',target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root)
    prior,ref=_parent_component(c,'IDENTITY_UNIVERSE'); bao=_input(c,'BAOSTOCK_DAILY_UPDATE')
    lifecycle=build_current_lifecycle_snapshot(trade_date=c['target'],baseline_date=parent_data_head['head']['accepted_trade_date'],
        baseline_data_head=parent_data_head['head'],parent_universe_rows=prior['rows'],identity_records=identity_binding['records'],
        baostock_snapshot=bao,official_session_bridge=dict(status='PASS',latest_completed_official_session=parent_data_head['head']['accepted_trade_date'],
            official_sessions_after_base_cutoff=[d for d in calendar_binding['session_dates'] if d>parent_data_head['head']['accepted_trade_date']]),
        source_evidence=dict(baseline_data_head_sha256=parent_data_head['binding']['sha256'],parent_universe=ref,
            identity=identity_binding['binding'],baostock=source_freeze['inputs']['BAOSTOCK_DAILY_UPDATE']),observed_at=source_freeze['observed_at'])
    by_key={str(r.get('source_security_key') or r.get('symbol')).upper():r for r in identity_binding['records']
            if str(r.get('symbol_effective_from') or r.get('effective_from') or r.get('list_date') or '')<=c['target']
            and (not (r.get('symbol_effective_to') or r.get('effective_to') or r.get('delist_date'))
                 or str(r.get('symbol_effective_to') or r.get('effective_to') or r.get('delist_date'))>=c['target'])}
    rows=lifecycle['source_rows'];present={r['source_security_key'] for r in rows}
    # Roster absence alone cannot remove the accepted parent identity.
    for r in prior['rows']:
        key=r['source_security_key'].upper()
        if key not in present and key in by_key:
            rows.append(dict(trade_date=c['target'],source_security_key=key,security_id=r.get('security_id'),
                identity_status='IDENTITY_BOUND_ROSTER_ABSENT',unknown_reason='ROSTER_ABSENCE_IS_NOT_DELISTING'))
    for r in rows:
        record=by_key.get(r['source_security_key'],{})
        r.update(board_scope=record.get('board_scope') or record.get('board'),security_type=record.get('security_type','UNKNOWN'),
            list_date=record.get('list_date'),delist_date=record.get('delist_date'),
            knowledge_time=record.get('system_available_at'),knowledge_lineage='TARGET_DATED_IDENTITY_NOT_HISTORICAL_BACKFILL',
            parent_universe_publication=ref['sha256'],absence_is_delisting_evidence=False)
        if not r.get('security_id'):r['unknown_reason']=r.get('reason') or 'IDENTITY_UNKNOWN'
        if r['security_type']=='UNKNOWN' or not r['knowledge_time']:
            r['unknown_reason']=r.get('unknown_reason') or 'DATED_IDENTITY_TYPE_OR_KNOWLEDGE_UNKNOWN'
    return _finish(c,rows,dict(lifecycle_event_status=lifecycle['event_status'],boundary_events=lifecycle['boundary_events']))

def build_raw_daily(target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root):
    c=_context('RAW_DAILY',target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root)
    delta=_input(c,'TDX_PACKAGE_DELTA');universe,_=_dependency(c,'IDENTITY_UNIVERSE')
    if delta.get('contract_id')!='TDX_PACKAGE_DELTA_V1' or delta.get('status')!='READY' or delta.get('target_date')!=c['target']:
        raise ComponentBuildError('TDX_TARGET_DATE_DELTA_NOT_READY')
    expected=source_freeze['source_families']['TDX_FULL_PACKAGE']
    if delta.get('current_snapshot_id')!=expected['source_revision'] or expected['sha256']!=str(delta['current_snapshot_id']).removeprefix('sha256-'):
        raise ComponentBuildError('OFFICIAL_PACKAGE_IDENTITY_MISMATCH')
    u={r['source_security_key']:r for r in universe}; rows=[]
    for bar in delta['target_bars']:
        key=str(bar.get('source_security_key') or bar['security_id']).upper()
        if key.startswith('BJ.'):continue
        if key not in u:raise ComponentBuildError('RAW_OUTSIDE_IDENTITY_UNIVERSE')
        if int(bar['trade_date'])!=int(c['target'].replace('-','')):raise ComponentBuildError('RAW_TARGET_DATE_MISMATCH')
        member=u[key]
        intervals={key:[dict(normalized_effective_from=c['target'],normalized_effective_to=c['target'],security_id=member['security_id'],
            source_revision_id=identity_binding['publication_id'])]} if member.get('security_id') else {}
        sid,quality,basis,rev=date_identity(key,int(bar['trade_date']),intervals)
        prices=[bar[x] for x in ('open','high','low','close')]
        q=check_raw_quality((int(bar['trade_date']),*prices,bar['amount'],bar['volume'],0))
        r=dict(security_id=sid,source_security_key=key,trade_date=c['target'],board_scope=member['board_scope'],
            **{x:bar[x] for x in ('open','high','low','close','volume','amount')},
            source_authority='TDX_OFFICIAL_PACKAGE',source_snapshot_id=delta['current_snapshot_id'],
            source_digest=source_freeze['inputs']['TDX_PACKAGE_DELTA']['sha256'],record_quality=q,identity_quality=quality,
            membership_basis=basis,identity_source_revision=rev,bao_stock_ohlc_substitution_permitted=False,
            amount_unit='TDX_SOURCE_NATIVE',volume_unit='TDX_SOURCE_NATIVE')
        if q!='SOURCE_FILE_VALIDATED_RECORD' or not sid:r['unknown_reason']=q if q!='SOURCE_FILE_VALIDATED_RECORD' else 'IDENTITY_UNKNOWN'
        rows.append(r)
    if not rows:raise ComponentBuildError('RAW_TARGET_ROWS_EMPTY')
    return _finish(c,rows)

def _bao_rows(c):
    bao=_input(c,'BAOSTOCK_DAILY_UPDATE')
    if bao.get('trade_date')!=c['target'] or bao.get('provider_date')!=c['target'] or bao.get('status') not in ('BAOSTOCK_DAILY_SNAPSHOT_READY','NOOP_SOURCE_ALREADY_FROZEN'):
        raise ComponentBuildError('DATED_PROVIDER_TARGET_MISMATCH')
    result={}
    for r in bao.get('daily_rows',[]):
        key=str(r.get('code') or '').upper()
        if r.get('date')!=c['target'] or not key or key in result:raise ComponentBuildError('PROVIDER_DATE_OR_DUPLICATE')
        result[key]=r
    return result

def build_trading_status(target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root):
    c=_context('TRADING_STATUS',target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root)
    raw,_=_dependency(c,'RAW_DAILY');universe,_=_dependency(c,'IDENTITY_UNIVERSE');bao=_bao_rows(c)
    facts={(key.lower(),c['target']):(str(r['tradestatus']),str(r['isST'])) for key,r in bao.items()
           if str(r.get('tradestatus')) in ('0','1') and str(r.get('isST')) in ('0','1')}
    present={r['source_security_key'] for r in raw};rows=[]
    for member in universe:
        out,conflicts=classify_dated_status(dict(member,source_bar_present=member['source_security_key'] in present),facts)
        out.update(actual_bar_present=member['source_security_key'] in present,provider_conflicts=conflicts,
                   status_conflict=bool(conflicts),knowledge_time=c['freeze']['system_available_at'])
        if out['status'] in ('DATA_GAP','UNKNOWN'):out['unknown_reason']='MISSING_BAR_'+out['status']
        elif conflicts:out['unknown_reason']='PROVIDER_STATUS_CONFLICT_LOCAL_BAR_PRECEDENCE'
        rows.append(out)
    return _finish(c,rows)

def build_isst(target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root):
    c=_context('ISST',target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root)
    universe,_=_dependency(c,'IDENTITY_UNIVERSE');bao=_bao_rows(c);rows=[]
    for member in universe:
        provider=bao.get(member['source_security_key'])
        if provider and (str(provider.get('isST')) not in ('0','1') or str(provider.get('tradestatus')) not in ('0','1')):provider=None
        row=dated_isst_fact(member,c['target'],provider,c['freeze']['inputs']['BAOSTOCK_DAILY_UPDATE']['sha256'])
        row['knowledge_time']=c['freeze']['system_available_at'];row['historical_backfill_permitted']=False
        if row['is_st'] is None:row['unknown_reason']='DATED_ST_UNAVAILABLE'
        rows.append(row)
    return _finish(c,rows)

def _actions(c):
    ref=c['freeze']['inputs'].get('GBBQ')
    if not ref:raise ComponentBuildError('ACCEPTED_GBBQ_MISSING')
    meta=_input(c,'GBBQ_DISPOSITIONS')
    if meta.get('first_eligible_formal_trade_date','9999')>c['target']:
        raise ComponentBuildError('GBBQ_NOT_ELIGIBLE_AT_TARGET')
    if meta.get('gbbq_sha256')!=ref['sha256']:raise ComponentBuildError('GBBQ_DISPOSITION_SOURCE_MISMATCH')
    classification=load(c['contract']['gbbq_classification_binding'])
    accepted_categories={k:v['formal_disposition'] for k,v in classification['dispositions'].items()}
    if meta.get('category_dispositions')!=accepted_categories:
        raise ComponentBuildError('GBBQ_CATEGORY_DISPOSITION_NOT_ACCEPTED')
    events={}
    for r in read_gbbq(bound_path(ref)):
        if r.event_date<=int(c['target'].replace('-','')):events.setdefault(r.security_id.upper(),[]).append(r)
    dispositions={r['security_id']:dict(r) for r in meta['rows']}
    universe,_=_dependency(c,'IDENTITY_UNIVERSE')
    for r in universe:
        if r.get('security_id') in dispositions:
            d=dispositions[r['security_id']]
            actual_blockers=[e.category for e in events.get(r['source_security_key'],[]) if accepted_categories.get(str(e.category),'UNKNOWN_PRICE_IMPACT') in
                             ('UNKNOWN_PRICE_IMPACT','PRICE_AFFECTING_UNSUPPORTED')]
            d['blocking_categories']=sorted(set([*d.get('blocking_categories',[]),*actual_blockers]))
    return events,dispositions

def build_adjusted_daily(target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root):
    c=_context('ADJUSTED_DAILY',target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root)
    raw,raw_receipt=_dependency(c,'RAW_DAILY');events,dispositions=_actions(c);rows=[]
    for r in raw:
        disp=dispositions.get(r['security_id']);blocked=disp is None or bool(disp.get('blocking_categories')) or r.get('unknown_reason')
        out=dict(r,raw_daily_digest=raw_receipt['logical_digest'],price_basis='TDX_NATIVE_AFFINE_QFQ',
                 adjustment_readiness='UNKNOWN' if blocked else 'READY',adjustment_source_revision=c['freeze']['inputs']['GBBQ']['sha256'])
        if blocked:
            out.update(**{p:None for p in ('open','high','low','close')},unknown_reason='UNSUPPORTED_OR_UNPROVED_ADJUSTMENT',qfq_mul=None,qfq_add=None)
        else:
            factors=build_affine_factors([int(c['target'].replace('-',''))],[xrxd_from_gbbq(e) for e in events.get(r['source_security_key'],[]) if e.category==1])
            factor=factors[int(c['target'].replace('-',''))];prices=adjust_ohlc(r,factor)
            out.update(**{p:str(v) for p,v in prices.items()},qfq_mul=str(factor.qfq_mul),qfq_add=str(factor.qfq_add))
        rows.append(out)
    return _finish(c,rows,dict(raw_daily_artifact_sha256=raw_receipt['artifact_sha256']))

class _DigestChain:
    """Versioned lineage extension; original aggregate digest is a frozen parent, never a resumable hash."""
    def __init__(self,parent_digest):self.parent=parent_digest;self.parts=[]
    def update(self,data):self.parts.append(data.hex())
    def hexdigest(self):return digest(dict(protocol='DM01_PERIOD_PARENT_PLUS_TARGET_R1',parent=self.parent,target=self.parts))

def _build_period(c,adjusted):
    cap=c['cap'];daily,dr=_dependency(c,'ADJUSTED_DAILY' if adjusted else 'RAW_DAILY')
    statuses,_=_dependency(c,'TRADING_STATUS');u,_=_dependency(c,'IDENTITY_UNIVERSE')
    prior,pr=_parent_component(c,cap);target_num=int(c['target'].replace('-',''));sessions=c['calendar']['session_dates']
    _unique(prior['rows'],True)
    rows=[];current={}; pdate=c['parent']['head']['accepted_trade_date'];basis='QFQ' if adjusted else 'RAW'
    for r in prior['rows']:
        key=(r['security_id'],r['period_type'],r['period_key'])
        if key in current:raise ComponentBuildError('PARENT_PERIOD_KEY_DUPLICATE')
        if r.get('period_end_date',pdate)<=pdate and r.get('period_view')=='CLOSED_ONLY':rows.append(deepcopy(r))
        else:
            if r.get('as_of_date')!=pdate or r.get('parent_daily_cutoff',pdate)!=pdate:
                raise ComponentBuildError('PARENT_PERIOD_ASOF_MISMATCH')
            current[key]=deepcopy(r)
    bars={_key(r):r for r in daily};status_by={_key(r):r for r in statuses}
    action_events,_=_actions(c) if adjusted else ({},{})
    for member in u:
        sid=_key(member);bar=bars.get(sid);status=status_by[sid]['status']
        for kind in ('WEEKLY','MONTHLY'):
            pk=period_key(target_num,kind);key=(sid,kind,pk)
            # Close an earlier partial period using only the frozen accepted calendar.
            for oldkey,r in list(current.items()):
                if oldkey[0]==sid and oldkey[1]==kind and oldkey[2]!=pk:
                    eligible=[d for d in sessions if period_key(int(d.replace('-','')),kind)==oldkey[2]]
                    if not eligible or max(eligible)>pdate:raise ComponentBuildError('PARENT_PERIOD_STATE_DISCONTINUITY')
                    r.update(period_end_date=max(eligible),period_view='CLOSED_ONLY')
                    if r.get('period_status')=='AS_OF_PARTIAL_READY':r['period_status']='CLOSED_ONLY_READY'
                    rows.append(r);del current[oldkey]
            old=current.pop(key,None)
            if old and (old.get('as_of_date')!=pdate or old.get('parent_daily_cutoff',pdate)!=pdate):
                raise ComponentBuildError('PARENT_PERIOD_ASOF_MISMATCH')
            if old and old.get('price_basis')!=basis:raise ComponentBuildError('PARENT_PERIOD_PRICE_BASIS_MISMATCH')
            pp={kind:{}};agg=None
            if old and old.get('actual_count',0):
                prices={p:(Decimal(str(old[p])) if old[p] is not None else None) for p in ('open','high','low','close')}
                if adjusted and all(v is not None for v in prices.values()):
                    ev=[xrxd_from_gbbq(e) for e in action_events.get(member['source_security_key'],[]) if e.category==1 and e.event_date>int(pdate.replace('-',''))]
                    factor=build_affine_factors([int(pdate.replace('-','')),target_num],ev)[int(pdate.replace('-',''))]
                    prices=adjust_ohlc(prices,factor)
                agg=dict(first_date=int(old['first_source_date'].replace('-','')),max_date=int(old['max_source_date'].replace('-','')),
                    **prices,volume=old['volume'],amount=old['amount'],actual=old['actual_count'],digest=_DigestChain(old['source_daily_digest']))
                pp[kind][(pk,basis)]=agg
            if bar and bar.get('record_quality')=='SOURCE_FILE_VALIDATED_RECORD':
                vals=[Decimal(str(bar[p])) if bar[p] is not None else None for p in ('open','high','low','close')]
                agg=accumulate_period_bar(pp,kind,pk,basis,target_num,vals,bar['volume'],float(bar['amount']))
                if not isinstance(agg['digest'],_DigestChain):
                    # The original domain hash for a new period is exact; existing periods use an explicit parent chain.
                    pass
            dates=[d for d in sessions if period_key(int(d.replace('-','')),kind)==pk]
            if not dates:raise ComponentBuildError('PERIOD_CALENDAR_COVERAGE_MISSING')
            natural=natural_period_end(pk,kind);natural_iso=f'{natural//10000:04d}-{natural//100%100:02d}-{natural%100:02d}'
            end=max(dates);fully_covered=c['calendar']['coverage_end']>=natural_iso
            closed=fully_covered and end<=c['target']
            gap=(old or {}).get('data_gap_count',0)+int(status=='DATA_GAP')
            unknown=(old or {}).get('unknown_count',0)+int(status=='UNKNOWN')
            unready=bool(bar and bar.get('unknown_reason')) or bool(old and old.get('unknown_reason'))
            out=dict(security_id=sid,source_security_key=member['source_security_key'],period_type=kind,period_key=pk,
                trade_date=c['target'],as_of_date=c['target'],parent_daily_cutoff=c['target'],price_basis=basis,
                period_end_date=end if closed else natural_iso,period_view='CLOSED_ONLY' if closed else 'AS_OF_PARTIAL',
                **{p:str(agg[p]) if agg and agg[p] is not None and not unready else None for p in ('open','high','low','close')},
                volume=agg['volume'] if agg else (old or {}).get('volume',0),amount=agg['amount'] if agg else (old or {}).get('amount',0.0),
                actual_count=(old or {}).get('actual_count',0)+int(bar is not None),
                calendar_count=(old or {}).get('calendar_count',sum((old or {}).get(k,0) for k in ('actual_count','suspended_count','data_gap_count','unknown_count')))+1,
                suspended_count=(old or {}).get('suspended_count',0)+int(status=='SUSPENDED'),data_gap_count=gap,unknown_count=unknown,
                first_source_date=(f"{agg['first_date']//10000:04d}-{agg['first_date']//100%100:02d}-{agg['first_date']%100:02d}" if agg else None),
                max_source_date=(f"{agg['max_date']//10000:04d}-{agg['max_date']//100%100:02d}-{agg['max_date']%100:02d}" if agg else None),
                source_daily_digest=agg['digest'].hexdigest() if agg else digest(dict(parent=(old or {}).get('source_daily_digest'),no_actual_bar=True)),
                parent_period_publication=pr['sha256'],target_daily_publication=dr['logical_digest'])
            if unready or gap or unknown:out['unknown_reason']='ADJUSTMENT_OR_INVALID_DAILY_UNKNOWN' if unready else 'PERIOD_REQUIRED_STATUS_UNKNOWN'
            out['period_status']=('BLOCKED_BY_ADJUSTMENT' if unready else 'BLOCKED_BY_DATA_GAP' if gap
                else 'BLOCKED_BY_UNKNOWN_STATUS' if unknown else 'NO_ACTUAL_BARS' if out['actual_count']==0
                else 'CLOSED_ONLY_READY' if closed else 'AS_OF_PARTIAL_READY')
            rows.append(out)
    # Preserve inactive identities' previous state without adding fabricated target bars.
    rows.extend(current.values())
    return _finish(c,rows,dict(parent_period_publication=pr,source_daily_publication=dr['logical_digest']))

def build_period_raw(target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root):
    return _build_period(_context('PERIOD_RAW',target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root),False)

def build_period_adjusted(target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root):
    return _build_period(_context('PERIOD_ADJUSTED',target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root),True)

def _phase_inputs(c):
    manifest=_input(c,'SPECIAL_PRICE_PHASE')
    if manifest.get('contract_id')!='SPECIAL_PHASE_SOURCE_MANIFEST_V1' or manifest.get('trade_date')!=c['target'] or manifest.get('status')!='READY':
        raise ComponentBuildError('SPECIAL_PHASE_MANIFEST_NOT_READY')
    store=SpecialPhaseEventStore.from_jsonl(bound_path(manifest['event_store']))
    policies=PhasePolicyRegistry.from_json(bound_path(manifest['policy']))
    accepted=c['contract']['accepted_phase_bindings']
    if any(manifest[k]['sha256']!=accepted[k]['sha256'] for k in ('event_store','policy')):
        raise ComponentBuildError('SPECIAL_PHASE_NOT_ACCEPTED_EVENT_POLICY')
    for event in store.events:
        if event.phase_effective_from<=c['target'] and (event.phase_effective_to is None or c['target']<=event.phase_effective_to):
            if datetime.fromisoformat(event.system_available_at.replace('Z','+00:00'))>datetime.fromisoformat(c['freeze']['system_available_at'].replace('Z','+00:00')):
                raise ComponentBuildError('SPECIAL_PHASE_FUTURE_KNOWLEDGE')
    return store,policies

def build_special_phase(target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root):
    c=_context('SPECIAL_PHASE',target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root)
    universe,ur=_dependency(c,'IDENTITY_UNIVERSE');store,policies=_phase_inputs(c);rows=[]
    m=_input(c,'SPECIAL_PRICE_PHASE')
    if m.get('lifecycle_snapshot',{}).get('sha256')!=c['freeze']['source_families']['IDENTITY_LIFECYCLE']['sha256']:
        raise ComponentBuildError('SPECIAL_PHASE_LIFECYCLE_BINDING_MISMATCH')
    if set(m.get('active_security_ids',[]))!={r['security_id'] for r in universe if r.get('security_id')}:
        raise ComponentBuildError('SPECIAL_PHASE_ACTIVE_IDENTITY_MISMATCH')
    for member in universe:
        base=dict(member,limit_status='UNKNOWN',reason='IDENTITY_UNKNOWN' if not member.get('security_id') else None)
        result,phase,_=apply_row_runtime(base,store,policies,c['calendar']['session_dates'])
        result.update(quality='READY',event_manifest_digest=c['freeze']['inputs']['SPECIAL_PRICE_PHASE']['sha256'])
        if phase.value=='UNKNOWN_SPECIAL_PHASE' or not member.get('security_id'):result['unknown_reason']='SPECIAL_PHASE_OR_IDENTITY_UNKNOWN'
        rows.append(result)
    return _finish(c,rows)

def build_price_limit(target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root):
    c=_context('PRICE_LIMIT',target_trade_date,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root)
    universe,_=_dependency(c,'IDENTITY_UNIVERSE');raw,rr=_dependency(c,'RAW_DAILY');statuses,_=_dependency(c,'TRADING_STATUS');isst,_=_dependency(c,'ISST')
    prior,_=_parent_component(c,'PRICE_LIMIT');store,policies=_phase_inputs(c);rules=_input(c,'PRICE_RULES')['rules']
    if c['freeze']['inputs']['PRICE_RULES']['sha256']!=c['contract']['accepted_phase_bindings']['rules']['sha256']:
        raise ComponentBuildError('PRICE_RULES_NOT_ACCEPTED')
    service=LimitStateService(rules);events,disp=_actions(c);classifications=_input(c,'GBBQ_DISPOSITIONS')['category_dispositions']
    pmap={_key(r):r for r in prior['rows']};rmap={_key(r):r for r in raw};smap={_key(r):r for r in statuses};imap={_key(r):r for r in isst};rows=[]
    sessions=c['calendar']['session_dates'];index={d.replace('-',''):i for i,d in enumerate(sessions)};Action=namedtuple('Action','record event disposition')
    for member in universe:
        sid=_key(member);bar=rmap.get(sid);status=smap[sid]['status'];st=imap[sid]['is_st'];old=pmap.get(sid,{})
        state=PreviousCloseState(Decimal(str(old['next_reference_close'])) if old.get('next_reference_close') is not None else None,old.get('next_reference_blocked_by'))
        d=c['target'].replace('-','');actions=[Action(e,xrxd_from_gbbq(e) if e.category==1 else None,
            classifications.get(str(e.category),'UNKNOWN_PRICE_IMPACT')) for e in events.get(member['source_security_key'],[]) if str(e.event_date)==d]
        ref=state.apply_actions([(e.disposition,e.event) for e in actions],lambda value,ev:ex_right_reference_price(value,ev,'0.01'))
        result=dict(contract_id='PRICE_LIMIT_RULE_V1',security_id=member.get('security_id'),source_security_key=member['source_security_key'],
            trade_date=c['target'],board_scope=member['board_scope'],trading_status=status,is_st=st,risk_status=None,reference_price=None,
            reference_basis='UNKNOWN',rule_id=None,limit_up_price=None,limit_down_price=None,limit_status='UNKNOWN',reason=None)
        listing=member.get('list_date');first={sid:index[listing.replace('-','')]} if listing and listing.replace('-','') in index else {}
        actual=dict(raw_close=Decimal(str(bar['close'])),trade_date=d) if bar and not bar.get('unknown_reason') else None
        result=evaluate_price_base(result,status,actual,st,state,ref,actions,service,
            {sid:{str(member['delist_date']).replace('-','')}} if member.get('delist_date') else {},
            {sid} if not listing else set(),first,index)
        result,phase,_=apply_row_runtime(result,store,policies,sessions,close_lookup={(str(member.get('security_id')),c['target']):str(bar['close'])} if bar else {},standard_rules=rules)
        if bar and not bar.get('unknown_reason'):state.observe_actual_close(bar['close'])
        result.update(raw_daily_publication=rr['logical_digest'],next_reference_close=str(state.value) if state.value is not None else None,
            next_reference_blocked_by=state.blocked_by)
        if result['limit_status']=='UNKNOWN':result['unknown_reason']=result.get('reason') or 'PRICE_LIMIT_UNKNOWN'
        rows.append(result)
    return _finish(c,rows)

# Explicit allowlist; configuration cannot discover/import another implementation.
BUILDERS=dict(RAW_DAILY=build_raw_daily,IDENTITY_UNIVERSE=build_identity_universe,
    TRADING_STATUS=build_trading_status,ISST=build_isst,ADJUSTED_DAILY=build_adjusted_daily,
    PERIOD_RAW=build_period_raw,PERIOD_ADJUSTED=build_period_adjusted,PRICE_LIMIT=build_price_limit,SPECIAL_PHASE=build_special_phase)
BUILD_ORDER=('IDENTITY_UNIVERSE','RAW_DAILY','TRADING_STATUS','ISST','ADJUSTED_DAILY','PERIOD_RAW','PERIOD_ADJUSTED','PRICE_LIMIT','SPECIAL_PHASE')
