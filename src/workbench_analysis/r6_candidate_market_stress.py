"""Bounded, post-hoc market axes from date-bound candidate Owners (NON_PIT)."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import statistics
from datetime import datetime
from pathlib import Path

from v4.factors.native import market_axis_primitives, candidate_threshold
from v4.factors.native import market_trend_axis


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _checked(root, ref):
    root=Path(root).resolve();path=(root/ref['path']).resolve()
    if root not in path.parents:raise ValueError('R7_MARKET_STRESS_OWNER_PATH_ESCAPES_ROOT')
    size=path.stat().st_size
    if size!=ref.get('bytes',size):
        raise ValueError('R7_MARKET_STRESS_OWNER_BYTES_OR_SHA_MISMATCH')
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    if digest.hexdigest()!=ref['sha256']:
        raise ValueError('R7_MARKET_STRESS_OWNER_BYTES_OR_SHA_MISMATCH')
    return path


def _read_rows(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:return [json.loads(line) for line in stream]


def _iter_rows(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        for line in stream:
            if line.strip():yield json.loads(line)


def _selected_history_bars(path,required_sessions):
    """Stream the bound history and retain only dates needed by the T/T-3 formula.

    Duplicate security rows or duplicate bars in the calculation window must
    fail explicitly; dictionary construction must never silently choose the
    last source record.
    """
    required=set(required_sessions);selected={}
    for row in _iter_rows(path):
        sid=row.get('security_id')
        if not isinstance(sid,str) or not sid:
            raise ValueError('R7_MARKET_HISTORY_SECURITY_ID_MISSING')
        if sid in selected:
            raise ValueError('R7_MARKET_HISTORY_DUPLICATE_SECURITY_ID:'+sid)
        bars={}
        dated_bars=row.get('bars')
        if not isinstance(dated_bars,list):
            raise ValueError('R7_MARKET_HISTORY_BARS_INVALID:'+sid)
        for bar in dated_bars:
            if not isinstance(bar,dict):
                raise ValueError('R7_MARKET_HISTORY_BAR_INVALID:'+sid)
            day=bar.get('trade_date')
            if day not in required:continue
            if day in bars:
                raise ValueError('R7_MARKET_HISTORY_DUPLICATE_SECURITY_DATE:'+sid+':'+str(day))
            bars[day]=bar.get('qfq_ohlc')
        selected[sid]=bars
    return selected


def _comparison_universe(root,candidate,prior3,membership_ref):
    """Use the frozen four-board historical universe as the denominator.

    A predecessor Core is only a safe acceleration when its row-level date and
    board projection is exactly the same identity set as the bound historical
    universe.  A Core Owner is not itself a membership contract.
    """
    authoritative=set()
    for row in _iter_rows(_checked(root,membership_ref)):
        sid=row.get('security_id')
        if not sid or row.get('trade_date')!=prior3 or row.get('board_scope') not in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT'):
            continue
        if sid in authoritative:raise ValueError('R10_MARKET_HISTORICAL_UNIVERSE_DUPLICATE_ID:'+str(sid))
        authoritative.add(sid)
    if not authoritative:
        raise ValueError('R10_MARKET_HISTORICAL_UNIVERSE_DATE_SCOPE_EMPTY:'+str(prior3))
    predecessor=candidate.get('owners',{}).get(prior3,{}).get('core')
    if predecessor:
        core_universe=set()
        for row in _iter_rows(_checked(root,predecessor)):
            sid=row.get('security_id')
            if not sid or row.get('trade_date')!=prior3 or row.get('board_scope') not in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT'):
                continue
            if sid in core_universe:raise ValueError('R10_MARKET_CORE_UNIVERSE_DUPLICATE_ID:'+str(sid))
            core_universe.add(sid)
        if core_universe==authoritative:
            return core_universe,dict(contract_id='R10_MARKET_COMPARISON_UNIVERSE_V1',
                source='EXACT_CORE_PROJECTION',core=predecessor,historical_universe=membership_ref,
                trade_date=prior3,board_scope=['SH_MAIN','SZ_MAIN','STAR','CHINEXT'],
                identity_count=len(authoritative),identity_digest=hashlib.sha256(
                    _canonical(sorted(authoritative))).hexdigest(),membership_match=True)
        return authoritative,dict(contract_id='R10_MARKET_COMPARISON_UNIVERSE_V1',
            source='BOUND_HISTORICAL_UNIVERSE_CORE_MISMATCH',core=predecessor,
            historical_universe=membership_ref,trade_date=prior3,
            board_scope=['SH_MAIN','SZ_MAIN','STAR','CHINEXT'],identity_count=len(authoritative),
            identity_digest=hashlib.sha256(_canonical(sorted(authoritative))).hexdigest(),
            membership_match=False,core_only=sorted(core_universe-authoritative),
            historical_only=sorted(authoritative-core_universe))
    return authoritative,dict(contract_id='R10_MARKET_COMPARISON_UNIVERSE_V1',
        source='BOUND_HISTORICAL_UNIVERSE',historical_universe=membership_ref,trade_date=prior3,
        board_scope=['SH_MAIN','SZ_MAIN','STAR','CHINEXT'],identity_count=len(authoritative),
        identity_digest=hashlib.sha256(_canonical(sorted(authoritative))).hexdigest(),membership_match=None)


def candidate_breadth_formula_comparison(comparison, *, boundary):
    """Expose signed-SIGN and positive-indicator breadth on identical pairs."""
    if not isinstance(boundary,(int,float)) or isinstance(boundary,bool) or not math.isfinite(boundary) or boundary<0:
        raise ValueError('R7_BREADTH_THRESHOLD_INVALID')
    rows=list(comparison)
    if not rows:
        return dict(contract_id='S02_ADVANCERS_SHARE_DELTA3_R1',version='1.0.0',
            algorithm_id='ADVANCERS_SHARE_DELTA3',compatibility_formula='POSITIVE_INDICATOR',
            adjudication_status='DEV_CANDIDATE_VERSIONED',
            evaluable=0,threshold=boundary,threshold_parameter_id='V4_03_MARKET_BREADTH_AXIS',
            signed=dict(value=None,classification='UNKNOWN',formula='MEAN(SIGN(r_t)-SIGN(r_t_minus_3))'),
            positive_indicator=dict(value=None,classification='UNKNOWN',formula='MEAN(I(r_t>0)-I(r_t_minus_3>0))'),
            difference=None,zero_current=0,zero_comparison=0)
    sign_value=sum((1 if now>0 else -1 if now<0 else 0)-
                   (1 if old>0 else -1 if old<0 else 0) for now,old in rows)/len(rows)
    positive_value=sum((1 if now>0 else 0)-(1 if old>0 else 0) for now,old in rows)/len(rows)
    classify=lambda value:('IMPROVING' if value>boundary else 'DETERIORATING' if value< -boundary else 'STABLE')
    return dict(contract_id='S02_ADVANCERS_SHARE_DELTA3_R1',version='1.0.0',
        algorithm_id='ADVANCERS_SHARE_DELTA3',compatibility_formula='POSITIVE_INDICATOR',
        adjudication_status='DEV_CANDIDATE_VERSIONED',
        evaluable=len(rows),threshold=boundary,threshold_parameter_id='V4_03_MARKET_BREADTH_AXIS',
        signed=dict(value=sign_value,classification=classify(sign_value),formula='MEAN(SIGN(r_t)-SIGN(r_t_minus_3))'),
        positive_indicator=dict(value=positive_value,classification=classify(positive_value),formula='MEAN(I(r_t>0)-I(r_t_minus_3>0))'),
        difference=sign_value-positive_value,zero_current=sum(now==0 for now,_ in rows),
        zero_comparison=sum(old==0 for _,old in rows))


def _valid_sha(value):
    return isinstance(value,str) and re.fullmatch(r'[0-9a-fA-F]{64}',value) is not None


def _permission_chain_proven(chain, source_sha256, publication_id):
    """Read the exact candidate publication and verify its bound reference bytes.

    A caller-supplied permission flag or digest is never sufficient. The candidate
    Head, R8 receipt, source Owner, reference bytes, PG publication row and latest
    append-only FINALIZED event must all agree.
    """
    try:
        if not isinstance(chain,dict) or not isinstance(publication_id,str) or not _valid_sha(publication_id):
            return False
        root=Path(chain.get('candidate_root','')).resolve()
        day=chain.get('trade_date')
        if not day or not _valid_sha(source_sha256):return False
        head_path=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
        head_raw=head_path.read_bytes()
        if hashlib.sha256(head_raw).hexdigest()!=publication_id:return False
        head=json.loads(head_raw)
        if head.get('accepted_trade_date')!=day:return False
        receipt_path=root/'data/v4/r8_publication_bridge_v1/receipts'/f'{publication_id}.json'
        receipt=json.loads(receipt_path.read_bytes())
        if (receipt.get('contract_id')!='V4_R8_REAL_APPEND_PG_RECEIPT_R2'
                or receipt.get('status')!='PASS' or receipt.get('candidate_token')!=publication_id
                or receipt.get('trade_date')!=day or receipt.get('production_accepted') is not False
                or receipt.get('formal_head_modified') is not False
                or hashlib.sha256(head_raw).hexdigest()!=receipt.get('candidate_head_sha256')):
            return False

        def checked_ref(ref):
            if not isinstance(ref,dict):raise ValueError('REFERENCE_BINDING_MISSING')
            path=_checked(root,ref)
            return path

        owner_authority=receipt.get('owner_authority') or {}
        source_freeze=receipt.get('source_freeze') or {}
        transaction=receipt.get('publication_transaction') or {}
        if (not _valid_sha(owner_authority.get('sha256')) or not _valid_sha(source_freeze.get('sha256'))
                or not _valid_sha(transaction.get('sha256'))):return False
        checked_ref(owner_authority);checked_ref(source_freeze)
        transaction_path=checked_ref(transaction)
        tx=json.loads(transaction_path.read_bytes())
        if tx.get('state')!='COMMITTED' or tx.get('candidate_token')!=publication_id:return False

        market_binding=(head.get('owners',{}).get(day) or {}).get('market')
        if not isinstance(market_binding,dict):return False
        market=json.loads(_checked(root,market_binding).read_bytes())
        if market.get('trade_date')!=day:return False
        ref_bindings=[item for item in market.get('input_bindings',[])
            if Path(item.get('path','')).name.startswith('V4_03_MARKET_REFERENCE_PATH_CANDIDATE')]
        if len(ref_bindings)!=1:return False
        ref_binding=ref_bindings[0]
        if ref_binding.get('sha256')!=source_sha256:return False
        reference_path=_checked(root,ref_binding)
        with gzip.open(reference_path,'rt',encoding='utf-8') as stream:
            rows=[json.loads(line) for line in stream if line.strip()]
        from workbench_analysis.market_source_acquisition import official_sessions
        sessions=[session for session in official_sessions(root) if session<=day]
        if len(sessions)<25:return False
        window=sessions[-25:]
        by_day={}
        for row in rows:
            if row.get('trade_date') in window:
                if row['trade_date'] in by_day:return False
                by_day[row['trade_date']]=row
        if list(sorted(by_day))!=window:return False
        chosen=[by_day[session] for session in window]
        identity_keys=('series_version','path_identity','market_calendar_id')
        first=chosen[0]
        if (not first.get('adjustment_basis_id') or any(
                any(row.get(key)!=first.get(key) for key in identity_keys)
                or not row.get('adjustment_basis_id')
                or row.get('quality_state')!='OBSERVED'
                or not isinstance(row.get('level'),(int,float))
                or isinstance(row.get('level'),bool) or not math.isfinite(row.get('level'))
                or row.get('level')<=0 for row in chosen)):
            return False
        values=[float(row['level']) for row in chosen]
        expected=dict(trade_date=day,series_id=first['path_identity']+':'+first['series_version'],
            price_basis_id=chosen[-1]['adjustment_basis_id'],market_calendar_id=first['market_calendar_id'],
            index_close=values[-1],index_ma20=sum(values[-20:])/20,
            index_ma20_t_minus_5=sum(values[:20])/20)
        if any(chain.get(key)!=value for key,value in expected.items()):return False

        from workbench_db.v4_native import connection,workspace_schema
        from workbench_db.v4_forward_pg_r1 import ForwardFactStore
        schema=receipt.get('pg_schema')
        expected_schema=workspace_schema(root/'data/v4/r8_publication_bridge_v1','r8pub')
        if schema!=expected_schema:return False
        with connection(schema,read_only=True) as pg:
            if ForwardFactStore._database_identity(pg)!=receipt.get('pg_database_identity'):return False
            row=pg.execute('SELECT candidate_token,trade_date::text,predecessor_head_sha256,candidate_head_sha256,owner_authority_sha256,source_freeze_sha256,readback,inserted_at::text FROM r8_publications WHERE candidate_token=%s AND trade_date=%s',
                (publication_id,day)).fetchone()
            event=pg.execute('SELECT event_type,row_sha256,evidence,inserted_at::text FROM r8_publication_events WHERE candidate_token=%s ORDER BY event_id DESC LIMIT 1',
                (publication_id,)).fetchone()
        if row is None or event is None:return False
        row_sha=hashlib.sha256(_canonical([*row[:6],row[6]])).hexdigest()
        if (row[0]!=publication_id or row[1]!=day or row[2]!=receipt.get('predecessor_head_sha256')
                or row[3]!=receipt.get('candidate_head_sha256')
                or row[4]!=owner_authority['sha256'] or row[5]!=source_freeze['sha256']
                or row[6]!=dict(status='PENDING',context_token=publication_id,accepted_trade_date=day,
                    production_accepted=False,read_scope='DEVELOPMENT_CANDIDATE_PREVIEW')
                or row_sha!=receipt.get('pg_row_sha256') or event[0]!='FINALIZED'
                or event[1]!=row_sha):return False
        evidence=event[2] or {}
        if (evidence.get('transaction_sha256')!=transaction['sha256']
                or evidence.get('readback')!=receipt.get('readback')):return False
        pg_time=datetime.fromisoformat(str(event[3]).replace('Z','+00:00'))
        supplied_cutoff=datetime.fromisoformat(str(chain.get('knowledge_cutoff','')).replace('Z','+00:00'))
        supplied_available=datetime.fromisoformat(str(chain.get('source_available_at','')).replace('Z','+00:00'))
        return supplied_cutoff==pg_time and supplied_available==pg_time
    except Exception:
        return False


def adapt_candidate_trend_reference(reference, *, t0, knowledge_cutoff):
    """Validate one explicitly bound same-series trend reference; fail closed."""
    if not isinstance(reference, dict):
        return dict(value='UNKNOWN',quality='SOURCE_INCOMPLETE',reason='TREND_REFERENCE_NOT_BOUND',
                    contract_id='MARKET_REGIME_TREND_WEAK_ERRATUM_V1')
    required=('trade_date','series_id','price_basis_id','source_sha256','market_calendar_id',
              'index_close','index_ma20','index_ma20_t_minus_5','source_available_at',
              'knowledge_cutoff','permission_chain','input_publication_id','time_role')
    missing=[key for key in required if reference.get(key) is None]
    if missing:
        return dict(value='UNKNOWN',quality='SOURCE_INCOMPLETE',reason='TREND_REFERENCE_REQUIRED_FIELDS_MISSING',
                    missing_fields=missing,contract_id='MARKET_REGIME_TREND_WEAK_ERRATUM_V1')
    def instant(value):
        if not isinstance(value,str):return None
        try:
            parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
            return parsed if parsed.tzinfo is not None else None
        except ValueError:return None
    available=instant(reference['source_available_at'])
    cutoff_instant=instant(reference['knowledge_cutoff'])
    expected_cutoff=instant(knowledge_cutoff) if 'T' in str(knowledge_cutoff) else None
    if available is None or cutoff_instant is None or expected_cutoff is None:
        reason='TREND_REFERENCE_TIME_NOT_AUDITABLE'
    elif available>cutoff_instant or cutoff_instant>expected_cutoff:
        reason='TREND_REFERENCE_AVAILABLE_AFTER_CUTOFF'
    elif reference['trade_date'] != t0:
        reason='TREND_REFERENCE_DATE_MISMATCH'
    elif reference['trade_date'] > knowledge_cutoff:
        reason='TREND_REFERENCE_FUTURE_INPUT'
    elif reference['time_role']!='KNOWN_BY_CUTOFF':
        reason='TREND_REFERENCE_TIME_ROLE_NOT_ADMISSIBLE'
    elif not _permission_chain_proven({**reference['permission_chain'],
            'knowledge_cutoff':reference['knowledge_cutoff'],
            'source_available_at':reference['source_available_at'],
            'trade_date':reference['trade_date'],'series_id':reference['series_id'],
            'price_basis_id':reference['price_basis_id'],'market_calendar_id':reference['market_calendar_id'],
            'index_close':reference['index_close'],'index_ma20':reference['index_ma20'],
            'index_ma20_t_minus_5':reference['index_ma20_t_minus_5']},
            reference.get('source_sha256'),reference.get('input_publication_id')):
        reason='TREND_REFERENCE_PERMISSION_NOT_PROVEN'
    elif not isinstance(reference['source_sha256'],str) or not re.fullmatch(r'[0-9a-fA-F]{64}',reference['source_sha256']):
        reason='TREND_REFERENCE_SOURCE_DIGEST_INVALID'
    else:
        reason=None
    if reason:
        return dict(value='UNKNOWN',quality='SOURCE_INCOMPLETE',reason=reason,
                    contract_id='MARKET_REGIME_TREND_WEAK_ERRATUM_V1')
    result=market_trend_axis(index_close=reference['index_close'],index_ma20=reference['index_ma20'],
        index_ma20_t_minus_5=reference['index_ma20_t_minus_5'],trade_date=t0,
        market_calendar_id=reference['market_calendar_id'],market_snapshot_id=reference['series_id'],
        adjustment_basis_id=reference['price_basis_id'],input_source_digest=reference['source_sha256'])
    return dict(value=result['trend_axis'],quality=result['quality_state'],reason=result['unknown_reason'],
        contract_id=result['contract_id'],contract_version=result['contract_version'],identity=result['identity'],
        input_digest=result['input_digest'],output_digest=result['output_digest'],
        available_at=reference['source_available_at'],knowledge_cutoff=knowledge_cutoff,
        time_role=reference['time_role'],permission_chain_proven=True)


def _limit_owner(root,candidate,day):
    owner=candidate.get('owners',{}).get(day,{})
    expected=owner.get('raw',{}).get('path','')
    match=re.search(r'dynamic_daily_owners[/\\]'+re.escape(day)+r'[/\\]([^/\\]+)',expected)
    registry=candidate.get('source_registry',{}).get(day) or {}
    generation_ref=registry.get('generation');freeze_ref=registry.get('freeze')
    if generation_ref and freeze_ref:
        generation=json.loads(_checked(root,generation_ref).read_bytes())
        if generation.get('source_freeze')!=freeze_ref.get('sha256'):
            raise ValueError('R7_MARKET_STRESS_GENERATION_FREEZE_MISMATCH:'+day)
        generation_root=_checked(root,generation_ref).parent
        candidate_owner_id=generation_root.name
    elif match:
        candidate_owner_id=match.group(1)
        generation_root=Path(root)/'data/v4/dynamic_daily_owners'/day/candidate_owner_id
    else:raise ValueError('R7_MARKET_STRESS_DATED_CANDIDATE_OWNER_ID_MISSING:'+day)
    raw_ref=owner.get('raw') or {}
    if len(str(raw_ref.get('sha256',''))) != 64:raise ValueError('R7_MARKET_STRESS_CANDIDATE_RAW_BINDING_MISSING:'+day)
    matches=[];bound_limits=[];receipt_paths=[]
    if owner.get('market'):
        market=json.loads(_checked(root,owner['market']).read_bytes())
        bound_limits=[item for item in market.get('input_bindings',[])
                      if Path(item.get('path','')).name=='daily_price_limits_v1.jsonl.gz'
                      and '/owners/'+day+'/' in item['path'].replace('\\','/')]
        for binding in bound_limits:
            path=_checked(root,binding)
            receipt_path=path.parents[2]/'DAILY_PRICE_LIMIT_REPLAY.json'
            if receipt_path.is_file():receipt_paths.append(receipt_path)
        if len(bound_limits)>1:raise ValueError('R7_MARKET_STRESS_DATED_LIMIT_BINDING_AMBIGUOUS:'+day)
    # Search legacy materializations only when the dated market Owner has no
    # colocated receipt. The normal R9 path binds the exact limit artifact and
    # its receipt; scanning every historical materialization on each cache-key
    # lookup made a cold Home request proportional to the whole candidate root.
    # Legacy receipts remain eligible only when no exact receipt is present and
    # their input and output still match the bound Owner below.
    if not receipt_paths:
        receipt_paths.extend(Path(root).glob(
            'r5_daily_limit_materialization_*/'+day+'/DAILY_PRICE_LIMIT_REPLAY.json'))
    for receipt_path in sorted(set(receipt_paths)):
        receipt_bytes=receipt_path.read_bytes();receipt=json.loads(receipt_bytes)
        if receipt.get('production_admission') is not False or not receipt.get('contract'):
            continue
        _checked(root,receipt['contract'])
        for row in receipt.get('owners',[]):
            if bound_limits and row.get('artifact') not in bound_limits:continue
            if row.get('raw_binding') is not None and row['raw_binding']!=raw_ref:continue
            source=row.get('baostock_source') or {}
            if bound_limits and source.get('candidate_owner_id') is None:
                # Older receipts lack the new display metadata. Prove their
                # exact daily rows against this date's frozen capture instead.
                freeze_ref=(candidate.get('source_registry',{}).get(day) or {}).get('freeze')
                if not freeze_ref:continue
                freeze=json.loads(_checked(root,freeze_ref).read_bytes())
                payload=json.loads(_checked(root,source).read_bytes())
                if (freeze.get('target_session')!=day or payload.get('rows')!=freeze.get('normalized',{}).get('daily',{}).get('rows')
                        or any(item.get('date')!=day for item in payload.get('rows',[]))):continue
                source=dict(source,trade_date=day,candidate_owner_id=candidate_owner_id,
                    capture_observed_at=payload.get('observed_at'),source_freeze=freeze_ref,
                    temporal_proof='EXACT_BOUND_MARKET_LIMIT_AND_DATED_FREEZE_ROWS_V1')
                row=dict(row,baostock_source=source)
            if (row.get('trade_date')!=day or source.get('trade_date')!=day or
                    source.get('candidate_owner_id')!=candidate_owner_id):
                continue
            source_path=_checked(root,source)
            source_payload=json.loads(source_path.read_bytes())
            observed_at=source_payload.get('observed_at')
            if not isinstance(observed_at,str) or source.get('capture_observed_at')!=observed_at:
                continue
            try:
                capture_time=datetime.fromisoformat(observed_at.replace('Z','+00:00'))
                if capture_time.tzinfo is None:continue
            except ValueError:
                continue
            # Daily source lives in generation/sources, while RAW lives in
            # generation/owner_v3/owners/day. They are siblings, not children.
            try:source_path.resolve().relative_to(generation_root.resolve())
            except ValueError:continue
            binding=row.get('artifact') or {}
            _checked(root,binding)
            matches.append((binding,row,receipt_path,hashlib.sha256(receipt_bytes).hexdigest()))
    unique={(x[0].get('sha256'),x[0].get('bytes'),
             x[1]['baostock_source'].get('sha256'),x[1]['baostock_source'].get('bytes'),
             json.dumps(x[1].get('counts',{}),sort_keys=True,separators=(',',':'))) for x in matches}
    if len(unique)!=1:raise ValueError('R7_MARKET_STRESS_LIMIT_OWNER_NOT_UNIQUE_OR_SOURCE_MISMATCH:'+day)
    selected=sorted(matches,key=lambda x:(x[3],str(x[2])))[0]
    selected[1]['_receipt_sha256s']=sorted({x[3] for x in matches})
    return selected


def _stress_window_days(candidate):
    t0=candidate.get('accepted_trade_date')
    sessions=candidate.get('published_sessions')
    if not isinstance(t0,str) or not isinstance(sessions,list):
        raise ValueError('R7_MARKET_STRESS_PUBLISHED_SESSION_BINDING_MISSING')
    ordered=sorted({session for session in sessions if isinstance(session,str) and session<=t0})
    if not ordered or ordered[-1]!=t0:
        raise ValueError('R7_MARKET_STRESS_T0_NOT_IN_PUBLISHED_SESSIONS')
    return ordered[-3:]


def _candidate_trend_reference(root,candidate,day):
    """Derive the current trend inputs from the bound R8 market reference path."""
    root=Path(root).resolve()
    head_path=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    head_raw=head_path.read_bytes()
    token=hashlib.sha256(head_raw).hexdigest()
    head=json.loads(head_raw)
    if (head.get('accepted_trade_date')!=day or candidate.get('accepted_trade_date')!=day
            or head.get('owners')!=candidate.get('owners')):
        return None
    market_binding=(head.get('owners',{}).get(day) or {}).get('market')
    if not isinstance(market_binding,dict):return None
    market=json.loads(_checked(root,market_binding).read_bytes())
    bindings=[item for item in market.get('input_bindings',[])
        if Path(item.get('path','')).name.startswith('V4_03_MARKET_REFERENCE_PATH_CANDIDATE')]
    if len(bindings)!=1:return None
    binding=bindings[0];path=_checked(root,binding)
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        rows=[json.loads(line) for line in stream if line.strip()]
    from workbench_analysis.market_source_acquisition import official_sessions
    sessions=official_sessions(root)
    if not isinstance(sessions,list):return None
    ordered=sorted({session for session in sessions if isinstance(session,str) and session<=day})
    if len(ordered)<25 or ordered[-1]!=day:return None
    window=ordered[-25:]
    by_day={}
    for row in rows:
        if row.get('trade_date') in window:
            if row['trade_date'] in by_day:return None
            by_day[row['trade_date']]=row
    if list(sorted(by_day))!=window:return None
    chosen=[by_day[session] for session in window]
    first,last=chosen[0],chosen[-1]
    if any(row.get('quality_state')!='OBSERVED' or not isinstance(row.get('level'),(int,float))
            or isinstance(row.get('level'),bool) or not math.isfinite(row.get('level'))
            or row.get('level')<=0 or not row.get('adjustment_basis_id')
            or any(row.get(key)!=first.get(key) for key in
                ('series_version','path_identity','market_calendar_id')) for row in chosen):
        return None
    receipt_path=root/'data/v4/r8_publication_bridge_v1/receipts'/f'{token}.json'
    try:receipt=json.loads(receipt_path.read_bytes())
    except (OSError,ValueError):return None
    pg_schema=receipt.get('pg_schema')
    if not isinstance(pg_schema,str):return None
    from workbench_db.v4_native import connection
    try:
        with connection(pg_schema,read_only=True) as pg:
            row=pg.execute('SELECT event_type,inserted_at::text FROM r8_publication_events WHERE candidate_token=%s ORDER BY event_id DESC LIMIT 1',
                (token,)).fetchone()
        if row is None or row[0]!='FINALIZED':return None
        cutoff=datetime.fromisoformat(str(row[1]).replace('Z','+00:00')).isoformat()
    except Exception:
        return None
    values=[float(row['level']) for row in chosen]
    return dict(trade_date=day,series_id=last['path_identity']+':'+last['series_version'],
        price_basis_id=last['adjustment_basis_id'],source_sha256=binding['sha256'],
        market_calendar_id=last['market_calendar_id'],index_close=values[-1],
        index_ma20=sum(values[-20:])/20,index_ma20_t_minus_5=sum(values[:20])/20,
        source_available_at=cutoff,knowledge_cutoff=cutoff,
        permission_chain=dict(candidate_root=str(root),trade_date=day),
        input_publication_id=token,time_role='KNOWN_BY_CUTOFF')


def candidate_market_stress_identity(root,candidate):
    """Content-verify cached inputs so same-token candidate replacement misses cache."""
    root=Path(root);t0=candidate['accepted_trade_date']
    rows=[];verified_historical={}
    for day in _stress_window_days(candidate):
        if day not in candidate.get('owners',{}):
            raise ValueError('R7_MARKET_STRESS_DATED_OWNER_MISSING:'+day)
        owner=candidate['owners'][day];market=_checked(root,owner['market'])
        market_doc=json.loads(market.read_bytes())
        historical_refs=[ref for ref in market_doc.get('input_bindings',[])
                         if 'historical_universe' in Path(ref.get('path','')).name]
        if len(historical_refs)!=1:
            raise ValueError('R10_MARKET_HISTORICAL_UNIVERSE_BINDING_AMBIGUOUS:'+day)
        historical_ref=historical_refs[0]
        historical_key=(historical_ref['path'],historical_ref['sha256'],historical_ref.get('bytes'))
        if historical_key not in verified_historical:
            verified_historical[historical_key]=_checked(root,historical_ref)
        historical_path=verified_historical[historical_key]
        limit,receipt,_,_=_limit_owner(root,candidate,day);limit_path=_checked(root,limit)
        core_path=_checked(root,owner['core'])
        stat=lambda path:(path.stat().st_size,path.stat().st_mtime_ns)
        rows.append(dict(day=day,core_sha256=owner['core']['sha256'],core_stat=stat(core_path),
            market_sha256=owner['market']['sha256'],market_stat=stat(market),
            historical_universe_sha256=historical_refs[0]['sha256'],
            historical_universe_stat=stat(historical_path),
            limit_sha256=limit['sha256'],limit_stat=stat(limit_path),
            raw_source_sha256=receipt['baostock_source']['sha256'],receipt_sha256s=receipt['_receipt_sha256s']))
    source=dict(contract='R7_CANDIDATE_MARKET_STRESS_V2',T0=t0,
        producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        parameter_sha256=hashlib.sha256((Path(__file__).resolve().parents[2]/'config/v4_03_parameter_set_v1.json').read_bytes()).hexdigest(),
        inputs=rows)
    return hashlib.sha256(_canonical(source)).hexdigest()


def _market_axes_from_owner(root,candidate,day,core_binding,market_binding,core_rows,*,allow_reprojection=False):
    market_path=_checked(root,market_binding);market=json.loads(market_path.read_bytes())
    if market.get('trade_date')!=day or market.get('AS_RECORDED') is not False or market.get('accepted') is not False:
        raise ValueError('R7_MARKET_OWNER_DATE_OR_AUTHORITY_MISMATCH:'+day)
    bindings=market.get('input_bindings',[])
    bound={Path(ref['path']).name:ref for ref in bindings}
    history_ref=bound.get('history.jsonl.gz')
    membership_ref=next((ref for ref in bindings if 'historical_universe' in Path(ref['path']).name),None)
    core_refs=[ref for ref in bindings if Path(ref['path']).name==Path(core_binding['path']).name]
    if not history_ref or not membership_ref or len(core_refs)!=1:
        raise ValueError('R7_MARKET_OWNER_REQUIRED_INPUT_BINDING_MISSING:'+day)
    core_reconciliation=None
    if core_refs[0]!=core_binding:
        # RPS-only annotations can mint a new Core Owner without changing the
        # market's consumed fields. Verify those exact field envelopes and the
        # complete identity set; bind both versions in this new NON_PIT result.
        # Any market-consumed field change still requires a producer rebuild.
        old_core=_read_rows(_checked(root,core_refs[0]))
        def consumed(rows):
            result={}
            for row in rows:
                sid=row.get('security_id')
                if not sid or sid in result:raise ValueError('R7_MARKET_CORE_IDENTITY_AMBIGUOUS:'+day)
                result[sid]={key:row.get(key) for key in ('trade_date','source_security_key','board_scope')}
                result[sid]['amount_ratio20']=(row.get('fields') or {}).get('amount_ratio20')
            return result
        old_consumed,new_consumed=consumed(old_core),consumed(core_rows)
        equal=old_consumed==new_consumed
        if not equal and not allow_reprojection:
            raise ValueError('R7_MARKET_CORE_CONSUMED_FIELD_REVISION_REQUIRED:'+day)
        core_reconciliation=dict(contract_id='R9_MARKET_CORE_SOURCE_REPROJECTION_V1',
            original_core=core_refs[0],current_core=core_binding,
            consumed_fields=['security_id','trade_date','source_security_key','board_scope','fields.amount_ratio20'],
            original_count=len(old_core),identity_count=len(core_rows),
            added_identities=sorted(set(new_consumed)-set(old_consumed)),
            removed_identities=sorted(set(old_consumed)-set(new_consumed)),
            changed_envelopes=sum(old_consumed[sid]!=new_consumed[sid] for sid in set(old_consumed)&set(new_consumed)),
            status='PROVEN_EQUAL' if equal else 'NEW_NON_PIT_DERIVATION_REQUIRED_AND_CALCULATED',production_admission=False)
    from workbench_analysis.market_source_acquisition import official_sessions
    sessions=[session for session in official_sessions(Path(root)) if session<=day]
    index=sessions.index(day);prior3=sessions[index-3] if index>=3 else None
    if prior3 is None or market.get('comparison_trade_date')!=prior3:
        raise ValueError('R7_MARKET_BREADTH_COMPARISON_SESSION_MISMATCH:'+day)
    universe,comparison_membership_binding=_comparison_universe(root,candidate,prior3,membership_ref)
    # Validate the full comparison denominator before inflating the much larger
    # multi-year quote history. Missing membership evidence is a fast,
    # capability-scoped failure and does not spend a cold Home load on quotes.
    required_history_sessions=set()
    for return_day in (day,prior3):
        position=sessions.index(return_day)
        if position>0:required_history_sessions.update((return_day,sessions[position-1]))
    history=_selected_history_bars(_checked(root,history_ref),required_history_sessions)
    current={r['security_id']:r for r in core_rows if r.get('security_id') in universe}
    comparison=[]
    for sid in current:
        bars=history.get(sid,{})
        def ret(d):
            pos=sessions.index(d)
            if pos<1:return None
            today=bars.get(d);previous=bars.get(sessions[pos-1])
            if not today or not previous or len(today)<4 or len(previous)<4:return None
            close,prior_close=today[3],previous[3]
            if (not isinstance(close,(int,float)) or isinstance(close,bool) or
                    not isinstance(prior_close,(int,float)) or isinstance(prior_close,bool) or
                    not math.isfinite(close) or not math.isfinite(prior_close) or close<=0 or prior_close<=0):
                return None
            return close/prior_close-1
        now,old=ret(day),ret(prior3)
        if now is not None and old is not None:comparison.append((now,old))
    # The existing implementation is the positive-indicator definition. Keep
    # it for the recorded-axis parity check while exposing the distinct SIGN
    # definition for independent S02 contract adjudication.
    breadth_metrics=candidate_breadth_formula_comparison(comparison,
        boundary=candidate_threshold('market_breadth_axis'))
    breadth_positive=breadth_metrics['positive_indicator']['value']
    formula_comparison=dict(breadth_metrics)
    formula_comparison.update(contract='S02_BREADTH_FORMULA_COMPARISON_R1',
        positive_indicator={**breadth_metrics['positive_indicator'],'definition':'I(r>0) in {0,1}','zero_return':'0'},
        signed={**breadth_metrics['signed'],'definition':'SIGN(r) in {-1,0,1}','zero_return':'0'},
        adjudication='OPEN_SOURCE_CONTRACT_REVIEW_REQUIRED')
    amounts=[]
    for row in core_rows:
        fact=(row.get('fields') or {}).get('amount_ratio20') or {};value=fact.get('value')
        if fact.get('quality_state')=='OBSERVED' and isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value):amounts.append(value)
    participation=statistics.median(amounts) if amounts else None
    return breadth_positive,participation,dict(comparison_trade_date=prior3,universe_count=len(universe),
        current_members=len(current),breadth_evaluable=len(comparison),participation_evaluable=len(amounts),
        breadth_formula='ADVANCERS_SHARE_DELTA3:MEAN(I(RET1_T>0)-I(RET1_T_MINUS_3>0))',
        breadth_formula_comparison=formula_comparison,
        return_window=dict(current_return='close_t / close_t_minus_1 - 1',
            comparison_return='close_t_minus_3 / close_t_minus_4 - 1',
            coordinate='QFQ_OHLC',missing_policy='EXCLUDE_FROM_EVALUABLE_COMPARISON',
            source='BOUND_MARKET.history.jsonl.gz',as_of=day),
        participation_formula='MEDIAN(CORE.amount_ratio20 WHERE quality_state=OBSERVED)',
        market_owner_binding=market_binding,history_binding=history_ref,membership_binding=membership_ref,
        comparison_membership_binding=comparison_membership_binding,
        recorded_breadth_axis=market.get('axes',{}).get('breadth_axis'),
        core_source_reconciliation=core_reconciliation,
        recorded_participation_axis=market.get('axes',{}).get('participation_axis'))


def build_candidate_market_stress(root,candidate):
    """Recalculate available market axes from verified date-bound candidate inputs."""
    root=Path(root);t0=candidate['accepted_trade_date']
    scope=candidate.get('r9_derivation_scope') or {}
    allow_reprojection=False
    if scope.get('market_reprojection_contract')=='R9_MARKET_CORE_SOURCE_REPROJECTION_V1':
        original=json.loads(_checked(root,scope['source_head']).read_bytes())
        from .operational_successor_v1 import digest
        if (scope.get('contract_id')!='V4_R9_CANDIDATE_OWNER_SCOPE_V1'
                or scope.get('production_admission') is not False
                or scope.get('T0')!=t0 or scope.get('source_context_token')!=digest(original)
                or scope.get('source_owners')!=original.get('owners',{}).get(t0)
                or original.get('owners')!=candidate.get('owners')
                or original.get('accepted_trade_date')!=t0):
            raise ValueError('R9_MARKET_REPROJECTION_SCOPE_MISMATCH')
        allow_reprojection=True
    dates=_stress_window_days(candidate)
    outputs={};owners={}
    references=candidate.get('market_trend_references') or {}
    if not isinstance(references,dict):references={}
    if isinstance(candidate.get('market_trend_reference'),dict):
        references.setdefault(candidate['market_trend_reference'].get('trade_date'),candidate['market_trend_reference'])
    for day in dates:
        limit_binding,receipt_owner,receipt_path,receipt_sha=_limit_owner(root,candidate,day)
        states_rows=_read_rows(_checked(root,limit_binding));states={r['security_id']:r['limit_state'] for r in states_rows}
        valid={sid:value for sid,value in states.items() if value in ('NOT_LIMIT','LIMIT_UP','LIMIT_DOWN')}
        core_binding=candidate['owners'][day]['core'];core_rows=_read_rows(_checked(root,core_binding))
        universe={row['security_id'] for row in core_rows if row.get('security_id')};common=set(valid)&universe
        coverage=len(common)/len(universe) if universe else None
        stress=sum(valid[sid]=='LIMIT_DOWN' for sid in common)/len(common) if common else None
        index=candidate['published_sessions'].index(day)
        prior_day=candidate['published_sessions'][index-1] if index>0 else None;prior_valid=None
        if prior_day and prior_day in dates:
            prior_binding,prior_owner,_,_=_limit_owner(root,candidate,prior_day)
            prior_rows=_read_rows(_checked(root,prior_binding));prior_states={r['security_id']:r['limit_state'] for r in prior_rows}
            comparable=common&{sid for sid,state in prior_states.items() if state in ('NOT_LIMIT','LIMIT_UP','LIMIT_DOWN')}
            if comparable:
                prior_valid=dict(day=prior_day,ratio=sum(prior_states[s]=='LIMIT_DOWN' for s in comparable)/len(comparable),
                    current_ratio=sum(valid[s]=='LIMIT_DOWN' for s in comparable)/len(comparable),common_count=len(comparable),owner=prior_binding)
        market_binding=candidate['owners'][day].get('market') or {}
        breadth,participation,axis_inputs=_market_axes_from_owner(root,candidate,day,core_binding,market_binding,core_rows,
            allow_reprojection=allow_reprojection)
        source_identity=dict(day=day,core=core_binding,limits=limit_binding,receipt_sha256s=receipt_owner['_receipt_sha256s'],
            source=receipt_owner['baostock_source'],market=market_binding,axis_inputs=axis_inputs,prior=prior_valid)
        source_digest=hashlib.sha256(_canonical(source_identity)).hexdigest()
        axes=market_axis_primitives(breadth=breadth,participation=participation,limit_coverage=coverage,
            stress_ratio=stress,prior_stress_ratio=prior_valid['ratio'] if prior_valid else None,
            stress_change_current_ratio=prior_valid['current_ratio'] if prior_valid else None,
            stress_change_current_provided=bool(prior_valid),trade_date=day,market_calendar_id='V4_OFFICIAL',
            market_snapshot_id=market_binding.get('sha256') or core_binding['sha256'],
            adjustment_basis_id=core_binding['sha256'],input_source_digest=source_digest)
        if not allow_reprojection and (axis_inputs['recorded_breadth_axis']!=axes['breadth_axis'] or
                axis_inputs['recorded_participation_axis']!=axes['participation_axis']):
            raise ValueError('R7_MARKET_AXIS_RECALCULATION_MISMATCH:'+day)
        trend_reference=references.get(day)
        if day==t0 and trend_reference is None:
            trend_reference=_candidate_trend_reference(root,candidate,day)
        if day==t0 and isinstance(trend_reference,dict):
            cutoff=trend_reference.get('knowledge_cutoff')
            trend=adapt_candidate_trend_reference(trend_reference,t0=day,knowledge_cutoff=cutoff)
        else:
            trend=dict(value='UNKNOWN',quality='SOURCE_INCOMPLETE',
                reason='TREND_REFERENCE_NOT_BOUND_TO_CURRENT_PUBLICATION',
                contract_id='MARKET_REGIME_TREND_WEAK_ERRATUM_V1')
        outputs[day]=dict(T0=day,stress_level=axes['stress_level'],stress_change=axes['stress_change'],
            breadth_axis=axes['breadth_axis'],participation_axis=axes['participation_axis'],
            trend_axis=trend,
            composite_regime_status='NOT_PUBLISHED_V4_03',status='CANDIDATE_POST_HOC',
            AS_RECORDED=False,PIT_ELIGIBLE=False,production_admission=False,known_count=len(common),universe_count=len(universe),
            limit_coverage=coverage,limit_state_counts={name:sum(states.get(sid)==name for sid in common)
                for name in ('NOT_LIMIT','LIMIT_UP','LIMIT_DOWN')},unknown_count=sum(states.get(sid)=='UNKNOWN' for sid in universe),
            suspended_count=sum(states.get(sid)=='SUSPENDED' for sid in universe),
            capture_observed_at=receipt_owner['baostock_source']['capture_observed_at'],limit_owner=limit_binding,
            limit_receipt_path=str(receipt_path),limit_receipt_sha256=receipt_sha,raw_source=receipt_owner['baostock_source'],
            core_owner=core_binding,market_owner=market_binding,axis_inputs=axis_inputs,breadth_value=breadth,
            participation_value=participation,prior_comparison=prior_valid,input_digest=axes['input_digest'],
            output_digest=axes['output_digest'],source_digest=source_digest,contract_id=axes['contract_id'],
            parameter_set_id=axes['parameter_set_id'])
        owners[day]=dict(receipt_path=str(receipt_path),limit=limit_binding,raw=receipt_owner['baostock_source'],core=core_binding)
    trend=outputs.get(t0,{}).get('trend_axis') or dict(value='UNKNOWN',quality='SOURCE_INCOMPLETE',
        reason='BOUND_MARKET_RELATIVE_REFERENCE_PATH_NOT_PROVEN',contract_id='MARKET_REGIME_TREND_WEAK_ERRATUM_V1')
    return dict(contract_id='R7_CANDIDATE_MARKET_STRESS_PREVIEW_V2',T0=t0,status='READY' if outputs else 'SOURCE_INCOMPLETE',
        input_authority='EXPLICIT_SUCCESSOR_CANDIDATE_PLUS_POST_HOC_DATED_BAOSTOCK',market_stress=outputs,source_owners=owners,
        trend_reference=trend,trend_axis_status=trend['value'] if trend['quality']=='OBSERVED' else 'UNKNOWN_REFERENCE_PATH_NOT_COMPLETE_AT_T0',
        composite_regime_status='NOT_PUBLISHED_V4_03',AS_RECORDED=False,PIT_ELIGIBLE=False,production_admission=False)
