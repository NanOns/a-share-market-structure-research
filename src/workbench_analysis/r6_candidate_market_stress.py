"""Bounded, post-hoc market stress preview from dated 10/12-10/14 limit Owners."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from v4.factors.native import market_axis_primitives


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _checked(root, ref):
    path=Path(root)/ref['path'];raw=path.read_bytes()
    if len(raw)!=ref.get('bytes',len(raw)) or hashlib.sha256(raw).hexdigest()!=ref['sha256']:
        raise ValueError('R6_MARKET_STRESS_OWNER_BYTES_OR_SHA_MISMATCH')
    return path


def _read_rows(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:return [json.loads(line) for line in stream]


def _limit_owner(root,candidate,day):
    expected=candidate.get('owners',{}).get(day,{}).get('raw',{}).get('path','')
    import re
    match=re.search(r'dynamic_daily_owners[/\\]'+re.escape(day)+r'[/\\]([^/\\]+)',expected)
    if not match:raise ValueError('R6_MARKET_STRESS_DATED_CANDIDATE_OWNER_ID_MISSING:'+day)
    candidate_owner_id=match.group(1)
    matches=[]
    for receipt_path in Path(root).glob('r5_daily_limit_materialization_*/'+day+'/DAILY_PRICE_LIMIT_REPLAY.json'):
        receipt=json.loads(receipt_path.read_bytes())
        for owner in receipt.get('owners',[]):
            if owner.get('trade_date')==day and owner.get('baostock_source',{}).get('candidate_owner_id')==candidate_owner_id:
                binding=owner['artifact'];artifact=Path(root)/binding['path']
                if artifact.exists() and _checked(root,binding)==artifact:matches.append((binding,owner,receipt_path))
    unique={(m[0]['sha256'],m[1]['baostock_source']['sha256']) for m in matches}
    if len(unique)!=1:raise ValueError('R6_MARKET_STRESS_LIMIT_OWNER_NOT_UNIQUE:'+day)
    return sorted(matches,key=lambda item:str(item[2]))[-1]


def build_candidate_market_stress(root,candidate):
    """Compute only the stress axis; missing breadth/participation stay UNKNOWN."""
    root=Path(root);t0=candidate['accepted_trade_date']
    if t0>'2026-10-14':raise ValueError('R6_MARKET_STRESS_CUTOFF_EXCEEDED')
    dates=[d for d in ('2026-10-12','2026-10-13','2026-10-14') if d in candidate.get('owners',{}) and d<=t0]
    outputs={};owners={}
    for day in dates:
        binding,receipt_owner,receipt_path=_limit_owner(root,candidate,day)
        limit_rows=_read_rows(_checked(root,binding));states={r['security_id']:r['limit_state'] for r in limit_rows}
        valid={sid:state for sid,state in states.items() if state in ('NOT_LIMIT','LIMIT_UP','LIMIT_DOWN')}
        core_binding=candidate['owners'][day]['core'];core_rows=_read_rows(_checked(root,core_binding))
        universe={row['security_id'] for row in core_rows if row.get('security_id')}
        common=set(valid)&universe
        coverage=len(common)/len(universe) if universe else None
        stress=sum(valid[sid]=='LIMIT_DOWN' for sid in common)/len(common) if common else None
        prior_day=None
        index=candidate['published_sessions'].index(day)
        if index>0:prior_day=candidate['published_sessions'][index-1]
        prior_valid=None
        if prior_day and prior_day in ('2026-10-12','2026-10-13','2026-10-14'):
            prior_binding,prior_owner,_=_limit_owner(root,candidate,prior_day)
            prior_rows=_read_rows(_checked(root,prior_binding));prior_states={r['security_id']:r['limit_state'] for r in prior_rows}
            comparable=common & {sid for sid,state in prior_states.items() if state in ('NOT_LIMIT','LIMIT_UP','LIMIT_DOWN')}
            if comparable:
                prior_ratio=sum(prior_states[sid]=='LIMIT_DOWN' for sid in comparable)/len(comparable)
                current_ratio=sum(valid[sid]=='LIMIT_DOWN' for sid in comparable)/len(comparable)
                prior_valid=dict(day=prior_day,ratio=prior_ratio,current_ratio=current_ratio,common_count=len(comparable),owner=prior_binding)
        market_binding=candidate['owners'][day].get('market') or {}
        source_identity=dict(day=day,core=core_binding,limits=binding,
                             source=receipt_owner['baostock_source'],market=market_binding,
                             prior=prior_valid)
        source_digest=hashlib.sha256(_canonical(source_identity)).hexdigest()
        axes=market_axis_primitives(breadth=None,participation=None,limit_coverage=coverage,
            stress_ratio=stress,prior_stress_ratio=prior_valid['ratio'] if prior_valid else None,
            stress_change_current_ratio=prior_valid['current_ratio'] if prior_valid else None,
            stress_change_current_provided=bool(prior_valid),trade_date=day,
            market_calendar_id='V4_OFFICIAL',market_snapshot_id=market_binding.get('sha256') or core_binding['sha256'],
            adjustment_basis_id=core_binding['sha256'],input_source_digest=source_digest)
        outputs[day]=dict(T0=day,stress_level=axes['stress_level'],stress_change=axes['stress_change'],
            breadth_axis=None,participation_axis=None,composite_regime_status='UNAVAILABLE_INCOMPLETE_AXES',
            status='CANDIDATE_POST_HOC',AS_RECORDED=False,PIT_ELIGIBLE=False,production_admission=False,
            known_count=len(common),universe_count=len(universe),limit_coverage=coverage,
            limit_state_counts={name:sum(states.get(sid)==name for sid in common) for name in ('NOT_LIMIT','LIMIT_UP','LIMIT_DOWN')},
            unknown_count=sum(states.get(sid)=='UNKNOWN' for sid in universe),suspended_count=sum(states.get(sid)=='SUSPENDED' for sid in universe),
            capture_observed_at=receipt_owner['baostock_source']['capture_observed_at'],
            limit_owner=binding,raw_source=receipt_owner['baostock_source'],core_owner=core_binding,
            market_owner=market_binding,prior_comparison=prior_valid,input_digest=axes['input_digest'],
            output_digest=axes['output_digest'],source_digest=source_digest,
            contract_id=axes['contract_id'],parameter_set_id=axes['parameter_set_id'])
        owners[day]=dict(receipt_path=str(receipt_path),limit=binding,raw=receipt_owner['baostock_source'],core=core_binding)
    return dict(contract_id='R6_CANDIDATE_MARKET_STRESS_PREVIEW_V1',T0=t0,
        status='READY' if outputs else 'SOURCE_INCOMPLETE',input_authority='EXPLICIT_SUCCESSOR_CANDIDATE_PLUS_POST_HOC_DATED_BAOSTOCK',
        market_stress=outputs,source_owners=owners,composite_regime_status='UNKNOWN_BREADTH_AND_PARTICIPATION_UNAVAILABLE',
        AS_RECORDED=False,PIT_ELIGIBLE=False,production_admission=False)
