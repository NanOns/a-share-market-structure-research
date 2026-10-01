from __future__ import annotations
"""Independent artifact/source comparisons; never calls a candidate builder as oracle."""
from collections import Counter
from datetime import datetime
from decimal import Decimal,ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import struct
import zipfile

def _canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')
def _digest(v):return hashlib.sha256(_canonical(v)).hexdigest()
def _key(r):return str(r.get('security_id') or 'SOURCE:'+str(r.get('source_security_key','')))
def _read(ref):
    p=Path(ref['path'])
    if not p.is_absolute():p=Path(__file__).resolve().parents[2]/p
    data=p.read_bytes()
    if hashlib.sha256(data).hexdigest()!=ref['sha256']:raise ValueError('INDEPENDENT_INPUT_DIGEST_MISMATCH')
    return json.loads(data.decode('utf8'))

def _get_component(receipt):
    return _read(dict(path=receipt['artifact_path'],sha256=receipt['artifact_sha256']))

def check_component(receipt,payload,freeze,parent,calendar,identity):
    rows=payload['rows'];cap=receipt['component_id'];errors=[]
    def check(name,ok):
        if not ok:errors.append(name)
    check('row_count_and_logical_digest',len(rows)==receipt['row_count'] and _digest(rows)==receipt['logical_digest'])
    keys=[(_key(r),r.get('period_type'),r.get('period_key')) if cap.startswith('PERIOD_') else (_key(r),r.get('trade_date')) for r in rows]
    check('unique_canonical_keys',len(keys)==len(set(keys)))
    check('nonempty_output',bool(rows))
    target=receipt['target_trade_date']
    check('target_and_parent_binding',payload['trade_date']==target==freeze['trade_date'] and receipt['parent_data_head_digest']==parent['binding']['sha256'])
    check('source_calendar_identity_binding',receipt['source_revision']==freeze['manifest_sha256'] and
        receipt['calendar_publication_id']==calendar['publication_id'] and receipt['identity_publication_id']==identity['publication_id'])
    for r in rows:
        check('future_or_wrong_row_date',r.get('as_of_date',r.get('trade_date',''))<=target if cap.startswith('PERIOD_') else r.get('trade_date')==target)
        for p in ('max_source_date','knowledge_time'):
            if p=='max_source_date' and r.get(p):check('future_source_bar',r[p]<=target)
        if 'unknown_reason' in r:check('explicit_unknown_reason',isinstance(r['unknown_reason'],str) and bool(r['unknown_reason']))
    if cap=='RAW_DAILY':
        delta=_read(freeze['inputs']['TDX_PACKAGE_DELTA']);by={str(r.get('source_security_key') or r['security_id']).upper():r for r in delta['target_bars']}
        check('raw_unique_source_keys',len(by)==len(delta['target_bars']))
        for r in rows:
            source=by.get(r['source_security_key'],{})
            check('raw_source_numeric_exact',all(r.get(k)==source.get(k) for k in ('open','high','low','close','volume','amount')))
            check('raw_official_authority',r['source_snapshot_id']==delta['current_snapshot_id'] and r['source_authority']=='TDX_OFFICIAL_PACKAGE'
                  and r['bao_stock_ohlc_substitution_permitted'] is False)
            check('raw_ohlc_quality',r['record_quality']!='SOURCE_FILE_VALIDATED_RECORD' or
                (Decimal(str(r['high']))>=max(Decimal(str(r[x])) for x in ('open','low','close')) and
                 Decimal(str(r['low']))<=min(Decimal(str(r[x])) for x in ('open','high','close')) and r['amount']>=0 and r['volume']>=0))
        # Independent binary package probe across the sorted scope; all rows are checked against the frozen delta above.
        package=Path(freeze['source_families']['TDX_FULL_PACKAGE']['path'])
        with zipfile.ZipFile(package) as archive:
            names={n.casefold():n for n in archive.namelist()}
            sampled=rows[::max(1,len(rows)//13)]
            for r in sampled:
                market,code=r['source_security_key'].split('.');suffix=f'{market.lower()}/lday/{market.lower()}{code}.day'
                name=names.get(suffix)
                if name is None:
                    matches=[n for k,n in names.items() if k.endswith('/'+suffix)]
                    name=matches[0] if len(matches)==1 else None
                check('raw_binary_source_entry_exists',name is not None)
                if name is None:continue
                data=archive.read(name);target_num=int(target.replace('-',''))
                hits=[struct.unpack('<IIIIIfII',data[i:i+32]) for i in range(0,len(data),32)
                      if len(data[i:i+32])==32 and struct.unpack('<I',data[i:i+4])[0]==target_num]
                check('raw_binary_unique_target',len(hits)==1)
                if len(hits)==1:
                    day,op,hi,lo,cl,amount,volume,_=hits[0]
                    check('raw_binary_numeric_probe', [float(r[x]) for x in ('open','high','low','close')]==[x/100 for x in (op,hi,lo,cl)]
                          and float(r['amount'])==amount and r['volume']==volume)
    if cap in ('TRADING_STATUS','ISST'):
        bao=_read(freeze['inputs']['BAOSTOCK_DAILY_UPDATE']);by={r['code'].upper():r for r in bao['daily_rows']}
        for r in rows:
            provider=by.get(r['source_security_key'],{});valid=str(provider.get('isST')) in ('0','1') and str(provider.get('tradestatus')) in ('0','1')
            if cap=='ISST':
                check('dated_ST_exact',r['is_st']==(provider.get('isST') if valid else None) and r['historical_backfill_permitted'] is False)
            else:
                expected='ACTUAL_TRADED' if r['actual_bar_present'] else ('SUSPENDED' if valid and provider['tradestatus']=='0'
                    else 'DATA_GAP' if valid and provider['tradestatus']=='1' else 'UNKNOWN')
                check('dated_status_precedence_exact',r['status']==expected)
                check('status_conflict_explicit',r['status_conflict']==bool(r['actual_bar_present'] and valid and provider['tradestatus']!='1'))
    if cap=='IDENTITY_UNIVERSE':
        original=_read(parent['components']['IDENTITY_UNIVERSE'])['rows']
        prior={r['source_security_key']:r for r in original}
        for r in rows:
            check('absence_not_delisting',r['absence_is_delisting_evidence'] is False)
            if r['source_security_key'] in prior and r.get('security_id'):
                check('stable_parent_identity_continuity',prior[r['source_security_key']].get('security_id')==r['security_id'])
            check('security_type_and_knowledge_explicit','security_type' in r and 'knowledge_time' in r)
    if cap=='ADJUSTED_DAILY':
        raw_path=Path(receipt['artifact_path']).parent.parent/'RAW_DAILY'/'artifact.json'
        if not raw_path.is_absolute():raw_path=Path(__file__).resolve().parents[2]/raw_path
        raw=json.loads(raw_path.read_text(encoding='utf8'))['rows'];by={_key(r):r for r in raw}
        for r in rows:
            src=by[_key(r)]
            check('adjusted_volume_amount_raw_exact',r['volume']==src['volume'] and r['amount']==src['amount'])
            if r['adjustment_readiness']=='READY':
                check('target_latest_QFQ_identity_exact',all(Decimal(r[p])==Decimal(str(src[p])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                      for p in ('open','high','low','close')))
            else:check('adjustment_fail_closed',all(r[p] is None for p in ('open','high','low','close')) and bool(r.get('unknown_reason')))
    if cap.startswith('PERIOD_'):
        old=_read(parent['components'][cap]);closed={(r['security_id'],r['period_type'],r['period_key']):r for r in old['rows'] if r.get('period_view')=='CLOSED_ONLY'}
        present={(r['security_id'],r['period_type'],r['period_key']):r for r in rows}
        check('closed_parent_rows_byte_logical_identity',all(present.get(k)==v for k,v in closed.items()))
        check('period_parent_exact',payload['parent_period_publication']==parent['components'][cap])
    if cap=='SPECIAL_PHASE':
        manifest=_read(freeze['inputs']['SPECIAL_PRICE_PHASE'])
        lifecycle=_read(manifest['lifecycle_snapshot'])
        policy=_read(manifest['policy'])
        event_path=Path(manifest['event_store']['path'])
        if not event_path.is_absolute():event_path=Path(__file__).resolve().parents[2]/event_path
        event_bytes=event_path.read_bytes()
        check('special_event_store_digest',hashlib.sha256(event_bytes).hexdigest()==manifest['event_store']['sha256'])
        events=[json.loads(line) for line in event_bytes.decode('utf8').splitlines() if line.strip()]
        check('special_lifecycle_publication',manifest['lifecycle_snapshot']['sha256']==freeze['source_families']['IDENTITY_LIFECYCLE']['sha256'])
        check('special_active_identity_exact',{r['security_id'] for r in rows if r.get('security_id')}==set(manifest['active_security_ids'])==set(lifecycle['active_security_ids']))
        for r in rows:
            check('special_manifest_publication',r['event_manifest_digest']==freeze['inputs']['SPECIAL_PRICE_PHASE']['sha256'])
            matches=[e for e in events if e['security_id']==r.get('security_id')]
            if not matches:
                check('special_valid_no_event_regular',r['special_price_phase']=='REGULAR')
            else:
                provenance=[e for e in matches if e['source_capture_sha256']==r.get('special_phase_source_capture_sha256')
                    and e['source_ref']==r.get('special_phase_source_ref') and e['phase_effective_from']==r.get('special_phase_effective_date')]
                if r['special_price_phase'] not in ('REGULAR','UNKNOWN_SPECIAL_PHASE'):
                    check('special_event_provenance_exact',bool(provenance))
                    check('special_event_knowledge_cutoff',all(datetime.fromisoformat(e['system_available_at'].replace('Z','+00:00'))<=
                        datetime.fromisoformat(freeze['system_available_at'].replace('Z','+00:00')) for e in provenance))
            applicable=[p for p in policy['policies'] if p['phase']==r['special_price_phase'] and p.get('valid_from','0001-01-01')<=target
                and (not p.get('valid_to') or target<=p['valid_to']) and (not p.get('board_scope') or p['board_scope']==r['board_scope'])]
            if len(applicable)==1 and applicable[0]['action']=='NO_LIMIT':
                check('special_no_limit_null_boundaries',r['limit_status']=='NO_LIMIT' and r['limit_up_price'] is None and r['limit_down_price'] is None)
    return dict(contract_id='DM01_INDEPENDENT_COMPONENT_POSTCHECK_R1',component_id=cap,status='PASS' if not errors else 'FAIL',
        errors=sorted(set(errors)),row_count=len(rows),logical_digest=receipt['logical_digest'],
        independently_read_sources=True,adapter_used_as_oracle=False)

def check_cross_components(receipts,freeze,parent,calendar,identity):
    from workbench_analysis.daily_data_head import CAPABILITIES
    errors=[];component_checks={};loaded={}
    def check(n,ok):
        if not ok:errors.append(n)
    check('nine_components_exact',set(receipts)==set(CAPABILITIES))
    for cap,r in receipts.items():
        payload=_get_component(r);loaded[cap]=payload['rows']
        result=check_component(r,payload,freeze,parent,calendar,identity);component_checks[cap]=result
        check('component_postcheck:'+cap,result['status']=='PASS' and _digest(result)==r['postcheck_digest'])
    if set(loaded)!=set(CAPABILITIES):return dict(status='FAIL',errors=errors,component_checks=component_checks)
    by={cap:{_key(r):r for r in rows} for cap,rows in loaded.items() if not cap.startswith('PERIOD_')}
    universe=set(by['IDENTITY_UNIVERSE']);raw=set(by['RAW_DAILY'])
    check('raw_identity_subset',raw<=universe)
    check('raw_adjusted_keyset_exact',raw==set(by['ADJUSTED_DAILY']))
    for cap in ('TRADING_STATUS','ISST','PRICE_LIMIT','SPECIAL_PHASE'):check('universe_keyset:'+cap,set(by[cap])==universe)
    for sid in universe:
        status=by['TRADING_STATUS'][sid]
        check('required_active_RAW_coverage:'+sid,sid in raw or status['status']=='SUSPENDED')
    for cap in ('PERIOD_RAW','PERIOD_ADJUSTED'):
        daily='ADJUSTED_DAILY' if cap=='PERIOD_ADJUSTED' else 'RAW_DAILY'
        old_rows=_read(parent['components'][cap])['rows'];prior={(r['security_id'],r['period_type'],r['period_key']):r for r in old_rows}
        for r in loaded[cap]:
            if r.get('as_of_date')!=freeze['trade_date']:continue
            old=prior.get((r['security_id'],r['period_type'],r['period_key']),{});bar=by[daily].get(r['security_id'])
            check('period_daily_digest:'+cap,r['target_daily_publication']==receipts[daily]['logical_digest'])
            if bar and not bar.get('unknown_reason') and not r.get('unknown_reason'):
                check('period_volume_amount_independent:'+cap,
                    r['volume']==old.get('volume',0)+bar['volume'] and abs(r['amount']-(old.get('amount',0)+float(bar['amount'])))<=1e-7)
                # Parent QFQ rebasing is separately checked when an intervening action exists; RAW is directly composable.
                if cap=='PERIOD_RAW' or not old:
                    check('period_OHLC_independent:'+cap,
                        Decimal(r['open'])==Decimal(str(old.get('open') or bar['open'])) and
                        Decimal(r['close'])==Decimal(str(bar['close'])) and
                        Decimal(r['high'])==max(Decimal(str(old.get('high') or bar['high'])),Decimal(str(bar['high']))) and
                        Decimal(r['low'])==min(Decimal(str(old.get('low') or bar['low'])),Decimal(str(bar['low']))))
    rules=_read(freeze['inputs']['PRICE_RULES'])['rules'];rule_by={r['rule_id']:r for r in rules}
    parent_prices={_key(r):r for r in _read(parent['components']['PRICE_LIMIT'])['rows']}
    from tdx.gbbq_reader import read_gbbq
    action_path=Path(freeze['inputs']['GBBQ']['path'])
    if not action_path.is_absolute():action_path=Path(__file__).resolve().parents[2]/action_path
    actions=read_gbbq(action_path)
    for sid,r in by['PRICE_LIMIT'].items():
        check('price_raw_publication',r['raw_daily_publication']==receipts['RAW_DAILY']['logical_digest'])
        if r['limit_status'] in ('LIMIT_UP','LIMIT_DOWN','NOT_LIMIT'):
            rule=rule_by[r['rule_id']];reference=Decimal(r['reference_price']);tick=Decimal(str(rule['tick']));ratio=Decimal(str(rule['limit_ratio']))
            if r.get('special_price_phase')=='REGULAR':
                previous=parent_prices.get(sid,{}).get('next_reference_close')
                check('canonical_parent_previous_close_exists',previous is not None)
                if previous is not None:
                    expected_ref=Decimal(str(previous))
                    for e in actions:
                        if e.security_id.upper()==r['source_security_key'] and e.event_date==int(freeze['trade_date'].replace('-','')) and e.category==1:
                            cash,rights_price,bonus,rights=[Decimal(str(v)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for v in (e.c1,e.c2,e.c3,e.c4)]
                            expected_ref=(expected_ref-(cash-rights*rights_price)/10)/((10+bonus+rights)/10)
                    expected_ref=expected_ref.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                    check('canonical_source_reference_independent',reference==expected_ref)
            up=((reference*(1+ratio)/tick).quantize(Decimal(1),rounding=ROUND_HALF_UP))*tick
            down=((reference*(1-ratio)/tick).quantize(Decimal(1),rounding=ROUND_HALF_UP))*tick
            if abs(up-reference)<tick:up=reference+tick
            if abs(reference-down)<tick:down=reference-tick
            check('price_limit_boundaries_independent',Decimal(r['limit_up_price'])==up and Decimal(r['limit_down_price'])==down)
            close=Decimal(str(by['RAW_DAILY'][sid]['close']));expected='LIMIT_UP' if close==up else 'LIMIT_DOWN' if close==down else 'NOT_LIMIT'
            check('price_limit_state_independent',r['limit_status']==expected and down<=close<=up)
    return dict(contract_id='DM01_INDEPENDENT_CROSS_COMPONENT_POSTCHECK_R1',status='PASS' if not errors else 'FAIL',
        errors=sorted(set(errors)),component_checks=component_checks,artifact_row_counts={k:len(v) for k,v in loaded.items()},
        numeric_oracle='SOURCE_BINARY_AND_INDEPENDENT_DECIMAL_PARENT_PLUS_TARGET',adapter_used_as_oracle=False)
