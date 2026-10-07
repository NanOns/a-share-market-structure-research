"""Close the independently audited V4 selector omission, preserving prior runs."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from scripts.full_chain_repair_io import ROOT, binding, capture, write

P='reports/v4_only_scope_omission_repair_20261007/'
OLD='reports/forward_r2_final_blocker_repair_20261007/'
DOC='V4_ONLY_FULL_REGRESSION_INDEPENDENT_EXTERNAL_AUDIT_R1_20261007.md'


def entry():
    if (ROOT/(P+'ENTRY_BASELINE.json')).exists():
        raise ValueError('STAGE_BASELINE_EXISTS_USE_A_NEW_VERSION')
    write('docs/evidence/v4_only_scope_omission_repair_20261007/'+DOC,
          (Path('D:/Users/lps/Desktop/阶段任务')/DOC).read_bytes(),raw=True)
    for folder in (P,'docs/evidence/v4_only_scope_omission_repair_20261007/'):
        write(folder+'.gitattributes',b'* -text whitespace=-blank-at-eol,-blank-at-eof,-space-before-tab\n',raw=True)
    write(P+'ENTRY_BASELINE.json',capture())
    from scripts import forward_final_v4_scope as scope
    scope.P=P
    files=scope.build()
    prior=json.loads((ROOT/(OLD+'V4_ONLY_EXECUTION_SCOPE.json')).read_bytes())
    assert all(binding(row['path'])==row for row in prior['bindings'])
    added=sorted(set(files)-set(prior['files']))
    assert added==['tests/test_r17a_historical_governance.py','tests/v4_joint/test_execution_scope_coverage.py']
    assert not set(prior['files'])-set(files)
    write(P+'SCOPE_DIFF.json',dict(before_files=len(prior['files']),after_files=len(files),
        added_files=added,removed_files=[],previous_212_test_file_bindings_unchanged=True,
        previous_scope=binding(OLD+'V4_ONLY_EXECUTION_SCOPE.json'),
        current_scope=binding(P+'V4_ONLY_EXECUTION_SCOPE.json')))
    write(P+'STAGE_EXECUTION_LEDGER.json',dict(stage='V4_ONLY_SCOPE_OMISSION_REPAIR_R1',
        contract=binding('docs/evidence/v4_only_scope_omission_repair_20261007/'+DOC),
        execution='Previously accepted 4759-node V4 profile retained unchanged; actual execution of both added files',
        acceptance='PENDING',next_stage='NEW_NODE_EXECUTION_AND_COMPLETE_COLLECTION_RECONCILIATION',
        pre_v4_execution=False,runtime_authorized=False))


def fingerprint(label):
    from scripts import forward_final_bootstrap as tdx
    from scripts.forward_p1_fingerprint import capture as runtime_capture
    tdx.P=P
    tdx.fingerprint(label)
    write(P+'PROTECTED_'+label+'_FINGERPRINT.json',runtime_capture())


def seal():
    for name in ('v4_scope_omission_tests.xml','v4_scope_omission_tests.log','v4_scope_full_collection.log'):
        write(P+'execution/'+name,(Path('G:/codex_tmp')/name).read_bytes(),raw=True)
    xml=ET.fromstring((ROOT/(P+'execution/v4_scope_omission_tests.xml')).read_bytes())
    delta=xml.findall('.//testcase')
    assert delta and all(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in delta)
    old_xml=ET.fromstring((ROOT/(OLD+'execution/current_full.xml')).read_bytes())
    prior=old_xml.findall('.//testcase')
    old_receipt=json.loads((ROOT/(OLD+'GLOBAL_CURRENT_REGRESSION_RECEIPT.json')).read_bytes())
    assert binding(OLD+'execution/current_full.xml')==old_receipt['xml']
    assert len(prior)==4759 and all(c.find('failure') is None and c.find('error') is None for c in prior)
    scope=json.loads((ROOT/(P+'V4_ONLY_EXECUTION_SCOPE.json')).read_bytes())
    assert all(binding(row['path'])==row for row in scope['bindings'])
    key=lambda c:c.attrib.get('classname','')+'::'+c.attrib['name']
    assert not set(map(key,prior))&set(map(key,delta))
    merged=prior+delta
    suite=ET.Element('testsuite',dict(name='V4_COMPLETE_ACCEPTED_PROFILE_PLUS_SCOPE_OMISSION_EXECUTION',
        tests=str(len(merged)),failures='0',errors='0',skipped='2'))
    for case in merged:suite.append(case)
    write(P+'execution/complete_profile.xml',ET.tostring(suite,encoding='utf-8',xml_declaration=True),raw=True)
    collected=(ROOT/(P+'execution/v4_scope_full_collection.log')).read_text(encoding='utf8')
    # The collection ledger contains every node, not only a numerical total.
    expected={key(c).replace('tests.', 'tests/', 1).split('::',1)[0].replace('.', '/')+'.py::'+c.attrib['name'] for c in merged}
    actual={line.strip() for line in collected.splitlines() if line.startswith('tests/') and '::' in line}
    assert len(actual)==len(merged) and actual==expected, 'COMPLETE_COLLECTION_NODE_SET_MUST_EQUAL_EXECUTED_NODE_SET'
    pre=json.loads((ROOT/(P+'TDX_PRE_FINGERPRINT.json')).read_bytes())
    post=json.loads((ROOT/(P+'TDX_POST_FINGERPRINT.json')).read_bytes())
    assert pre==post
    assert (ROOT/(P+'PROTECTED_PRE_FINGERPRINT.json')).read_bytes()==(ROOT/(P+'PROTECTED_POST_FINGERPRINT.json')).read_bytes()
    baseline=json.loads((ROOT/(P+'ENTRY_BASELINE.json')).read_bytes())
    assert baseline['protected']==capture()['protected']
    guard_runs=[]
    for run in ('v4_scope_omission_tests','v4_scope_full_collection'):
        for path in (Path('G:/codex_tmp/test_temp')/(run+'_source_guard')).glob('*.json'):
            value=json.loads(path.read_bytes());guard_runs.append(value)
            write(P+'execution/source_guard/'+run+'/'+path.name,path.read_bytes(),raw=True)
    assert guard_runs and all(v.get('guard_installed') and v.get('source_mutations_executed')==0 for v in guard_runs)
    result=dict(total=len(merged),passed=sum(c.find('skipped') is None for c in merged),failed=0,errors=0,
        skipped=sum(c.find('skipped') is not None for c in merged),additional_actual_passed=len(delta),
        prior_accepted_nodes=len(prior),selected_files=214,ignored=[],deselected=[],new_xfail=[],
        method='INDEPENDENTLY_ACCEPTED_PROFILE_PLUS_REAL_SCOPE_OMISSION_EXECUTION; COMPLETE_NODE_SET_RECONCILED',
        prior_receipt=binding(OLD+'GLOBAL_CURRENT_REGRESSION_RECEIPT.json'),
        added_tests=binding(P+'execution/v4_scope_omission_tests.xml'),
        complete_collection=binding(P+'execution/v4_scope_full_collection.log'),
        complete_profile=binding(P+'execution/complete_profile.xml'),
        single_new_full_rerun=False)
    write(P+'GLOBAL_CURRENT_REGRESSION_RECEIPT.json',result)
    write(P+'PROTECTED_STATE_READBACK.json',dict(TDX_pre_post_equal=True,source_mutations_executed=0,
        guarded_python_processes=len(guard_runs),protected_runtime_bytes_mtime_equal=True,
        accepted_heads_and_migrations_equal=True,tdx_pre=binding(P+'TDX_PRE_FINGERPRINT.json'),
        tdx_post=binding(P+'TDX_POST_FINGERPRINT.json'),
        historical_incident_write_calls=5,historical_incident_files=4,historical_incident_zero_write=False))
    status=dict(status='CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',
        resolved_issue='ONE_SCOPE_OMISSION_CASE_SENSITIVE_SELECTOR',scope='V4_ONLY',
        global_receipt=binding(P+'GLOBAL_CURRENT_REGRESSION_RECEIPT.json'),
        external_acceptance=False,runtime_authorized=False,production=False,shadow=False,
        focus=False,default_ui=False,real_samples_added=False,
        IA07='NOT_VERIFIABLE_BY_CURRENT_ACCEPTED_CAPABILITY',
        prior_IA07=binding(OLD+'IA07_ACCEPTED_CAPABILITY_SCOPE.json'))
    write(P+'CANDIDATE_SEAL.json',status)
    write(P+'SCOPE_AUDIT_ITEM.json',dict(audit_id='V4_ONLY_SCOPE_OMISSION_R1',
        scope=['scripts/forward_final_v4_scope.py','tests/test_r17a_historical_governance.py'],
        finding='Case-sensitive V4 contract detection omitted the current R17A governance tests',
        acceptance='CLOSED_ENGINEERING_PENDING_INDEPENDENT_EXTERNAL_REAUDIT',
        scope_diff=binding(P+'SCOPE_DIFF.json'),execution=binding(P+'GLOBAL_CURRENT_REGRESSION_RECEIPT.json'),
        runtime_authorized=False))
    write(P+'STAGE_EXECUTION_LEDGER.json',dict(stage='V4_ONLY_SCOPE_OMISSION_REPAIR_R1',
        contract=binding('docs/evidence/v4_only_scope_omission_repair_20261007/'+DOC),
        acceptance=status['status'],evidence=[binding(P+'GLOBAL_CURRENT_REGRESSION_RECEIPT.json'),
            binding(P+'PROTECTED_STATE_READBACK.json')],next_stage='INDEPENDENT_V4_SCOPE_REAUDIT',pre_v4_execution=False))
    report=f'''# V4-only 外审范围遗漏修复 R1

外审基线 d68adc4a。修复 root test selector 的大小写敏感判断，将源码中的 V4_ 合同同样识别为 V4。旧 212 个测试文件绑定全部不变，新增遗漏的 test_r17a_historical_governance.py 和一项实际仓库范围防复发测试，当前 214 个文件。

新增文件实际执行 {len(delta)} 个节点，全部通过。全范围重新 collection 的逐节点集合与此前外审认可的 4759 节点及本次新增执行的并集完全一致。归并验收：{result['total']} total，{result['passed']} passed，0 failed，0 errors，2 platform symlink skipped（原 V4 portable equivalents 已通过）。没有 ignore/deselect/xfail。未再重跑 41 分钟的原已验收 profile；不是一次新全量零错误声明。原始 XML、collection ledger 与依赖绑定完整保留。

本次补跑前后全部 TDX 指纹相同，保护的运行目录 bytes/mtime、已接受头、SQL migration 均不变。旧事故 5 次写入、4 文件、zero-write=false 永久保留。IA-07 能力债务保持，不授权运行、shadow、production、focus、default UI，不增加真实样本，不运行 pre-V4 测试。

候选结论：CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT。新外部验收尚未取得，commit/push 不代表进入后续门禁阶段。
'''
    write(P+'COMPLETION_REPORT.md',report.encode(),raw=True)
    write('docs/audits/V4_ONLY_SCOPE_OMISSION_REPAIR_R1_20261007.md',report.encode(),raw=True)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    import sys
    {'ENTRY':entry,'PRE':lambda:fingerprint('PRE'),'POST':lambda:fingerprint('POST'),'SEAL':seal}[sys.argv[1]]()
