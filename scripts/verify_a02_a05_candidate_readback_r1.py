"""Independent source/readback oracle for A02/A05, runnable in clean checkout."""
from pathlib import Path
import gzip
import json
from hashlib import sha256
from decimal import Decimal
from collections import Counter
from datetime import date
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from v4.rps_pit_history_a02_v1 import read_bound,digest
from v4.rps_history_reader_a02_v1 import read_triplet

def verify_bytes(ref, seen):
    identity=(ref['path'],ref['sha256'])
    if identity in seen: return
    path=(ROOT/ref['path']).resolve()
    if not path.is_relative_to(ROOT): raise ValueError('ORACLE_PATH_ESCAPE')
    payload=path.read_bytes()
    if sha256(payload).hexdigest()!=ref['sha256'] or len(payload)!=ref.get('bytes',ref.get('byte_count',len(payload))): raise ValueError('ORACLE_SOURCE_BINDING_MISMATCH:'+ref['path'])
    seen.add(identity)

def gzip_rows(ref,seen):
    verify_bytes(ref,seen)
    with gzip.open(ROOT/ref['path'],'rt',encoding='utf8') as stream:
        return [json.loads(line) for line in stream]

def verify_a02():
    import pandas as pd
    evidence=json.loads((ROOT/'reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R3.json').read_text(encoding='utf8'))
    seen=set();publications={};inputs={};source_rows=None;sessions=None;count=0;bad=0
    for day,ref in evidence['inputs'].items():
        inp=read_bound(ROOT,ref);inputs[day]=inp;sessions=inp['sessions']
        if source_rows is None:
            rows=gzip_rows(inp['source_bindings']['bounded_price_rows'],seen)
            source_rows={(r['security_id'],r['trade_date']):r for r in rows}
        for source in inp['source_bindings']['accepted_sources']: verify_bytes(source,seen)
        pub=read_bound(ROOT,evidence['publications'][day]);publications[day]=pub
        from v4.rps_history_producer_a02_r2 import publish as compatible_publish
        assert compatible_publish(inp,pub['previous_publication'])==pub
        assert pub['input_digest']==digest(inp)
        assert pub['logical_digest']==digest({k:v for k,v in pub.items() if k!='logical_digest'})
        assert pub['universe_identity']['members_digest']==digest(inp['universe'])
        index=sessions.index(day)
        for h in (5,20):
            returns={}
            for sid in inp['universe']:
                window=sessions[max(0,index-h):index+1];rows=[source_rows.get((sid,d)) for d in window];a=rows[0];b=rows[-1]
                reason=None
                if len(window)!=h+1: reason='INSUFFICIENT_SESSION_HISTORY'
                elif a is None or b is None or a['state']!='ACTUAL_TRADED' or b['state']!='ACTUAL_TRADED': reason='MISSING_OR_SUSPENDED_ENDPOINT'
                elif any(r is None or r['state'] not in ('ACTUAL_TRADED','SUSPENDED') for r in rows): reason='UNEXPLAINED_DATA_GAP'
                elif any(r['quality']!='READY' for r in rows): reason='ADJUSTMENT_UNKNOWN'
                elif (Decimal(a['mul']),Decimal(a['add']))!=(Decimal(b['mul']),Decimal(b['add'])): reason='MIXED_ADJUSTMENT_IDENTITY'
                elif Decimal(a['close'])<=0 or Decimal(b['close'])<=0: reason='INVALID_PRICE'
                expected=None if reason else float(b['close'])/float(a['close'])-1
                trace=inp['endpoint_evidence'][sid][str(h)]
                bad+=trace['unknown_reason']!=reason or trace['window_digest']!=digest(rows) or trace['start']!=a or trace['end']!=b or inp['returns'][str(h)][sid]!=expected
                returns[sid]=expected;count+=1
            # Third independent implementation: pandas average rank, not producer/oracle pairwise.
            values=pd.Series(returns,dtype='float64');n=int(values.notna().sum());ranks=(values.rank(method='average')-1)*100/(n-1) if n>=2 else values*float('nan')
            for row in pub['rows']:
                expected=None if pd.isna(ranks[row['security_id']]) else float(ranks[row['security_id']]);actual=row[f'rps{h}']['value']
                bad+=actual is not None if expected is None else actual is None or abs(actual-expected)>1e-12
                count+=1
    # Reconstruct the frozen bounded observation set directly from accepted source
    # artifacts, independently of the producer's stored endpoint/return values.
    import pyarrow.parquet as pq
    authority_chain=read_bound(ROOT,inp['data_authority']['chain'])
    historical=inputs[min(inputs)]['source_bindings']['accepted_sources'][0]
    historical_rows=[r for r in source_rows.values() if r['trade_date']<='2026-09-24']
    start=min(r['trade_date'] for r in historical_rows)
    actual=pq.read_table(ROOT/historical['path'],columns=['canonical_security_id','source_security_key','trade_date','qfq_close','qfq_mul','qfq_add','adjusted_quality','trading_status','adjustment_source_revision'],filters=[('trade_date','>=',int(start.replace('-',''))),('trade_date','<=',20260924)]).to_pylist()
    assert len(actual)==len(historical_rows)
    for r in actual:
        raw=str(r['trade_date']);day=raw[:4]+'-'+raw[4:6]+'-'+raw[6:]
        expected=dict(security_id=r['canonical_security_id'],trade_date=day,source_security_key=r['source_security_key'],close=str(r['qfq_close']) if r['qfq_close'] is not None else None,mul=str(r['qfq_mul']),add=str(r['qfq_add']),quality=r['adjusted_quality'],state=r['trading_status'],adjustment_revision=r['adjustment_source_revision'])
        assert source_rows[(r['canonical_security_id'],day)]==expected
    for node in authority_chain['nodes']:
        day=node['trade_date'];component=node['components']['ADJUSTED_DAILY']
        artifact=read_bound(ROOT,dict(path=component['artifact_path'],sha256=component['artifact_sha256'],bytes=component['artifact_bytes']))
        actual_ids=set()
        for r in artifact['rows']:
            actual_ids.add(r['security_id'])
            expected=dict(security_id=r['security_id'],trade_date=day,source_security_key=r['source_security_key'],close=r['close'],mul=r['qfq_mul'],add=r['qfq_add'],quality=r['adjustment_readiness'],state='ACTUAL_TRADED',adjustment_revision=r['adjustment_source_revision'])
            assert source_rows[(r['security_id'],day)]==expected
        status=node['components']['TRADING_STATUS'];rows=read_bound(ROOT,dict(path=status['artifact_path'],sha256=status['artifact_sha256'],bytes=status['artifact_bytes']))['rows']
        for r in rows:
            if r['security_id'] not in actual_ids and r.get('trading_status')=='SUSPENDED':
                assert source_rows[(r['security_id'],day)]['state']=='SUSPENDED'
        assert sum(d==day for _,d in source_rows)==len(actual_ids)+sum(r['security_id'] not in actual_ids and r.get('trading_status')=='SUSPENDED' for r in rows)
    previous=None
    for day in sorted(publications):
        assert publications[day]['previous_publication']==previous
        previous=evidence['publications'][day]
    for coordinate,ref in evidence['deltas'].items():
        day,offset=coordinate.split(':T-');offset=int(offset);prior_day=sessions[sessions.index(day)-offset];current=publications[day];prior=publications.get(prior_day)
        now={r['security_id']:r for r in current['rows']};before={r['security_id']:r for r in prior['rows']} if prior else {}
        output=read_bound(ROOT,ref)
        for row in output['rows']:
            sid=row['security_id']
            for h in (5,20):
                cv=now[sid][f'rps{h}']['value'];pv=before.get(sid,{}).get(f'rps{h}',{}).get('value')
                reason=f'T_MINUS_{offset}_PUBLICATION_MISSING' if prior is None else 'PRIOR_UNIVERSE_MEMBER_MISSING' if sid not in before else 'RPS_ENDPOINT_UNKNOWN' if cv is None or pv is None else None
                expected=None if reason else cv-pv;field=row['fields'][f'rps{h}_delta{offset}']
                bad+=field['unknown_reason']!=reason or field['value']!=expected or field['current_publication_digest']!=current['logical_digest'] or field['prior_publication_digest']!=(prior['logical_digest'] if prior else None)
                count+=1
    for day,ref in evidence['publications'].items():
        index=sessions.index(day);priorrefs={o:evidence['publications'].get(sessions[index-o]) for o in (1,3)}
        read_triplet(ROOT,ref,priorrefs,sessions)
    # Full downstream readback binds every old/new row and full business diff.
    refs=evidence['downstream_replay']['artifacts'];records=[gzip_rows(r,seen) for r in refs[2:]]
    assert len(records[0])==len(records[1])==5222 and len(records[2])==10444
    assert sum(bool(r['business_changes']) for r in records[2] if r['package']=='V4_07')==evidence['downstream_replay']['seed_business_changed']
    assert sum(bool(r['business_changes']) for r in records[2] if r['package']=='V4_09')==evidence['downstream_replay']['stock_business_changed']
    lookups={name:{r['security_id']:r for r in record} for name,record in zip(('V4_07','V4_09'),records[:2])}
    for row in records[2]:
        pair=lookups[row['package']][row['security_id']]
        for field,change in row['business_changes'].items():
            assert change==dict(old=pair['old'][field],new=pair['new'][field])
    seedref=evidence['downstream_replay']['seed_amendment_artifact'];seedrows=gzip_rows(seedref,seen)
    assert seedrows==[r['new'] for r in records[0]]
    assert evidence['downstream_replay']['new_stock_context']['source_bindings']['seed_artifact']['sha256']==seedref['sha256']
    assert evidence['downstream_replay']['new_seed_context']['publication_id']!=evidence['downstream_replay']['source_context']['publication_id']
    assert evidence['downstream_replay']['new_seed_context']['profile_row_publication_id']!=evidence['downstream_replay']['source_context']['profile_row_publication_id']
    for ref in refs: verify_bytes(ref,seen)
    verify_bytes(evidence['reader_runtime_binding'],seen)
    assert not bad, ('A02_INDEPENDENT_MISMATCH',bad)
    return dict(status='PASS',checked_endpoint_rank_delta_values=count,real_source_rows_reconstructed=len(source_rows),verified_source_artifact_count=len(seen),mismatches=bad,publications=len(publications),T_T_MINUS_1_T_MINUS_3='EXACT_BOUND_NO_RUNTIME_RECOMPUTE')

