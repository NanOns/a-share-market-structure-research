"""Independent real target source checks; stop before an unaccepted final all-nine owner."""
import gzip,hashlib,json,struct,sys,zipfile
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.dm01_source_boundary_r2 import source_freeze_complete_v2,require_external_a12_owner_for_final_candidate

def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def sha(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def verified(ref):
    assert bind(ref['path'])['sha256']==ref['sha256'];return read(ref['path'])

def main():
    authority='docs/evidence/source_authority/DM01_A01_R2_BAOSTOCK_CATCHUP_SUPPLEMENTAL_GATE_REPAIR_TASK_20261001.md'
    policy=read('config/dm01_source_boundary_r2.json');a12=read('config/v4_02_status_st_authority_r1.json')
    protected=read('config/source_authority_governance_r1.json')['protected_bindings'];assert all(bind(r['path'])['sha256']==r['sha256'] for r in protected)
    entry=dict(status='AUTHORIZED_RUNTIME_CAPTURE_AND_SOURCE_PREFLIGHT_FINAL_OWNER_GATE',authority=bind(authority),precedence=bind('docs/evidence/source_authority/V4_A12_V4_02_STATUS_ST_AUTHORITY_AND_CASCADE_REPAIR_TASK_R1_20261001.md'),a12_producer_freeze=bind('reports/audits/A12_PRODUCER_CONTRACT_FREEZE_R1.json'),owner_contract=bind('config/v4_02_status_st_authority_r1.json'),stage_contract=bind('config/dm01_source_boundary_r2.json'),protected_bindings=protected,next_stage='Independent A12 external owner acceptance before final all-nine runtime integration and real candidate',external_acceptance=None)
    atomic_json(ROOT/'reports/audits/A01_R2_SOURCE_BOUNDARY_STAGE_ENTRY_R1.json',entry)
    summary=read('reports/audits/A01_R2_NORMALIZED_RUNTIME_AND_TARGET_CAPTURE_R2.json');capture=verified(summary['normalized']['TARGET_DATE_CAPTURE']);cap=verified(summary['normalized']['runtime_capability'])
    smoke=verified(cap['smoke_binding'])
    for method,response in smoke['responses'].items():
        value=verified(response['response_binding']);assert sha(value['rows'])==response['response_sha256']
        field='date' if method=='query_daily_history_k_AStock' else 'dividOperateDate'
        assert {r[field] for r in value['rows']}=={'2026-09-30'} and response['response_binding']['path']!=capture['responses'][method]['response_binding']['path']
    assert cap['smoke_date']=='2026-09-30' and capture['target_trade_date']=='2026-09-28'
    assert cap['runtime_capability_id']=='BS-CAP-V2:'+sha({k:v for k,v in cap.items() if k!='runtime_capability_id'})==capture['runtime_capability_id']
    provider={};response_checks={}
    for method,r in capture['responses'].items():
        raw=verified(r['raw_response_binding']);normalized=verified(r['response_binding']);expected=[dict(row) for row in raw['rows']]
        if method=='query_daily_adjust_factor':
            for row in expected:row['adjustFactor']=row.pop('adjustFacto')
            datefield='dividOperateDate'
        else:datefield='date';provider={row['code'].upper():row for row in expected}
        assert normalized['rows']==expected and sha(expected)==r['response_sha256']
        assert len(expected)==r['row_count'] and {row[datefield] for row in expected}=={'2026-09-28'}
        observed=datetime.fromisoformat(r['observed_at']);received=datetime.fromisoformat(r['received_at']);assert observed<=received and observed.date().isoformat()=='2026-10-01'
        assert r['request_count']>0 and r['provider_date']=='2026-09-28'
        response_checks[method]=dict(rows=len(expected),provider_date='2026-09-28',observed_at=r['observed_at'],received_at=r['received_at'],original_bytes_bound=True,normalization_independently_equal=True)
    assert summary['request_count']==6 and capture['origin']=='DELAYED_HISTORICAL_RETRIEVAL' and capture['first_availability_at_target_proven'] is False
    goforward=read('data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json');old=read('config/dm01_incremental_builders_contract_r1.json');refs=goforward['evidence_bindings']
    required=dict(TDX_ACCEPTED_FROZEN_PACKAGE=refs['official_tdx_package'],GBBQ_ACCEPTED_TARGET_ELIGIBLE=refs['gbbq_snapshot'],ACCEPTED_LOCAL_DATED_IDENTITY=old['accepted_identity_bindings'][0],ACCEPTED_CALENDAR=old['accepted_calendar_head'],ACCEPTED_PARENT_DATA_HEAD=bind('data/v4/V4_DATA_ACCEPTED_HEAD.json'),ACCEPTED_SPECIAL_PHASE_CONTRACT=old['accepted_phase_bindings']['policy'])
    supplemental={policy['supplemental_source_families'][0]:summary['normalized']['TARGET_DATE_CAPTURE'],policy['supplemental_source_families'][1]:capture['responses']['query_daily_adjust_factor']['response_binding']}
    present=source_freeze_complete_v2(ROOT,policy,required,supplemental);absent=source_freeze_complete_v2(ROOT,policy,required,{})
    assert present['core_source_gate']==absent['core_source_gate']=='PASS'
    gbbq=verified(refs['gbbq_snapshot']);assert gbbq['first_eligible_formal_trade_date']<='2026-09-28'
    gbbqfiles=[]
    for value in gbbq['files'].values():
        ref={**value,'path':str(Path(refs['gbbq_snapshot']['path']).parent/value['path']).replace('\\','/')};assert bind(ref['path'])['sha256']==value['sha256'];gbbqfiles.append(ref)
    assert bind(goforward['candidate_path'])['sha256']==goforward['candidate_sha256']
    with gzip.open(ROOT/goforward['candidate_path'],'rt',encoding='utf8') as stream:members=[json.loads(line) for line in stream]
    assert len(members)==5222 and len({r['security_id'] for r in members})==5222
    counts=Counter();conflicts=[]
    with zipfile.ZipFile(ROOT/refs['official_tdx_package']['path']) as archive:
        names=set(archive.namelist())
        for row in members:
            key=row['source_security_key'];market,code=key.split('.');name=f'{market.lower()}/lday/{market.lower()}{code}.day'
            data=archive.read(name) if name in names else b'';assert len(data)%32==0
            bar=struct.unpack('<IIIIIfII',data[-32:]) if data else None
            if bar:assert bar[0]<=20260928
            actual=bar is not None and bar[0]==20260928
            counts['target_members']+=1;counts['local_actual' if actual else 'local_bar_missing']+=1
            if actual:
                assert [Decimal(n)/100 for n in bar[1:5]]==[Decimal(n) for n in row['raw_ohlc']]
                p=provider.get(key)
                if p:
                    counts['provider_crosscheck_rows']+=1
                    if Decimal(p['close'])==Decimal(bar[4])/100:counts['close_exact_match']+=1
                    if p['tradestatus']!='1':conflicts.append(dict(security_id=row['security_id'],source_security_key=key,local_actual=True,provider_tradestatus=p['tradestatus'],provider_role='SUPPLEMENTAL_CROSSCHECK'))
    try:require_external_a12_owner_for_final_candidate(ROOT,entry['owner_contract'],read('data/v4/V4_STAGE_ACCEPTED_HEAD.json'))
    except ValueError as error:blocked=str(error)
    else:raise AssertionError('Unexpected owner acceptance; final candidate requires its own authorized execution')
    assert blocked=='A12_EXTERNAL_OWNER_ACCEPTANCE_REQUIRED'
    assert all(bind(r['path'])['sha256']==r['sha256'] for r in protected)
    report=dict(status='PASS_REAL_CAPTURE_AND_REQUIRED_SOURCE_PREFLIGHT_FINAL_ALL_NINE_BLOCKED',response_checks=response_checks,request_count=6,runtime_capability=summary['normalized']['runtime_capability'],capture=summary['normalized']['TARGET_DATE_CAPTURE'],required_source_bindings=required,gbbq_files=gbbqfiles,source_gate_with_provider=present,source_gate_without_provider=absent,tdx_independent_raw_checks=dict(counts),provider_conflicts=conflicts,canonical_qfq_authority='GBBQ_ONLY',st_or_suspension_not_inferred_from_provider=True,all_nine_final_execution_performed=False,all_nine_period_price_special_phase_postcheck_performed=False,final_candidate_blocker=blocked,required_next_input='Independent external acceptance of the A12 owner contract, followed by separately authorized owner promotion/binding',accepted_heads_unchanged=True,external_acceptance=None,first_availability_at_target_proven=False,engineering_r1_adapters_preserved=True,observed_at=datetime.now(timezone.utc).isoformat())
    atomic_json(ROOT/'reports/audits/A01_R2_INDEPENDENT_CAPTURE_AND_SOURCE_PREFLIGHT_R1.json',report)
    atomic_json(ROOT/'reports/audits/A01_R2_DEPENDENCY_BLOCKER_R1.json',dict(status='BLOCKED_A12_EXTERNAL_OWNER_ACCEPTANCE',work_package='WP-A01-DM01',completed_independent_scope=['Runtime capability/date decoupling','Actual bounded 9/28 delayed catch-up','Exact SDK hash schema adapter','Required versus supplemental preflight','Independent real TDX/BaoStock capture checks'],pending_required_scope=['Final R2 runtime integration around accepted A12 producers','Real all-nine target candidate','Independent all-nine parent/source/calendar and arithmetic postcheck','Real candidate idempotency and delayed-revision checks'],engineering_evidence=bind('reports/audits/A01_R2_INDEPENDENT_CAPTURE_AND_SOURCE_PREFLIGHT_R1.json'),a12_source_contract=entry['owner_contract'],external_acceptance=None,data_head_promoted=False,unique_completion_status_not_claimed='DM01_A01_R2_REAL_TARGET_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',next_stage=entry['next_stage']))
    print(json.dumps(dict(status=report['status'],counts=dict(counts),blocker=blocked)))

if __name__=='__main__':main()
