"""Independent literal promotion oracle; never imports or invokes the writer."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from scripts.r21_io import ROOT,BASE,TESTED,TAG,AUDIT,STAGE,HEAD
def require(ok,reason):
    if not ok:raise ValueError(reason)
def verify(binding,root):
    p=(root/binding['path']).resolve();require(p.is_relative_to(root.resolve()),'PATH_ESCAPE')
    raw=p.read_bytes();require(hashlib.sha256(raw).hexdigest()==binding['sha256'] and len(raw)==binding.get('bytes',binding.get('byte_count')),'EXACT_BINDING_'+binding['path']);return raw
def read(path,root):return json.loads((root/path).read_bytes())
def blob(path,root):return subprocess.check_output(['git','show',BASE+':'+path],cwd=root)
def validate_boundary(o):
    require(all(o.get(k,False) is False for k in ['production','shadow','focus','V4_16']),'PERMISSION_OVERCLAIM')
    require(o['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED','PIT_OVERCLAIM')
    require(o['CURRENT_REAL_MATURITY_EVIDENCE']=='NONE' and o['PROVED_HORIZONS']==[] and o['UNPROVED_HORIZONS']==[1,3,5,10,20],'MATURITY_OVERCLAIM')
    require(o['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME']=='NOT_GRANTED_PENDING_MATURITY_EVIDENCE' and o['REALTIME_ACCEPTED_COHORT_MATURITY']=='NOT_GRANTED','REAL_SCOPE_OVERCLAIM')
    require(o['V4_15_FWD_ADJ_VECTOR_01']=='OPEN_NONBLOCKING_TEST_ENHANCEMENT','TEST_ENHANCEMENT_CARRY_FORWARD')
def validate(root=ROOT,head=None,stage=None):
    root=Path(root);h=read(HEAD,root) if head is None else head;s=read(STAGE,root) if stage is None else stage
    parent=read('reports/r21/PARENT_STAGE_HEAD.json',root)
    require((root/'reports/r21/PARENT_STAGE_HEAD.json').read_bytes()==blob(STAGE,root),'PARENT_STAGE_EXACT')
    require((root/'reports/r21/PARENT_CURRENT_STAGE_AUTHORITY.json').read_bytes()==blob('config/v4_current_stage_authority_v1.json',root),'PARENT_AUTHORITY_EXACT')
    require(s['accepted_stage_range']=='V4_00_TO_V4_15_ACCEPTED','STAGE_15_EXACT')
    for k,v in parent.items():
        if k not in ['accepted_stage_range','v4_15_entry']:require(s[k]==v,'PRIOR_STAGE_KEEP_'+k)
    require(s['v4_15_entry']=='COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_RUNTIME','ENTRY_STATUS')
    require(json.loads(verify(s['v4_15_binding'],root))==h and s['v4_15_binding']['path']==HEAD,'HEAD_BINDING')
    e=json.loads(verify(h['entry_contract'],root));require(e['bindings']==h['bindings'] and e['capabilities']==h['capabilities'],'ENTRY_HEAD_MATCH')
    require(h['contract_id']=='V4_15_ACCEPTED_HEAD_V1' and h['stage']=='V4-15' and h['status']=='RUNTIME_ENGINEERING_PASS_CAPABILITY_SCOPED' and h['external_acceptance']=='EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED','HEAD_SEMANTICS')
    require(h['external_audit_decision']==s['v4_15_external_acceptance']=='PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED','EXTERNAL_ACCEPTANCE')
    required={'predecessor_v4_14':'data/v4/V4_14_ACCEPTED_HEAD.json','contract_package':'config/v4_15_contract_package_v1.json','runtime_seal':'reports/r20e/V4_15_RUNTIME_CANDIDATE_R20_SEAL.json','scope_seal':'reports/r20r1/V4_15_R20R1_CANDIDATE_SEAL.json','debt_seal':'reports/r20r1r1/V4_15_R20R1R1_CANDIDATE_SEAL.json','dm01_seal':'reports/r20r1r2/V4_15_R20R1R2_CANDIDATE_SEAL.json','external_audit':AUDIT,'data_head':'data/v4/V4_DATA_ACCEPTED_HEAD.json','maturity_readback':'reports/r20r1r2/MATURITY_DEBT_READBACK.json','forward_projection':'config/v4_15_forward_projection_r20r1r2_v1.json','open_validation_debt':'reports/r20r1/OPEN_VALIDATION_DEBT.json'}
    for k,p in required.items():
        require(h['bindings'][k]['path']==p,'REQUIRED_BINDING_'+k);raw=verify(h['bindings'][k],root)
        if k!='external_audit':require(raw==blob(p,root),'AUDITED_BYTES_KEEP_'+k)
    for k in ['calendar','identity','membership']:verify(h['bindings'][k],root)
    audit=verify(h['bindings']['external_audit'],root).decode('utf8')
    require(h['bindings']['external_audit']['sha256']=='daadcfe74ecb5a23aa9aaca09d0168e72b0e19e1d304a26e35ec5bde49826f71','AUDIT_INDEPENDENT_LITERAL_IDENTITY')
    require(h['bindings']['external_audit']['path']==AUDIT and BASE in audit and TESTED in audit and TAG in audit and 'V4_15_PROMOTION = AUTHORIZED' in audit,'EXACT_EXTERNAL_AUTHORIZATION')
    require(subprocess.check_output(['git','rev-parse',TAG+'^{commit}'],cwd=root).decode().strip()==h['tested_source']==TESTED and h['immutable_tested_tag']==TAG,'TESTED_IMMUTABLE_SOURCE')
    require(subprocess.run(['git','merge-base','--is-ancestor',TESTED,BASE],cwd=root,capture_output=True).returncode==0,'TESTED_ANCESTRY')
    c=read('config/v4_current_stage_authority_v2.json',root)
    require(c['current_head']==s['v4_15_binding'] and c['predecessor_v4_14']==s['v4_14_binding'] and c['V4_15_accepted'] is True,'CURRENT_AUTHORITY_15')
    expected_capabilities={k:'ENGINEERING_ACCEPTED' for k in ['V4_15_RUNTIME_ENGINEERING','RADAR_COHORT_RUNTIME','SETTLEMENT_RUNTIME','PERSISTED_E2E','INDEPENDENT_ORACLE','REAL_DM01_DATA_HEAD_REACHABILITY','REAL_DM01_ROW_SCHEMA_ADMISSION','FORWARD_EVALUATION_PROJECTION','HORIZON_SCOPED_VALIDATION_DEBT']}
    expected_capabilities.update({k:'PASS_CAPABILITY_SCOPED' for k in ['REAL_ACCEPTED_SOURCE_T0_INTEGRATION','REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK']})
    require(h['capabilities']==s['v4_15_capabilities']==expected_capabilities,'EXACT_GRANTED_CAPABILITIES')
    for o in [h,e,c,s['v4_15_capability_boundary']]:
        require(all(o.get(k,False) is False for k in ['production','shadow','focus','V4_16']),'PERMISSION_OVERCLAIM')
        require(o['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED','PIT_OVERCLAIM')
    for o in [h,e,s['v4_15_capability_boundary']]:
        validate_boundary(o)
        require(o['CURRENT_REAL_MATURITY_EVIDENCE']=='NONE' and o['PROVED_HORIZONS']==[] and o['UNPROVED_HORIZONS']==[1,3,5,10,20],'MATURITY_OVERCLAIM')
        require(o['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME']=='NOT_GRANTED_PENDING_MATURITY_EVIDENCE' and o['REALTIME_ACCEPTED_COHORT_MATURITY']=='NOT_GRANTED','REAL_SCOPE_OVERCLAIM')
    debt=json.loads(verify(h['bindings']['maturity_readback'],root));require(debt['proved_horizons']==[] and debt['unproved_horizons']==[1,3,5,10,20] and debt['blocks_unrelated_development'] is False,'NONBLOCKING_DEBT_KEEP')
    require(read(required['data_head'],root)['accepted_trade_date']==h['accepted_trade_date']=='2026-09-30','DATA_DATE_KEEP')
    protected=['reports/r20a','reports/r20b','reports/r20c','reports/r20d','reports/r20e','reports/r20r1','reports/r20r1r1','reports/r20r1r2','reports/v4_15_runtime_r20']
    require(subprocess.check_output(['git','diff',BASE,'--name-only','--',*protected],cwd=root)==b'','PRIOR_ACCEPTED_EVIDENCE_KEEP')
    changed=subprocess.check_output(['git','diff',BASE,'--name-only','--','src'],cwd=root).decode().splitlines()
    require(set(changed)<={'src/workbench_analysis/v4_current_stage_authority.py','src/workbench_analysis/v4_14_authority.py','src/workbench_analysis/v4_15_radar_cohort.py'},'BUSINESS_ALGORITHMS_KEEP')
    from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
    from workbench_analysis.v4_14_authority import ReplayAuthority
    a=CurrentStageAuthority(root);r=ReplayAuthority(root,a)
    require(a.head['stage']=='V4-15' and a.head_ref==c['current_head'] and r.head['stage']=='V4-14' and r.head_ref==s['v4_14_binding'],'CURRENT_REPLAY_SPLIT')
    return dict(R21_V4_15_PROMOTION='PASS_LOCAL',CURRENT_STAGE_AUTHORITY='V4_15',V4_14_REPLAY_PREDECESSOR='PASS',V4_15_ACCEPTED_HEAD='CREATED',V4_STAGE_ACCEPTED_HEAD=s['accepted_stage_range'],V4_DATA_ACCEPTED_HEAD='2026-09-30',CURRENT_REAL_MATURITY_EVIDENCE='NONE',REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME=h['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME'],HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',Production=False,Shadow=False,Focus=False,V4_16=False,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
def rollback_validation(root=ROOT):
    root=Path(root);pairs={'data/v4/V4_STAGE_ACCEPTED_HEAD.json':'reports/r21/PARENT_STAGE_HEAD.json','config/v4_current_stage_authority_v1.json':'reports/r21/PARENT_CURRENT_STAGE_AUTHORITY.json','src/workbench_analysis/v4_current_stage_authority.py':'reports/r21/PARENT_CURRENT_STAGE_AUTHORITY_READER.py','src/workbench_analysis/v4_14_authority.py':'reports/r21/PARENT_REPLAY_AUTHORITY_READER.py'}
    pairs['src/workbench_analysis/v4_15_radar_cohort.py']='reports/r21/PARENT_RADAR_COHORT_AUTHORITY_ADAPTER.py'
    restored=[]
    with tempfile.TemporaryDirectory(prefix='r21-rollback-') as d:
        fixture=Path(d)
        for target,archive in pairs.items():
            raw=(root/archive).read_bytes();require(raw==blob(target,root),'ROLLBACK_ARCHIVE_IDENTITY')
            p=fixture/target;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);require(p.read_bytes()==raw,'ROLLBACK_RESTORATION');restored.append(dict(target=target,archive=archive,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
        stage=read(STAGE,fixture);config=read('config/v4_current_stage_authority_v1.json',fixture)
        require(stage['accepted_stage_range']==config['accepted_stage_range']=='V4_00_TO_V4_14_ACCEPTED' and config['current_head']==stage['v4_14_binding'],'ROLLBACK_COHERENCE')
    return dict(status='PASS_LOCAL',isolated_restoration=True,successful_current_promotion_not_rolled_back=True,restored=restored,recipe='In an isolated checkout restore the five exact archived files; remove only R21-created Head/entry/v2 artifacts before exposing restored Stage. Validate the historical V4-14 reader. Never overwrite Data or historical evidence.')
if __name__=='__main__':
    from scripts.r21_io import atomic
    result=validate();atomic('reports/r21/V4_15_PROMOTION_GATE.json',result)
    atomic('reports/r21/CURRENT_V4_15_AUTHORITY_GATE.json',result);atomic('reports/r21/V4_14_REPLAY_COMPATIBILITY_GATE.json',result)
    atomic('reports/r21/ROLLBACK_VALIDATION.json',rollback_validation());print(json.dumps(result))