def verify_a05():
    import pyarrow.parquet as pq
    evidence=json.loads((ROOT/'reports/audits/A05_EXACT_RECOVERY_EVIDENCE_R2.json').read_text(encoding='utf8'))
    inp=read_bound(ROOT,evidence['input_binding']);seen=set()
    for ref in inp['original_byte_archives'].values(): verify_bytes(ref,seen)
    from sector.legacy_valid_member_a05_v1 import exact_value
    original=inp['original_byte_archives'];receipt=read_bound(ROOT,original['reports/phase2/PHASE2_FINAL_RECEIPT.json'])
    for key in ('data/sectors/sector_membership_daily.parquet','data/sectors/sector_factors_daily.parquet'):
        assert original[key]['sha256']==receipt['output_sha256'][key]
    subset=list(inp['legacy_outputs'][0]);day=date.fromisoformat(inp['trade_date'])
    actual=pq.read_table(ROOT/original['data/sectors/sector_factors_daily.parquet']['path'],columns=subset,filters=[('date','=',day)]).to_pylist()
    assert actual==inp['legacy_outputs']
    members=pq.read_table(ROOT/original['data/sectors/sector_membership_daily.parquet']['path'],columns=['sector_id','sector_role','security_id'],filters=[('date','=',day)]).to_pylist()
    assert members==inp['membership']
    facts={r['source_security_id']:r for r in inp['observations']};groups={}
    for row in members:
        if row['security_id'] is not None: groups.setdefault(row['sector_id'],set()).add(row['security_id'])
    mismatches=0
    for row in actual:
        ids=groups.get(row['sector_id'],set());total=len(ids)
        # Direct set oracle independent of extracted scalar producer.
        import re
        valid={sid for sid in ids if sid in facts and re.fullmatch(r'(SH|SZ|BJ)\.\d{6}',sid) and facts[sid]['missing_state'] is not None and facts[sid]['missing_state'] not in ('FILE_MISSING','DELISTED_OR_INACTIVE')}
        assert len(valid)==sum(exact_value(sid,facts[sid]['missing_state']) for sid in ids if sid in facts)
        reasons=[];role=row['sector_role']
        if total<(5 if role=='INDUSTRY' else 8): reasons.append('MIN_TOTAL_MEMBERS')
        if len(valid)<5: reasons.append('MIN_VALID_MEMBERS')
        if not total or len(valid)/total<.70: reasons.append('LOW_COVERAGE')
        if role=='EXCLUDE_FROM_THEME_RANK': reasons.append('EXCLUDED_ROLE')
        mismatches+=row['valid_member_count']!=len(valid) or row['total_member_count']!=total or row['invalid_member_count']!=total-len(valid) or row['coverage']!=(len(valid)/total if total else 0) or row['sector_valid']!=bool(not reasons) or row['invalid_reason']!='|'.join(reasons)
    import csv,io
    golden=json.loads((ROOT/'reports/audits/A05_REAL_GOLDEN_SAMPLE_READBACK_R1.json').read_text(encoding='utf8'));golden_count=0
    for item in golden['archives']:
        verify_bytes(item['archive'],seen)
        assert item['archive']['sha256']==item['original_namespace']['sha256']
        for row in csv.DictReader(io.StringIO((ROOT/item['archive']['path']).read_bytes().decode('utf-8-sig'))):
            if 'valid_member' in row and 'missing_state' in row:
                assert exact_value(row['security_id'],row['missing_state'] or None)==(row['valid_member'].lower()=='true')
                golden_count+=1
    assert golden_count==golden['real_member_values_checked']
    assert not mismatches, ('A05_INDEPENDENT_MISMATCH',mismatches)
    return dict(status='PASS',original_bytes_match_legacy_receipt=True,real_sector_outputs_checked=len(actual),observations=len(facts),real_golden_member_values_checked=golden_count,mismatches=mismatches)

def main():
    result=dict(contract_id='A02_A05_INDEPENDENT_READBACK_V1',A02=verify_a02(),A05=verify_a05(),status='PASS',production=False,formal_consumer_enabled=False)
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__': main()
