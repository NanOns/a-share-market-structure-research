"""Rebind period gap-quality counts; independently prove all arithmetic columns equal."""
from pathlib import Path
import duckdb,json,sys,os
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind

def main():
    c=duckdb.connect();report=[]
    repair=json.loads((ROOT/'reports/audits/A12_V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1.json').read_text(encoding='utf8'))
    assert set(repair['transitions']['status'])=={'ACTUAL_TRADED -> ACTUAL_TRADED','SUSPENDED -> UNKNOWN'}
    for name in ['V4_02_FORMAL_WEEKLY_RAW_QFQ_R7_20260927.parquet','V4_02_FORMAL_MONTHLY_RAW_QFQ_R7_20260927.parquet']:
        p='data/v4/artifact_store/v4_02/'+name;new='data/v4/artifact_store/a12_authority_candidate_r1/'+name.replace('R7_20260927','AUTHORITY_R1')
        c.read_parquet(str(ROOT/p)).create_view('old_period',replace=True)
        c.execute("create or replace temp view new_period as select * replace (0::USMALLINT as suspended_count, (unknown_count+suspended_count)::USMALLINT as unknown_count, case when suspended_count>0 and period_status not in ('BLOCKED_BY_ADJUSTMENT','NO_ACTUAL_BARS','BLOCKED_BY_DATA_GAP') then 'BLOCKED_BY_UNKNOWN_STATUS' else period_status end as period_status) from old_period")
        fields=['canonical_security_id','source_security_key','period_type','period_start_date','period_end_date','period_last_session','asof_trade_date','open','high','low','close','volume','amount','price_basis','period_view','calendar_count','actual_count','source_daily_digest','adjusted_quality']
        cols=','.join(fields)
        assert c.execute('select count(*) from ((select '+cols+' from old_period except all select '+cols+' from new_period) union all (select '+cols+' from new_period except all select '+cols+' from old_period))').fetchone()[0]==0
        changes=c.execute('select o.period_status,n.period_status,count(*) from old_period o join new_period n using (canonical_security_id,source_security_key,period_type,period_start_date,period_end_date,price_basis,asof_trade_date) where o.suspended_count<>n.suspended_count group by all').fetchall()
        dest=ROOT/(new+'.tmp');c.sql('select * from new_period').write_parquet(str(dest),compression='zstd');os.replace(dest,ROOT/new)
        report.append(dict(old=bind(p),candidate=bind(new),unchanged_arithmetic_fields=fields,arithmetic_rows_changed=0,status_count_transitions=changes,source_boundary='ALL_OLD_SUSPENDED_DAYS_NOW_UNKNOWN_PER_A12; UNKNOWN_COUNT_GROWS_BY_OLD_SUSPENDED_COUNT',original_quality_precedence='DATA_GAP > UNKNOWN > INVALID_ACTUAL; QFQ_ADJUSTMENT_OVERRIDE_PRESERVED'))
    atomic_json(ROOT/'reports/audits/A12_FORMAL_PERIOD_AUTHORITY_REBIND_R1.json',dict(status='PASS_BOUNDARY_ONLY_PERIOD_QUALITY_REPLAY',reports=report,formal_publication=False,external_acceptance=None))
    print('PASS_PERIOD_ARITHMETIC_UNCHANGED')

if __name__=='__main__':main()
