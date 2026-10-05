"""E2 evidence and final regression; no production or TDX writes."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from workbench_analysis.fep_e1.contracts import atomic_json,digest
from workbench_analysis.fep_e1.datasets import assemble
from workbench_analysis.fep_e2.input import bind
from workbench_analysis.fep_e2.support import discover, DIMENSIONS
from workbench_analysis.fep_e2.conditional import baseline,LEVELS
from scripts.validate_r25_preflight import protected,selection

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/fep_e2_r1'
BASE='06549c102da2a203a19004fbeb17a0a0cf717b6a'


def now():return datetime.now(timezone.utc).isoformat()


def binding(path):
    raw=(ROOT/path).read_bytes()
    return dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def prepare():
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/'.gitattributes').write_text('* -text\n',encoding='utf-8')
    sources=['V4_FEP_EXECUTION_MASTER_V4_15E2_R1_20261005.md',
             'V4_15E2_CONDITIONAL_STATISTICS_BASELINE_IMPLEMENTATION_TASK_R1_20261005.md',
             'V4_15E1_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md']
    for name in sources:
        raw=(Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes()
        temp=REPORT/(name+'.tmp');temp.write_bytes(raw);temp.replace(REPORT/name)
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    protected_files={p:binding(p) for p in tracked if p and (ROOT/p).is_file()}
    atomic_json(REPORT/'ENTRY_BASELINE.json',dict(stage='V4-15E2',baseline=BASE,entered_at=now(),
               authority=[binding('reports/fep_e2_r1/'+n) for n in sources],contract='CONDITIONAL_EXPECTANCY_V1',
               intended_acceptance='ENGINEERING_ONLY_OR_BLOCKED_IF_POLICY_UNSET',next='STOP_WAIT_EXTERNAL_AUDIT_OR_REPAIR',
               protected_files=protected_files,TDX='READ_ONLY_UNTOUCHED',storage='E_DRIVE'))
    observation=json.loads((ROOT/'reports/fep_e1_r2_final/ENGINEERING_OBSERVATION.json').read_bytes())
    snapshot=json.loads((ROOT/'reports/fep_e1_r2_final/ENGINEERING_SNAPSHOT.json').read_bytes())
    target='ABS_RETURN_N:T1';cutoff=now()
    e1=assemble([observation],[dict(target_id=target,scope_id=observation['scope_id'],horizon=1)],
                [dict(fold_id='E2_ENGINEERING',partition_name='FIT',observation_ids=[observation['observation_id']],
                      fold_dataset_cutoff=cutoff,phase_started_at=cutoff)],{},
                {observation['observation_id']:dict(snapshot_id=snapshot['feature_digest'])},cutoff)
    atomic_json(REPORT/'E1_FROZEN_DATASET.json',e1)
    row=dict(observation_id=observation['observation_id'],entity_id=observation['entity_id'],
             entity_type='STOCK',observation_scope=observation['scope_id'],signal_type='ENTRY',target=target,horizon=1,
             feature_variant='CORE',evidence_origin='RECONSTRUCTED_ASOF',label_quality_policy='E1_VISIBLE_TRAINABLE_ONLY',
             contract_versions={'feature':'FEP_FEATURE_OWNER_V1','target':'FEP_E1_TARGETS_V1'},
             trade_date=observation['trade_date'],date_ordinal=0,label_end_ordinal=1,episode_start=0,episode_end=1,
             regime='MISSING',trend='MISSING',position='MISSING',risk='MISSING',feature_support='NOT_PROJECTED',
             sector='UNAVAILABLE',support_class='UNAVAILABLE')
    dataset=bind(e1,dict(dataset_id='E2_E1_OWNER_ENGINEERING_NO_LABEL_V1',feature_contract_id='FEP_FEATURE_OWNER_V1',
                       target_contract_id='FEP_E1_TARGETS_V1',fold_id='E2_ENGINEERING',partition_name='FIT',
                       target=target,target_kind='CONTINUOUS',classes=[]),{observation['observation_id']:row})
    atomic_json(REPORT/'E1_INPUT_BINDING.json',dict(dataset=dataset,sources=[binding(p) for p in
        ['reports/fep_e1_r2_final/ENGINEERING_OBSERVATION.json','reports/fep_e1_r2_final/ENGINEERING_SNAPSHOT.json',
         'config/fep_feature_owner_contract_v1.json','config/fep_target_registry_v1.json',
         'reports/fep_e1_r2_final/FEP_E1_R2_CANDIDATE_SEAL.json']],
         source_boundary='Accepted single engineering observation; zero admitted mature label bindings. No synthetic labels substituted.'))
    discovery=discover(dataset['denominator'],dataset['rows']);discovery['discovered_at']=now()
    discovery.update(status='INSUFFICIENT_THRESHOLD_EVIDENCE',reason='0 eligible labels; one expected date/entity. No multi-date historical outcome population exact-bound in E1 acceptance.',
                     block_simulation=dict(eligible_intervals=[],non_overlap_blocks=0),
                     class_feasibility='NO_ADMITTED_OUTCOME_CLASSES',threshold_derivation='UNSET; unit-test policies are counterexamples, not admission evidence')
    atomic_json(REPORT/'SUPPORT_POLICY_DISCOVERY.json',discovery)
    freeze=now();parameters=[]
    values={k:'UNSET' for k in (*DIMENSIONS,'class_min','max_missing_fraction','max_total_variation')}
    for key,value in values.items():
        parameters.append(dict(parameter_id=key,value=value,unit='fraction' if key.startswith('max_') else 'count',
            allowed_range=[0,1] if key.startswith('max_') else [1,None],owner_stage='E2',
            reason=discovery['reason'],evidence=binding('reports/fep_e2_r1/SUPPORT_POLICY_DISCOVERY.json'),
            introduced_at=freeze,supersedes=None,status='UNSET_DIAGNOSTIC_ONLY',
            freeze_before_statistics_at=freeze,freeze_input_digest=discovery['input_digest']))
    policy=dict(policy_id='FEP_E2_SUPPORT_POLICY_V1',values=values,required_classes=['POS','NEG'],parameters=parameters,
                freeze_before_statistics_at=freeze,freeze_input_digest=discovery['input_digest'],status='UNSET_DIAGNOSTIC_ONLY')
    contract=dict(contract_id='CONDITIONAL_EXPECTANCY_V1',version='1.0.0',scope='FEP_STOCK_ENTRY_CORE',
                  levels=[[n,list(k)] for n,k in LEVELS],weighting='BUCKET_EQUAL_DATE_RATIONAL_V1',
                  quantile='INVERSE_EMPIRICAL_CDF_V1',estimand='COMPLETE_CASE_DESCRIPTIVE',
                  artifact_type='CONDITIONAL_STATISTICS_BASELINE',production=False)
    atomic_json(ROOT/'config/fep_conditional_statistics_contract_v1.json',contract)
    atomic_json(ROOT/'config/fep_e2_support_policy_v1.json',policy)
    atomic_json(REPORT/'SUPPORT_POLICY_FREEZE.json',dict(status=policy['status'],policy_digest=digest(policy),
              frozen_at=freeze,discovery_binding=binding('reports/fep_e2_r1/SUPPORT_POLICY_DISCOVERY.json'),
              outcome_statistics_started=False))
    artifact=baseline(dataset,row,policy,contract,now())
    atomic_json(REPORT/'DIAGNOSTIC_BASELINE.json',artifact)


def tests():
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT)+os.pathsep+str(ROOT/'src')
    env['TEMP']=env['TMP']='E:/codex_tmp/test_temp'
    env['WORKBENCH_PG_DSN']=env['FEP_E1_TEST_DSN']='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh'
    targeted=[sys.executable,'-m','pytest','tests/fep_e2','tests/fep','-q',
              '--basetemp=E:/codex_tmp/test_temp/e2-targeted','--junitxml='+str(REPORT/'targeted.xml')]
    execute(targeted,env,'targeted')
    prior=json.loads((ROOT/'reports/fep_e1_r2_final/SCOPED_REGRESSION_SUMMARY.json').read_bytes())
    command=[s for s in prior['command'] if not s.startswith(('--basetemp=','--junitxml='))]
    command[0]=sys.executable
    command+=['tests/fep_e2','--basetemp=E:/codex_tmp/test_temp/e2-scoped','--junitxml='+str(REPORT/'scoped.xml')]
    execute(command,env,'scoped',prior['current_failed_nodes'])


def execute(command,env,name,known=()):
    with (REPORT/(name+'.log.tmp')).open('wb') as stream:
        code=subprocess.call(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    os.replace(REPORT/(name+'.log.tmp'),REPORT/(name+'.log'))
    # Historical database tests write receipts in their original location.
    for filename in ('CAS_CONCURRENCY_fep_e1_fresh.json','CAS_CONCURRENCY_fep_e1_upgrade.json','TRANSACTION_ROLLBACK_GATE.json'):
        path=ROOT/'reports/fep_e1'/filename
        if path.exists():
            raw=path.read_bytes();temp=REPORT/(filename+'.tmp');temp.write_bytes(raw);temp.replace(REPORT/filename)
            raw=subprocess.check_output(['git','show',BASE+':reports/fep_e1/'+filename],cwd=ROOT)
            temp=path.with_name(path.name+'.tmp');temp.write_bytes(raw);temp.replace(path)
    cases=ET.parse(REPORT/(name+'.xml')).findall('.//testcase')
    failed=sorted(c.attrib['classname']+'::'+c.attrib['name'] for c in cases
                  if c.find('failure') is not None or c.find('error') is not None)
    result=dict(command=command,exit_code=code,passed=sum(all(c.find(k) is None for k in ('failure','error','skipped')) for c in cases),
                skipped=sum(c.find('skipped') is not None for c in cases),failed_nodes=failed,
                introduced_active_failures=sorted(set(failed)-set(known)),existing_debt_nodes=list(known),full_final_run=True)
    atomic_json(REPORT/('TARGETED_SUMMARY.json' if name=='targeted' else 'SCOPED_REGRESSION_SUMMARY.json'),result)
    print(name,result['passed'],len(failed),result['introduced_active_failures'],flush=True)


if __name__=='__main__':
    if sys.argv[1:] == ['prepare']:prepare()
    elif sys.argv[1:] == ['tests']:tests()
