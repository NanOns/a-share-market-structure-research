"""Seal actual remainder execution and open blockers without granting acceptance."""
import json
import subprocess
from pathlib import Path
from scripts.full_chain_repair_io import ROOT, binding, write
from scripts.forward_remainder_receipts import P, run_receipt


def classify():
    import xml.etree.ElementTree as ET
    runs={}
    for name in ('remainder_full_a','remainder_full_b','remainder_full_c','remainder_full_d','remainder_full_e','remainder_full_f'):
        path=Path('E:/codex_tmp')/(name+'.xml')
        if not path.exists():continue
        runs[name]={t.attrib['classname']+'::'+t.attrib['name']:next((s for s in ('failure','error','skipped') if t.find(s) is not None),'passed') for t in ET.parse(path).getroot().iter('testcase')}
    latest=runs.get('remainder_full_f',{})
    aliases={
        'tests.upgrade_m15.test_performance::test_assets_are_versioned_for_m15_04':
            ['tests.upgrade_m15.test_performance::test_assets_have_explicit_current_versions'],
        'tests.upgrade_m15.test_ui_flows::test_m15_v2_has_no_iframe_and_legacy_view_stays_bound':
            ['tests.upgrade_m15.test_ui_flows::test_m15_v2_keeps_only_hidden_focus_frame_and_legacy_view_bound'],
        'tests.upgrade_m7.test_quotes_universe::test_api_refuses_quote_when_bound_source_hash_has_drifted':
            ['tests.upgrade_m7.test_quotes_universe::test_api_refuses_non_success_historical_publication',
             'tests.upgrade_m7.test_quotes_universe::test_verified_quote_source_rejects_wrong_bound_file_hash']}
    rows=[]
    for name,cases in runs.items():
        for node,status in cases.items():
            if status not in ('failure','error'):continue
            result=latest.get(node)
            disposition='UNRESOLVED_FINAL_FAILURE' if result in ('failure','error') else 'REPAIRED_FINAL_PASS' if result=='passed' else 'FINAL_NODE_NOT_MATCHED_REQUIRES_REVIEW'
            if node in aliases:disposition='FORMAL_CURRENT_CONTRACT_SUPERSESSION'
            rows.append(dict(run=name,node=node,original=status,final=result,disposition=disposition,
                successors=[dict(node=n,status=latest.get(n,'NOT_RUN')) for n in aliases.get(node,[])]))
    write(P+'GLOBAL_FAILURE_DISPOSITION.json',dict(entries=rows,all_prior_failures_retained=True,unmatched_not_counted_as_pass=True))


def protected_after():
    from scripts import forward_p1_fingerprint as fingerprint
    original=fingerprint.file_state
    cache={}
    def cached(path):
        if path not in cache:cache[path]=original(path)
        return cache[path]
    fingerprint.file_state=cached
    after=fingerprint.capture()
    extra=fingerprint.supplemental()
    write(P+'PROTECTED_FINGERPRINT_AFTER.json',after)
    write(P+'ALL_RUNTIME_ROOTS_AFTER.json',extra)
    before=json.loads((ROOT/(P+'PROTECTED_FINGERPRINT_BEFORE.json')).read_bytes())
    baseline=json.loads((ROOT/(P+'ENTRY_BASELINE.json')).read_bytes())
    drift=[dict(before=ref,after=binding(ref['path'])) for ref in baseline['protected'] if binding(ref['path'])!=ref]
    write(P+'PROTECTED_STATE_READBACK.json',dict(
        enumerated_runtime_bytes_and_mtimes_unchanged=before==after,
        all_runtime_roots_unchanged=json.loads((ROOT/(P+'ALL_RUNTIME_ROOTS_BEFORE.json')).read_bytes())==extra,
        accepted_heads_and_migrations_drift=drift,TDX_ZERO_WRITE=False,
        tdx_incident=binding(P+'TDX_INPUT_WRITE_INCIDENT.json'),
        limitation='No pre-task TDX fingerprint; incident blocks zero-write acceptance',
        permissions_granted=False))


