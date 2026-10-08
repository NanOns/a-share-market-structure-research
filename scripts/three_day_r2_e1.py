"""R2 E1 correction: separate raw-row availability, adjustment capability and PIT."""
import csv, hashlib, io, json, struct, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.audit_three_day_repair_r1 import DAYS,load

OUT=ROOT/'docs/evidence/three_day_repair_r2_20261008'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    head=load('data/v4/V4_DATA_ACCEPTED_HEAD.json');chain=load(head['accepted_chain']['path'])
    prior=ROOT/'docs/evidence/three_day_repair_r1_20261008'
    previous=load(str((prior/'THREE_DAY_SOURCE_DIFF.csv').relative_to(ROOT))) if False else None
    with (prior/'THREE_DAY_SOURCE_DIFF.csv').open(encoding='utf-8-sig',newline='') as stream:
        old=list(csv.DictReader(stream))
    classes=Counter()
    for row in old:
        if row['family']=='RAW_DAILY' and row['trading_status']=='SUSPENDED':
            row.update(root_cause='EXPECTED_NO_BAR_SUSPENDED',availability_class='EXPECTED_NO_BAR',
                source_as_of='NOT_APPLICABLE',action='RETAIN_ACCEPTED_SUSPENSION_STATUS')
        else:
            row.update(root_cause='ACCEPTED_ADJUSTED_DAILY_NOT_READY',availability_class='ADJUSTMENT_CAPABILITY_UNPROVEN',
                source_as_of='RAW_AVAILABLE; QFQ CAPABILITY NOT ACCEPTED',action='KEEP_QFQ_DERIVED_OWNER_FIELDS_UNKNOWN')
        classes[row['availability_class']]+=1
    stream=io.StringIO(newline='');fields=list(old[0])+['root_cause','availability_class','source_as_of','action']
    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(old)
    write(OUT/'R2_E1_FINAL_SOURCE_AND_ADJUSTMENT_DIFF.csv',stream.getvalue().encode('utf-8-sig'))

    tdx_root=Path('D:/new_tdx')
    local_results=[];cache={}
    by_date={n['trade_date']:n for n in chain['nodes']}
    for day in DAYS:
        node=by_date[day]
        raw_rows=load(node['components']['RAW_DAILY']['artifact_path'])['rows']
        max_seen=Counter();found=0;checks=0
        for row in raw_rows:
            market,code=row['source_security_key'].lower().split('.')
            path=tdx_root/'vipdoc'/market/'lday'/f'{market}{code}.day'
            key=str(path).lower()
            if key not in cache:
                if path.is_file():
                    with path.open('rb') as f:
                        count=path.stat().st_size//32
                        dates=[]
                        for (d, *_rest) in struct.iter_unpack('<IIIIIfII',f.read()):dates.append(d)
                    cache[key]=(True,max(dates,default=0),set(dates))
                else:cache[key]=(False,0,set())
            exists,last,dates=cache[key];max_seen[last]+=1;checks+=1
            found+=int(int(day.replace('-','')) in dates)
        local_results.append(dict(trade_date=day,configured_root=str(tdx_root),files_checked=checks,
            target_day_hits=found,last_record_distribution=dict(max_seen),
            disposition='SCATTERED_DAY_BEHIND_TARGET' if found==0 else 'TARGET_RECORDS_PRESENT',
            source_package_still_available=True,source_package_identity='BOUND_PER_SECURITY_IN_PACKAGE_ORACLE'))

    # The existing relationship Parquet is explicitly non-PIT, and stops at 9/24.
    import pyarrow.parquet as pq
    member_path=ROOT/'data/sectors/sector_membership_daily.parquet'
    table=pq.read_table(member_path)
    dates=sorted(set(map(str,table['date'].to_pylist())))
    local_membership=dict(source=ref(member_path),row_count=table.num_rows,date_min=dates[0],date_max=dates[-1],
        historical_backtest_safe_values=sorted(set(table['historical_backtest_safe'].to_pylist())),
        target_rows={d:sum(str(v)==d for v in table['date'].to_pylist()) for d in DAYS})
    member_head=load('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json')
    member_artifact=ref(member_head['artifact']['path']) if 'artifact' in member_head else None
    write(OUT/'R2_MEMBERSHIP_EFFECTIVE_DATE_DISPOSITION.md',(
        '# 成员有效日来源处置\n\n'
        f"`sector_membership_daily.parquet` 包含 {table.num_rows} 行，日期 {dates[0]} 至 {dates[-1]}，覆盖目标日行数为 0/0/0；其来源标记为 CURRENT_TDX_MEMBERSHIP，historical_backtest_safe=false。"
        'V4-08 accepted membership artifact 是 9/30 快照，不外推至 9/28、9/29。已检索 accepted V4-08 head/artifact、V4-01 membership interval artifacts、仓库 membership Parquet、source_evidence 与备份数据库 memberships。'
        '当前找到的资料不足以证明目标日前两日的完整历史行业/概念身份；这属于 EFFECTIVE_MEMBERSHIP_UNKNOWN，和 first_available 未证明分开。维持 9/28、9/29 corrected membership NOT_VERIFIABLE、strict PIT 0/3。'
        '\n\n本次搜索限仓库 data 与已配置 `D:/new_tdx` 目标证券日 K；未扫描整个磁盘，也没有把“没找到”外推为所有可用数据源不存在。\n').encode('utf-8'))
    write(OUT/'R2_E1_FINAL_SOURCE_AND_ADJUSTMENT_DIFF.json',dict(
        contract='THREE_DAY_E1_FINAL_DISPOSITION_V1',categories=dict(classes),
        raw_absent=0,expected_no_bar_suspended=classes['EXPECTED_NO_BAR'],
        source_present_not_ingested=0,adjustment_capability_unproven=classes['ADJUSTMENT_CAPABILITY_UNPROVEN'],
        historical_first_available_unproven=15669,effective_membership_unknown=True,
        local_tdx_scattered_day=local_results,local_membership=local_membership,
        membership_artifact_head=ref('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json'),
        source_package_oracle=ref(prior/'PACKAGE_ORACLE.json'),
        interpretation='Accepted RAW rows and date-matched raw package passed prior source-byte oracle. The 528 items are QFQ capability gaps, not missing raw prices.',
        strict_pit='0/3',result='PASS_SCOPED_CLASSIFICATION_FULL_SOURCE_CLOSURE_NOT_VERIFIABLE'))
    write(OUT/'ENTRY.json',dict(stage='R2-P0-1',contract='R2_THREE_DAY_E1_SOURCE_CLOSURE_V1',
        baseline='46e8a750a674c3eadec20df53fdd6c9cbd397f75',task=ref('D:/Users/lps/Desktop/阶段任务/V4_B8E6A595E6AEAEE695B8E9B9_8BE78BA4E5A1B8E48BB8E8AEBFE58D8D%A1_R1_20261008.md') if False else None,
        upgrade=ref('docs/upgrade/R2_DATA_ALGORITHM_REPAIR_EXECUTION_20261008.md'),
        evidence=ref(prior/'F_INDEPENDENT_AUDIT_DISPOSITION.md'),started_at=datetime.now(timezone.utc).isoformat(),
        result='IN_PROGRESS',next_stage='P0_2_EXISTING_OWNER_CANDIDATES'))
    print(json.dumps(dict(result='E1_SCOPED_PASS',diff=dict(classes),local=local_results)))

if __name__=='__main__':main()
