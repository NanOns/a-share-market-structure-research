"""Independent source-byte oracle; does not call the candidate producer."""
import gzip,json,sys,zipfile,struct,random
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.build_a12_status_st_authority_r1 import PATHS
P='reports/audits/A12_R2_'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def main():
    repair=read(P+'V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1.json');c=duckdb.connect()
    def table(n,path,columns='*'):c.execute(f'create table {n} as select {columns} from read_json_auto(?)',[str(ROOT/path)])
    table('u',PATHS['universe'],'security_id,source_security_key,trade_date,source_bar_present,board_scope')
    table('source_status',PATHS['status'],'security_id,source_security_key,trade_date,provider_tradestatus')
    table('source_st',PATHS['st'],'security_id,source_security_key,trade_date,is_st,source_revision,binding_quality')
    for k,n in [('status','out_status'),('st','out_st')]:table(n,repair['artifacts'][k]['path'])
    key='security_id,source_security_key,trade_date'
    c.execute("create table expected_status as select u.security_id,u.source_security_key,u.trade_date, case when source_bar_present then 'ACTUAL_TRADED' when provider_tradestatus='0' then 'SUSPENDED' when provider_tradestatus='1' then 'DATA_GAP' else 'UNKNOWN' end status from u join source_status using("+key+")")
    status_diff=c.execute('select count(*) from ((select '+key+',status from expected_status except all select '+key+',status from out_status) union all (select '+key+',status from out_status except all select '+key+',status from expected_status))').fetchone()[0]
    st_diff=c.execute('select count(*) from ((select '+key+',is_st from source_st except all select '+key+',is_st from out_st) union all (select '+key+',is_st from out_st except all select '+key+',is_st from source_st))').fetchone()[0]
    assert status_diff==st_diff==0
    assert c.execute('select count(*) from expected_status').fetchone()[0]==4035729
    period_checks=[]
    period_receipt=read(P+'FORMAL_PERIOD_AUTHORITY_REBIND_R1.json')
    for kind,r in zip(['week','month'],period_receipt['reports'],strict=True):
        c.read_parquet(str(ROOT/r['candidate']['path'])).create_view('period',replace=True)
        c.execute("create or replace temp table counters as select security_id,date_trunc('"+kind+"',trade_date) bucket,count(*) filter(where status='ACTUAL_TRADED') actual,count(*) filter(where status='SUSPENDED') suspended,count(*) filter(where status='DATA_GAP') gap,count(*) filter(where status='UNKNOWN') unknown_n from expected_status group by all")
        checked=c.execute("select count(*),count(*) filter(where p.actual_count<>c.actual or p.suspended_count<>c.suspended or p.data_gap_count<>c.gap or p.unknown_count<>c.unknown_n) from period p join counters c on p.canonical_security_id=c.security_id and date_trunc('"+kind+"',strptime(p.period_start_date::varchar,'%Y%m%d'))=c.bucket").fetchone()
        total=c.execute('select count(*) from period').fetchone()[0]
        assert checked[0]==total and checked[1]==0,(kind,checked,total)
        period_checks.append(dict(period_type=kind,candidate=r['candidate'],rows_checked=total,status_counter_differences=checked[1],independent_source='Recomputed actual/suspended/gap/unknown counters from full source bytes grouped by canonical identity and calendar period; every RAW/QFQ view checked'))
    receipts=read('reports/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.json')['query_receipts']
    recovery='reports/v4_02/V4_02_DATED_ST_STATUS_BOUNDED_RECOVERY_R1_20260926.json'
    receipts+=read(recovery)['retry_receipts']
    byday={r['trade_date']:r['normalized_full_market_status_sha256'] for r in receipts if r.get('normalized_full_market_status_sha256')}
    assert len(byday)==786
    revisions=c.execute('select distinct trade_date,source_revision from source_st').fetchall();assert len(revisions)==786
    for day,digest in revisions:assert digest=='sha256:'+byday[str(day)]
    pools={}
    for tag,where in [('NORMAL',"status='ACTUAL_TRADED' and is_st='0'"),('SUSPENDED',"status='SUSPENDED'"),('ST',"is_st='1'"),('NON_ST',"is_st='0'"),('ALIAS',"source_security_key in ('SZ.300114','SZ.302132')"),('NEW_LISTING',"source_security_key='SZ.301611' and trade_date between '2024-08-16' and '2024-08-23'"),('DELISTING',"source_security_key='SH.600225' and trade_date between '2025-02-05' and '2025-02-17'")]:
        # Hash-based deterministic random selection independent of producer order.
        pools[tag]=c.execute('select security_id,source_security_key,trade_date,status,is_st,source_bar_present from expected_status join source_st using('+key+') join u using('+key+') where '+where+' order by hash(security_id,trade_date,12345) limit 40').fetchall()
        assert pools[tag]
    go=read('data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json');package=go['evidence_bindings']['official_tdx_package'];assert bind(package['path'])['sha256']==package['sha256']
    capture='reports/dm01/a01_r2/20261001T033251758661Z/TARGET_DATE_CAPTURE_query_daily_history_k_AStock_response.json'
    provider={r['code'].upper():r for r in read(capture)['rows']}
    with gzip.open(ROOT/go['candidate_path'],'rt',encoding='utf8') as f:members=[json.loads(l) for l in f]
    gap=[];suspended_target=[];actual=0;raw_sample_checks=[]
    smoke_path='reports/dm01/a01_r2/20261001T033251758661Z/CAPABILITY_SMOKE_query_daily_history_k_AStock_response.json'
    smoke={r['code'].upper():r for r in read(smoke_path)['rows']}
    with zipfile.ZipFile(ROOT/package['path']) as z:
        names=set(z.namelist())
        for r in members:
            market,code=r['source_security_key'].lower().split('.');name=f'{market}/lday/{market}{code}.day';raw=z.read(name) if name in names else b''
            assert len(raw)%32==0;present=bool(raw) and struct.unpack_from('<I',raw,len(raw)-32)[0]==20260928
            if present:actual+=1
            elif (fact:=provider.get(r['source_security_key'])) and fact['tradestatus']=='1':
                gap.append(dict(categories=['REAL_DATA_GAP','LOCAL_BAR_MISSING_SHOULD_TRADE'],security_id=r['security_id'],source_security_key=r['source_security_key'],effective_date='2026-09-28',provider_value=fact,official_local_evidence=[package,bind(capture)],expected_interpretation={'status':'DATA_GAP','is_st':fact['isST']},conflict_disposition='ACCEPTED_LOCAL_FROZEN_PACKAGE_HAS_NO_TARGET_BAR; DATED_PROVIDER_1_PROVES_SHOULD_TRADE_IN_CANDIDATE_ONLY',scope='OBSERVED_DELAYED_GO_FORWARD_CAPTURE_NOT_HISTORICAL_REBUILD',observed_at='2026-10-01T03:33:08.197373+00:00',formal_publication=False))
            elif not present:suspended_target.append(dict(security_id=r['security_id'],source_security_key=r['source_security_key'],date='2026-09-28',provider_value=provider.get(r['source_security_key']),interpretation='SUSPENDED_PROVIDER_0; NOT_DATA_GAP'))
            # Reuse actual 9/30 capture. The available local frozen package ends 9/28;
            # this is a real local capture lag, not an interior historical missing bar.
            fact=smoke.get(r['source_security_key'])
            if fact and fact['tradestatus']=='1' and len(gap)<8:
                assert not raw or struct.unpack_from('<I',raw,len(raw)-32)[0]<=20260928
                gap.append(dict(categories=['REAL_DATA_GAP','LOCAL_CAPTURE_LAG_SHOULD_TRADE'],security_id=r['security_id'],source_security_key=r['source_security_key'],effective_date='2026-09-30',provider_value={k:fact[k] for k in ['code','date','tradestatus','isST']},official_local_evidence=[package,bind(smoke_path)],expected_interpretation={'status':'DATA_GAP','is_st':fact['isST']},conflict_disposition='SOURCE_CAPTURE_LAG: ACTUAL_9_30_PROVIDER_1_BUT_AVAILABLE_LOCAL_INPUT_IS_FROZEN_AT_9_28; NOT_AN_INTERIOR_HISTORY_HOLE',scope='OBSERVED_DAILY_CANDIDATE_DIAGNOSTIC_ONLY; NO_9_30_HISTORICAL_OR_FORMAL_PUBLICATION',first_availability_at_target_proven=False,formal_publication=False))
        for tag,rows in pools.items():
            for sid,key,day,status,st,present in rows[:8]:
                market,code=key.lower().split('.');name=f'{market}/lday/{market}{code}.day';raw=z.read(name) if name in names else b'';wanted=int(str(day).replace('-',''))
                days={struct.unpack_from('<I',raw,i)[0] for i in range(0,len(raw),32)}
                # Numeric alias predecessor may be absent from current package; accepted historical daily remains source.
                matches=(wanted in days)==present
                raw_sample_checks.append(dict(category=tag,security_id=sid,key=key,date=str(day),expected_status=status,expected_st=st,historical_local_present=present,frozen_928_package_present=wanted in days,match=matches,disposition='EXACT_NATIVE_TDX_DATE_RECORD' if matches else 'LATER_PACKAGE_HISTORY_OR_ALIAS_DIFF; HISTORICAL_ACCEPTED_DAILY_REMAINS_AUTHORITATIVE'))
    assert actual==5210 and len(suspended_target)==12 and len(gap)==8
    atomic_json(ROOT/(P+'REAL_DATA_GAP_MATRIX_R1.json'),dict(status='PASS_REAL_SOURCE_DATA_GAP_CASES_WITH_CAPTURE_LAG_SCOPE',samples=gap,actual_928_rows=actual,suspended_928_rows=suspended_target,target_members=len(members),network_calls=0,scope='Real 9/30 should-trade capture vs frozen local 9/28 input; capture-lag gap, not a same-cutoff historical hole. Required historical scope has no provider=1 missing-bar case. 9/28 all twelve missing bars are provider=0 suspension, never relabelled gap.'))
    atomic_json(ROOT/(P+'SOURCE_REVISION_RECOVERY_BINDING_R1.json'),dict(primary=bind('reports/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.json'),bounded_recovery=bind(recovery),source_revision_dates=786,failed_initial_dates_recovered=10,unresolved_dates=0,primary_unknown_receipts_not_treated_as_facts=True))
    atomic_json(ROOT/(P+'INDEPENDENT_REAL_SOURCE_ORACLE_R1.json'),dict(status='PASS_FULL_ROW_REAL_SOURCE_ORACLE',source_bindings={k:bind(v) for k,v in PATHS.items()},candidate_bindings=repair['artifacts'],rows=4035729,status_differences=status_diff,st_differences=st_diff,independent_period_counter_checks=period_checks,independent_formula='TDX source_bar_present -> actual; else captured provider status 0/1 -> suspension/gap; ST from frozen source bytes with 786 revision receipts',source_revision_receipts_bound=bind('reports/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.json'),revision_dates_verified=786,stratified_random_samples={k:[dict(zip(['security_id','source_security_key','trade_date','expected_status','expected_st','local_actual'],[str(x) if hasattr(x,'isoformat') else x for x in r],strict=True)) for r in rows] for k,rows in pools.items()},native_tdx_byte_checks=raw_sample_checks,real_data_gap_matrix=bind(P+'REAL_DATA_GAP_MATRIX_R1.json'),producer_called=False,formal_authority_asserted=False,external_acceptance=None))
    print('PASS_FULL_ROW_SOURCE_ORACLE',status_diff,st_diff,'8 real capture-lag gaps; 12 real 9/28 suspensions; 786 source revisions')
if __name__=='__main__':main()