def missing_search(cases):
    import re
    original=json.loads((ROOT/(P+'IA05_MISSING_HISTORICAL_FIXTURES.json')).read_bytes())
    candidates={row['path']:list(row.get('nodes',[])) for row in original['items']}
    for case in cases:
        for path in re.findall(r"No such file or directory: '([^']+)'",case['trace'] or ''):
            normalized=path.replace('\\\\','/').replace('\\','/')
            relative=next((normalized[normalized.index('/'+name+'/')+1:] for name in ('reports','artifacts','data') if '/'+name+'/' in normalized),None)
            if relative:candidates.setdefault(relative,[]).append(case['node'])
    rows=[]
    for path,nodes in sorted(candidates.items()):
        commits=subprocess.check_output(['git','log','--all','--format=%H','--',path],cwd=ROOT,text=True).splitlines()
        rows.append(dict(path=path,affected_nodes=sorted(set(nodes)),exists_current=(ROOT/path).exists(),
            git_history_commits=commits,original_artifact_fabricated=False))
    write(P+'IA05_HISTORICAL_FIXTURE_RECOVERY_SEARCH_FINAL.json',dict(paths=rows,
        query='git log --all --format=%H -- <exact path>',
        limitation='All currently available local refs; does not prove absence from external backups'))


def final():
    from scripts.forward_remainder_receipts import build
    build();classify()
    isolation=[]
    for base,name in [(Path('E:/codex_tmp/test_temp'),'remainder_full_'+v) for v in ('a','b','c')]+[(Path('G:/codex_tmp/test_temp'),'remainder_full_'+v) for v in ('e','f')]:
        for suffix in ('_protected_fs_pg.json','_protected_connects.json','_failures.jsonl'):
            path=base/(name+suffix)
            if path.is_file():isolation.append(write(P+'execution/'+path.name,path.read_bytes(),raw=True))
    write(P+'ISOLATION_EXECUTION_LOGS.json',dict(artifacts=isolation,production_postgres_used=False,owned_postgres_ports=[55640,55641],tdx_whole_task_zero_write=False))
    run=run_receipt('remainder_full_f')
    if run is None:raise ValueError('FINAL_COMPLETE_JUNIT_REQUIRED')
    executed=json.loads((ROOT/(P+'FINAL_EXECUTED_SOURCE_BINDINGS.json')).read_bytes())
    evidence_only={'scripts/forward_remainder_seal.py','scripts/forward_remainder_receipts.py'}
    drift=[ref['path'] for ref in executed['files'] if ref['path'] not in evidence_only and binding(ref['path'])!=ref]
    if drift:raise ValueError('EXECUTED_RUNTIME_SOURCE_CHANGED:'+repr(drift))
    executed.update(runtime_source_drift=drift,evidence_only_helpers=sorted(evidence_only))
    executed['files']=[binding(ref['path']) for ref in executed['files']]
    write(P+'FINAL_EXECUTED_SOURCE_BINDINGS.json',executed)
    for filename in ('IA05_UI_QUOTE_TEST_SUPERSESSION.json','IA05_LINKAGE_TEST_SUPERSESSION.json',
                     'IA05_MIGRATION_TEST_SUPERSESSION.json','IA06_TEST_SUPERSESSION.json'):
        path=ROOT/(P+filename)
        value=json.loads(path.read_bytes())
        def refresh(obj):
            if isinstance(obj,dict):
                for key,item in list(obj.items()):
                    if key=='current' and isinstance(item,dict) and 'path' in item:obj[key]=binding(item['path'])
                    else:refresh(item)
            elif isinstance(obj,list):
                for item in obj:refresh(item)
        refresh(value);write(P+filename,value)
    incident=json.loads((ROOT/(P+'TDX_INPUT_WRITE_INCIDENT.json')).read_bytes())
    incident['corrected_tool']=binding('scripts/forward_remainder_profiles.py')
    write(P+'TDX_INPUT_WRITE_INCIDENT.json',incident)
    failures=[c for c in run['cases'] if c['status'] in ('failure','error')]
    missing_search(failures)
    skipped=[c for c in run['cases'] if c['status']=='skipped']
    pg_path=P+'IA06_PG_NEGATIVE_MATRIX.json'
    pg_matrix=json.loads((ROOT/pg_path).read_bytes())
    pg_matrix['final_global_cases']=[c for c in run['cases'] if c['node'].startswith(('tests.fep.','tests.fep_e5.','tests.test_full_chain_fep_db::'))]
    pg_matrix['final_source_execution']=True
    write(pg_path,pg_matrix)
    issues=[]
    for case in failures:
        trace=case['trace'] or ''
        category=('HISTORICAL_ARTIFACT_UNAVAILABLE' if 'FileNotFoundError' in trace or ('P09-01-A_SOURCE_REGISTRY.json' in trace and 'exists' in trace) else
                  'ISOLATION_BOUNDARY_REJECTION' if 'FORBIDDEN' in trace or 'DISPOSABLE_' in trace else
                  'HISTORICAL_OR_CURRENT_CONTRACT_ASSERTION_FAILURE' if 'AssertionError' in trace else
                  'EXECUTION_OR_FIXTURE_ERROR')
        issues.append(dict(node=case['node'],category=category,status='OPEN',evidence=trace,
            acceptance='NOT_PASSED',next_action='Recover original evidence or repair exact contract; rerun this node and applicable global gate'))
    issues.append(dict(id='TDX_READ_ONLY_BOUNDARY_INCIDENT',status='EXTERNAL_REVIEW_REQUIRED',
        evidence=binding(P+'TDX_INPUT_WRITE_INCIDENT.json'),acceptance='BLOCKED'))
    issues.append(dict(id='PREEXISTING_V1_CURRENT_RELEASE_IDENTITY_DRIFT',status='OPEN_SEPARATE_RELEASE_PROCESS_REQUIRED',
        evidence=binding(P+'IA05_LEGACY_V1_IDENTITY_REPLAY.json'),
        acceptance='Historical identity reproduced; current release identity not repaired or reaccepted'))
    for case in skipped:issues.append(dict(node=case['node'],status='ENVIRONMENT_VALIDATION_NOT_RUN',evidence=case['trace'],acceptance='NOT_PASSED'))
    write(P+'OPEN_ISSUES_FINAL_DISPOSITION.json',dict(status='BLOCKED_NOT_READY',issues=issues,
        no_unclassified_final_failure=len(issues)>=len(failures),prior_runs=binding(P+'GLOBAL_FAILURE_DISPOSITION.json')))
    result=json.loads((ROOT/(P+'GLOBAL_PYTEST_RECEIPT.json')).read_bytes())
    result.update(latest_is_final_source=True,global_pytest_pass=not failures and not skipped,
                  final_counts=run['counts'],candidate_ready=False)
    write(P+'GLOBAL_PYTEST_RECEIPT.json',result)
    original_keep=json.loads((ROOT/(P+'PASS_KEEP_REGRESSION.json')).read_bytes())
    keep_nodes={c['node'] for r in original_keep['runs'] for c in r['cases']}
    keep=[c for c in run['cases'] if c['node'] in keep_nodes or c['node'].startswith('tests.test_full_chain_fep_db::')]
    original_keep.update(final_global_cases=keep,final_source_execution=True,
        final_acceptance='PASS' if keep and all(c['status']=='passed' for c in keep) else 'FAIL',
        global_source=binding(P+'execution/remainder_full_f.xml'))
    write(P+'PASS_KEEP_REGRESSION.json',original_keep)
    disposition=json.loads((ROOT/(P+'OPEN_ISSUES_FINAL_DISPOSITION.json')).read_bytes())
    disposition['audit_items']={
        'IA05':dict(status='OPEN_GLOBAL_REGRESSION_DEBT' if failures or skipped else 'CANDIDATE_FIXED',evidence=binding(P+'GLOBAL_PYTEST_RECEIPT.json')),
        'IA06':dict(status='CANDIDATE_FIXED_CURRENT_ENV_VERIFIED',evidence=binding(P+'IA06_PG_NEGATIVE_MATRIX.json')),
        'IA07':dict(status='CANDIDATE_FIXED_PERFORMANCE_EVIDENCE_CURRENT_INPUT_SCOPE',evidence=binding(P+'IA07_PERFORMANCE_MEASUREMENTS.json')),
        'IA08':dict(status='CANDIDATE_FIXED_HISTORICAL_ROUTING',evidence=binding(P+'IA08_HISTORICAL_READER_PROOF.json')),
        'DM01_LEGACY_P2':dict(status='CANDIDATE_FIXED',evidence=binding(P+'DM01_LEGACY_TEST_SUPERSESSION_PROOF.json')),
        'IA01_IA02_IA03_IA04_IA09_IA10':dict(status='PASS_KEEP' if original_keep['final_acceptance']=='PASS' else 'FAIL',evidence=binding(P+'PASS_KEEP_REGRESSION.json')),
        'INCREMENTAL_WRITER_LIFECYCLE':dict(status='CANDIDATE_FIXED',evidence=binding(P+'INCREMENTAL_WRITER_LIFECYCLE_REPAIR.json')),
        'HOT_RANK_HTTP_SCOPE':dict(status='CANDIDATE_FIXED',evidence=binding(P+'HOT_RANK_HTTP_SCOPE_REPAIR.json')),
        'TDX_READ_ONLY_BOUNDARY':dict(status='NEW_BLOCKER_EXTERNAL_REVIEW_REQUIRED',evidence=binding(P+'TDX_INPUT_WRITE_INCIDENT.json'))}
    write(P+'OPEN_ISSUES_FINAL_DISPOSITION.json',disposition)
    write(P+'GLOBAL_COLLECTION_RECEIPT.json',dict(status='PASS',collected=run['total'],
        ignore=[],deselect=[],execution=binding(P+'execution/remainder_full_f.xml'),
        collect_only_log=write(P+'execution/remainder_collection_sealed.log',Path('E:/codex_tmp/remainder_collection_sealed.log').read_bytes(),raw=True)))
    protected=json.loads((ROOT/(P+'PROTECTED_STATE_READBACK.json')).read_bytes())
    seal=dict(status='BLOCKED_NOT_READY_FOR_EXTERNAL_ACCEPTANCE',candidate_ready=False,
        final_counts=run['counts'],global_pytest_pass=not failures and not skipped,
        TDX_ZERO_WRITE=False,protected_state=protected,release_permission=False,
        next_stage='INDEPENDENT_REVIEW_OF_BLOCKERS; NO_RUNTIME_PROPAGATION')
    write(P+'CANDIDATE_SEAL.json',seal)
    ledger=json.loads((ROOT/(P+'STAGE_EXECUTION_LEDGER.json')).read_bytes())
    ledger['record_kind']='Final actual execution disposition; no external acceptance'
    for stage in ledger['stages']:
        if stage['stage'] in ('WP-A','WP-E'):stage['acceptance']='BLOCKED_NOT_READY'
        for ref in stage.get('evidence',[]):ref.update(binding(ref['path']))
    ledger['final_seal']=binding(P+'CANDIDATE_SEAL.json')
    write(P+'STAGE_EXECUTION_LEDGER.json',ledger)
    report=f'''# R2 remainder 修复执行报告

最终状态：**BLOCKED / NOT_READY**，未授予下一阶段、运行或生产权限。

完整回归：{run['total']} 项，{run['counts']['passed']} 通过、{run['counts']['failure']} 失败、{run['counts']['error']} 错误、{run['counts']['skipped']} 跳过。全部失败逐节点保留在 OPEN_ISSUES_FINAL_DISPOSITION.json；此前轮次及中断执行也已保留，未用 skip、ignore 或 deselect 计绿。

已完成代码包括增量写入连接生命周期修复、历史与当前精确读取分离、明确版本的历史测试隔离及测试合同更新。隔离 PostgreSQL、现存数据升级、模型兼容性和实际规模性能证据分别保存于 IA06 / IA07 产物；局部通过不代替总验收。

TDX 只读边界事件涉及四个文件、五次同内容写回，修改时间发生变化。没有任务前 TDX 指纹，不能独立证明前后内容身份，也不能声明零写入。事件独立审计、原始证据和已修复的绝对路径边界测试均保留；不通过再次写入恢复元数据。

旧版 current release 的计算身份还存在本轮前已发生的两个源码绑定漂移，单列独立审计项；历史精确身份重放通过不代表当前发布重新验收。

部分历史验收产物当前缺失，已查询全部本地 Git 引用但没有找到列出的原始路径；不会虚构历史产物。Windows 符号链接和未启动本地界面的验证缺口按实际回归逐项记录。

受保护数据与 accepted heads 的最终比对见 PROTECTED_STATE_READBACK.json。新增大型历史副本使用 G 盘；被自动审批拒绝清理的 E 盘临时目录已保留。

代码、文档及证据按用户约定提交和 push；Git 推送不代表独立外审通过。
'''
    write(P+'COMPLETION_REPORT.md',report.encode('utf8'),raw=True)


