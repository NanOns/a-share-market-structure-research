"""Current R4 reconciliation; original acquisition receipts remain historical."""
import csv,io,json,struct,zipfile,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.corrected_owner_replay import load,checked,gzrows,gzwrite,ref,OUT
from workbench_analysis.market_source_acquisition import write,is_stock_code,now
from workbench_analysis.tdx_official_daily_source import _atomic_write


def main():
    out=ROOT/OUT;capture=load(ROOT/'docs/evidence/source_acquisition_r4_20261009/capture/acquisition.json')
    core=load(out/'CORE_REPLAY.json');profile=load(out/'PROFILE_STRUCTURE_REPLAY.json');health=load(out/'HEALTH_PROJECTION_REPLAY.json')
    sectors=load(out/'SECTOR_REPLAY.json');original=load(ROOT/'docs/evidence/source_acquisition_r4_20261009/03_FOUR_SESSION_QFQ_GAP_RECAPTURE_AND_ADJUSTMENT_ORACLE.json')
    legacy={(r['trade_date'],r['source_security_key']):r for r in original['legacy_rows']}
    batch={};history={};factor={};queries={};official={};matrix=[];gap=[];oracle=[];summary=[]
    dates=[o['trade_date'] for o in core['owners']]
    for q in capture['queries']:
        if not q.get('path'):continue
        payload=load(q['path']);m=q['method'];p=q['params'];rows=payload.get('rows',[])
        if m=='query_daily_history_k_AStock':batch[p['date']]={r['code'].lower():r for r in rows};queries[p['date']]=q
        elif m=='query_history_k_data_plus':
            for r in rows:history[r['date'],r['code'].lower(),p['adjustflag']]=r
        elif m=='query_adjust_factor':factor[p['code'].lower()]=rows
    with zipfile.ZipFile(checked(ROOT,core['owners'][0]['sources']['package'])) as z:
        for name in z.namelist():
            parts=name.lower().replace('\\','/').split('/');leaf=parts[-1];market=next((p for p in parts if p in ('sh','sz','bj')),None)
            if not market or not leaf.endswith('.day'):continue
            code=market+'.'+leaf[-10:-4]
            if not is_stock_code(code):continue
            for r in struct.iter_unpack('<IIIIIfII',z.read(name)):
                day=str(r[0]);day=day[:4]+'-'+day[4:6]+'-'+day[6:]
                if day in dates:official[day,code]=dict(zip(('open','high','low','close'),[v/100 for v in r[1:5]]),amount=r[5],volume=r[6])
    for own,p,h,s in zip(core['owners'],profile['owners'],health['owners'],sectors['owners']):
        day=own['trade_date'];rows=gzrows(checked(ROOT,own['core']));factors={r['source_security_key'].lower():r for r in rows}
        prev={r['security_id']:r for r in gzrows(checked(ROOT,own['prior_core']))}
        adjusted={r['security_id']:r for r in gzrows(checked(ROOT,own['adjusted']))};counts=Counter()
        codes=set(factors)|set(batch[day])|{code for d,code in official if d==day}
        for code in sorted(codes):
            f=factors.get(code);b=batch[day].get(code);o=official.get((day,code));old=legacy.get((day,code));sid=f['security_id'] if f else None
            a=adjusted.get(sid,{});suspended=(b or {}).get('tradestatus')=='0';local=capture['local'].get(code,{})
            known={k:v.get('value') is not None and v.get('quality_state')=='OBSERVED' for k,v in (f or {}).get('fields',{}).items()}
            atr=known.get('atr20',False);prioratr=prev.get(sid,{}).get('fields',{}).get('atr20',{}).get('value') is not None
            blockers=[]
            if not f:blockers.append('CANONICAL_IDENTITY_UNPROVEN')
            if suspended and not o:blockers.append('TRADING_SUSPENSION_NO_BAR')
            elif not o:blockers.append('RAW_BAR_NOT_CAPTURED')
            if f and not atr:blockers.append('ATR20_WINDOW_UNKNOWN')
            if f and not prioratr:blockers.append('T_MINUS_1_ATR20_WINDOW_UNKNOWN')
            if history.get((day,code,'2')):blockers.append('BAOSTOCK_QFQ_PROVIDER_COORDINATE_NOT_SUBSTITUTED')
            diffs={k:float(b[k])-o[k] for k in ('open','high','low','close') if b and o and b.get(k)}
            conflict=any(abs(v)>.011 for v in diffs.values())
            if conflict:blockers.append('CROSS_SOURCE_PRICE_BASIS_CONFLICT')
            row=dict(trade_date=day,source_security_key=code,security_id=sid or 'UNPROVEN',
                local_tdx_raw=day in local.get('bars',{}),official_tdx_raw=bool(o),baostock_raw=bool(b),
                official_source_hash=own['sources']['package']['sha256'],baostock_query_hash=queries[day]['hash'],
                raw_gap=not o and not suspended,qfq_current_ready=a.get('adjustment_readiness')=='READY',
                atr20_ready=atr,prior_atr20_ready=prioratr,suspended_no_bar=suspended and not o,
                baostock_qfq=bool(history.get((day,code,'2'))),baostock_factor=bool(factor.get(code)),
                source_conflict=conflict,raw_ohlc_differences=json.dumps(diffs),exact_blockers='|'.join(blockers),
                historical_as_recorded='NOT_PROVEN',lineage='RECONSTRUCTED_CORRECTED',accepted=False)
            matrix.append(row)
            if old:
                gap.append(dict(**row,before=old.get('old_reason',old.get('decision')),old_qfq_gap=old.get('decision')=='QFQ_FACTOR_UNAVAILABLE',
                    usable_corrected=bool(o and atr and prioratr),residual_unknown=bool(not suspended and not(atr and prioratr))))
            if diffs:
                oracle.append(dict(trade_date=day,code=code,category='RAW_TDX_VS_BAOSTOCK',OHLC_differences=diffs,
                    pass_diagnostic=not conflict,tolerance_scope='0.011 diagnostic only; native producer does not consume provider prices'))
            counts['official_all_A_stock_raw']+=bool(o);counts['suspended_no_bar']+=suspended and not o
            counts['canonical_identity_unproven_raw']+=bool(o and not f);counts['raw_gap']+=row['raw_gap'];counts['source_conflict']+=conflict
        qfq=[r for r in gap if r['trade_date']==day and r['old_qfq_gap']]
        summary.append(dict(trade_date=day,official_session=True,**counts,full_universe_count=len(codes),
             identity_stock_count=len(rows),canonical_tdx_raw_count=own['actual_raw_rows'],baostock_daily_count=len(batch[day]),
             gbbq_ready=own['adjustment_current_ready'],qfq_capability_unknown=sum(not r['atr20_ready'] for r in matrix if r['trade_date']==day and r['security_id']!='UNPROVEN' and not r['suspended_no_bar']),
             atr20_known=own['known_fields']['atr20'],core_profile_ready=True,
             industry_concept_membership_count=dict(CSRC_INDUSTRY=s['membership_count'],TDX_INDUSTRY_CONCEPT=50162 if day=='2026-09-30' else 'NOT_VERIFIABLE'),
             structure_known_count=dict(**{k:v['known'] for k,v in p['counts'].items()},structure_health_repaired=h['known'],relative_sector_state=s['relative_sector_known']),
             legacy_qfq_before=len(qfq),legacy_qfq_usable=sum(r['usable_corrected'] for r in qfq),legacy_qfq_residual=sum(r['residual_unknown'] for r in qfq),
             first_acquired_at=queries[day]['received_at'],data_head_candidate=own['core'],accepted_head_before='2026-09-30',accepted_head_after='2026-09-30',
             real_request_count=dict(date_specific_queries=sum(q['params'].get('date',q['params'].get('day'))==day for q in capture['queries']),shared_range_queries='See original request ledger; do not sum per-date shared requests')))
    text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=list(matrix[0]));writer.writeheader();writer.writerows(matrix)
    _atomic_write(out/'FOUR_SESSION_SOURCE_MATRIX_V2.csv',text.getvalue().encode('utf-8-sig'),tdx_root=Path('D:/new_tdx'))
    write(out/'LEGACY_528_AND_35_RECONCILIATION_V2.json',dict(rows=gap,old_qfq_count=sum(r['old_qfq_gap'] for r in gap),old_other_count=sum(not r['old_qfq_gap'] for r in gap),summary=summary))
    oraclebinding=gzwrite(ROOT,out/'RAW_CROSS_SOURCE_ORACLE_V2.jsonl.gz',oracle)
    write(out/'FOUR_SESSION_FINAL_RECONCILIATION.json',dict(dates=summary,source_matrix=ref(ROOT,out/'FOUR_SESSION_SOURCE_MATRIX_V2.csv'),
         raw_oracle=oraclebinding,raw_comparisons=len(oracle),raw_conflicts=sum(not r['pass_diagnostic'] for r in oracle),
         native_adjustment_oracle=ref(ROOT,out/'CORE_REPLAY.json'),historical_receipts_preserved=True,
         supersedes_current_claims_in='Original 02/03/08 receipts are pre-correction historical evidence; this is the current readback',updated_at=now()))
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