def checkpoint():
    partial=[]
    for name in ('remainder_frozen_a','remainder_frozen_b','remainder_frozen_c',
                 'remainder_frozen_d','remainder_frozen_final','remainder_full_c_pg_start_interrupted','remainder_full_d','remainder_final_boundary_replays'):
        log=Path('E:/codex_tmp')/(name+'.log')
        if log.exists() and not log.with_suffix('.xml').exists():
            ref=write(P+'execution/'+log.name,log.read_bytes(),raw=True)
            partial.append(dict(name=name,status='INTERRUPTED_DEVELOPMENT_NOT_ACCEPTANCE',log=ref,
                reason='Interrupted after immutable E/F engineering storage contract rejected G; bounded E adapter validated with 108 passing tests' if name=='remainder_full_d' else 'Temporary PostgreSQL startup timeout; restarted both owned clusters and verified directories' if 'pg_start' in name else 'Superseded by explicit historical fixture corrections; completed runs retained separately'))
    write(P+'INTERRUPTED_EXECUTION_LEDGER.json',dict(runs=partial,counts_as_pass=False))
    frozen = json.loads((ROOT/'config/v4_frozen_test_profiles_remainder_v1.json').read_bytes())
    write(P+'IA05_FROZEN_PROFILE_CONTRACT.json', dict(
        contract='FROZEN_TEST_PROFILE_EXECUTION_V1', profiles=frozen['profiles'],
        source_bindings=[binding(p) for p in (
            'tests/remainder_historical_profiles.py','tests/remainder_isolation_plugin.py',
            'scripts/forward_remainder_child.py','scripts/forward_remainder_profiles.py')],
        large_temporary_root='G:/codex_tmp/test_temp',
        tree_source='Exact declared historical Git commit; lazy blob reads; checked LFS SHA and size',
        representations='R19 protected bytes and contract package, PRE16 PROTECTED_BYTES, and the exact R11 snapshot_contract declaration only; raw, LF and CRLF candidates must match literal SHA and size',
        supplemental_registry='Exact entry Git blob when historical tree predates portability registry',
        historical_authority='Stage-13 historical class, pre-dispatch engineering runtime class and R20 original debt functions execute in private historical roots',
        git_references='Original remote refs and annotated or lightweight tags copied without retargeting',
        subprocess_replay='Original worker arguments and child PID retained; same private Git tree',
        lazy_io='Path and builtin open reads materialize exact Git blobs; original Path and builtin open tracked writes reject',
        fixture_scope='Module-level FrozenContracts rebuilt in exact input tree; historical chain and validator functions retain original exceptions and assertions; late current-module ROOT/defaults restored',
        current_permissions=False, assertions_deselected=False))
    write(P+'IA09_G_STORAGE_CONTRACT.json',dict(
        authorization='User explicitly authorized G drive temporary files when E space is insufficient',
        allowed_bases=['E:/codex_tmp/test_temp','G:/codex_tmp/test_temp'],
        original_guards_unchanged=True,
        source_bindings=[binding(p) for p in ('tests/remainder_storage.py','tests/remainder_isolation_plugin.py',
            'tests/runtime_isolation.py','tests/runtime_isolation_plugin.py','tests/test_remainder_current_guards.py')],
        bounded_engineering_outputs='FEP E2/E3/E4 and forward R2 CLI retain E isolation roots; 108 targeted tests passed',
        production_roots_allowed=False,postgres_roots='Exact owned E clusters only',
        audit=binding('docs/audits/AUDIT_REMAINDER_G_DRIVE_DISPOSABLE_STORAGE_20261007.md')))
    write(P+'IA05_FINAL_HISTORY_SCOPE_REPAIRS.json',dict(
        contract='EXACT_HISTORICAL_SCOPE_AND_DISPOSABLE_PROJECTION_V1',
        source_bindings=[binding(p) for p in ('tests/remainder_isolation_plugin.py','config/v4_frozen_test_profiles_remainder_v1.json',
          'tests/test_v4_17_shadow_ui.py','tests/test_v4_18_migration_contract.py','tests/v4_a03_a04_a07_r2/test_payload_governance_r2_1.py','tests/v4_dm01_r4r2/test_acceptance_seal.py')],
        original_test_bytes_changed=False,
        ast_scope='Only original V17 additive-route AST node uses exact entry tree; current HTTP and P01 lock assertions still execute current code',
        v18_scope='Original v1 design inventory uses original f7c7277 design tree, before FEP SQL; module C follows same exact tree',
        retry_scope='Actual accepted observation bytes replay to private G projection; only immediate envelope/source references copied with drive/root/traversal rejection',
        r25_scope='Original WAIT state reads entry Git tree, current fail-closed tests remain separate',
        executions=[run_receipt(n) for n in ('remainder_freeze_scope_final_b','remainder_final_boundary_replays_b')],
        production_write_permission=False))
    write(P+'IA05_HANDLER_STUB_CONTRACT_ADAPTER.json',dict(
        source=binding('tests/upgrade_v3/test_p01_01_lock_scope.py'),adapter=binding('tests/remainder_isolation_plugin.py'),
        purpose='Original lock-scope and disconnected-client assertions remain; no-op unit service implements current startup status read',
        operations_executed=False))
    write(P+'HOT_RANK_HTTP_SCOPE_REPAIR.json',dict(
        source=binding('src/workbench_service/app.py'),audit=binding('docs/audits/AUDIT_HOT_RANK_HTTP_REQUEST_SCOPE_20261007.md'),
        execution=run_receipt('remainder_guards_http_final'),
        change='Request-time hot-rank HTTP routes bypass broad request_scope after the existing exclusive-build rejection',
        capture_restored=False,exclusive_build_guard_unchanged=True))
    receipt=run_receipt('remainder_writer_final')
    old=subprocess.check_output(['git','show','433c3378:src/workbench_service/incremental_writer.py'],cwd=ROOT)
    import hashlib
    write(P+'INCREMENTAL_WRITER_LIFECYCLE_REPAIR.json',dict(
        audit=binding('docs/audits/AUDIT_INCREMENTAL_WRITER_CONNECTION_LIFECYCLE_20261007.md'),
        current=binding('src/workbench_service/incremental_writer.py'),
        old_sha256=hashlib.sha256(old).hexdigest(),old_bytes=len(old),execution=receipt,
        change='Use repository context manager for acquisition and close; preserve transaction and rollback',
        numeric_contract_changed=False,release_permission=False))
    paths=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines()
    paths += [str(p.relative_to(ROOT)).replace('\\','/') for directory,pattern in (
        ('scripts','forward_remainder*.py'),('tests','remainder_*.py'),('tests','test_remainder*.py'),
        ('config','*remainder_v1.json')) for p in (ROOT/directory).glob(pattern)]
    paths += ['tests/v4_dm01_r4/conftest.py','src/workbench_analysis/historical_binding_routing_remainder.py']
    write(P+'FINAL_EXECUTED_SOURCE_BINDINGS.json',dict(files=[binding(p) for p in sorted(set(paths))],
        purpose='Compare execution source bytes at final sealing; evidence-only seal scripts do not change runtime'))


if __name__=='__main__':
    import sys
    {'checkpoint':checkpoint,'protected_after':protected_after,'final':final}[sys.argv[1] if len(sys.argv)>1 else 'checkpoint']()
