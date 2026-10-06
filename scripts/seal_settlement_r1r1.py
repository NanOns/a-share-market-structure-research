"""Atomic P0-02 residual evidence, with protected-byte and executed-case gates."""
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from scripts.full_chain_repair_io import ROOT,write,binding

PREFIX='reports/full_chain_repair_r1r1_20261006/'
BASE='efe2d0c5f2b0d94878929120521fa48982e3cf56'
CHANGES={'.gitattributes','scripts/build_full_chain_runtime_successor.py',
    'scripts/v4_16_go_forward_shadow_runtime_r4r3.py','scripts/v4_16_settlement_worker_v2.py',
    'config/v4_16_runtime_dependencies_v5.json','config/v4_16_settlement_worker_contract_v2.json'}

def authority_proof():
    from tests.test_settlement_r1r1 import accepted
    from scripts.v4_16_go_forward_shadow_runtime_r4r3 import SettlementObligationControllerR4R2
    fixture=accepted.__wrapped__();db,x,a,b,ref=next(fixture)
    old={ '__name__':'scripts._r1r1_baseline_runtime','__file__':str(ROOT/'scripts/v4_16_go_forward_shadow_runtime_r4r3.py') }
    exec(compile(subprocess.check_output(['git','show',BASE+':scripts/v4_16_go_forward_shadow_runtime_r4r3.py']).decode('utf8'),'frozen_baseline.py','exec'),old)
    selections=[]
    try:
        for target in (b,a):
            db.conn.execute('UPDATE activation_head SET authority_id=?',(target,))
            current=SettlementObligationControllerR4R2(ROOT,db.path,simulation=True,simulation_dependencies=x['manifest'])
            prior=old['SettlementObligationControllerR4R2'](ROOT,db.path,simulation=True,simulation_dependencies=x['manifest'])
            assert current.activation['authority_id']==target
            selections.append(dict(head=target,selected=current.activation['authority_id'],baseline_selected=prior.activation['authority_id'],historical_activation_facts=len(db.rows('activation'))))
        assert selections[1]['baseline_selected']!=selections[1]['head']
        return dict(origin='ACTIVATION_SIMULATION',real_evidence=False,executed_selections=selections,
            baseline_selector='FACT_LIST_LAST_ITEM',candidate_selector='EXACT_ACTIVATION_HEAD_SINGLETON_AND_FACT_ID',
            selected_binding_exact=True,activation_fact_history_preserved=True)
    finally:
        try:next(fixture)
        except StopIteration:pass

def queue_proof():
    from tests.test_full_chain_repair import shadow,future
    from scripts.v4_16_settlement_worker_v2 import DurableSettlementWorker
    from scripts.v4_16_shadow_runtime import digest
    fixture=shadow.__wrapped__();db,x=next(fixture)
    try:
        authority,source=future(db);worker=DurableSettlementWorker(db,'PROOF')
        due=next(d for d in db.rows('due') if d['horizon']==1);due_id=digest([due['enrollment_id'],1]);sha=source.binding['sha256']
        key=worker.enqueue(due_id,sha,'2026-10-09');before=worker.row(key,sha)
        assert worker.enqueue(due_id,sha,'2026-10-09')==key and worker.row(key,sha)==before
        revised_sha=digest('R1R1_CONFLICT_PROOF_SOURCE_ONLY')
        other=next(d for d in db.rows('due') if d['horizon']!=1);other_id=digest([other['enrollment_id'],other['horizon']])
        db.conn.execute("INSERT INTO settlement_queue_v2(queue_key,evaluation_source_digest,due_kind,due_id,status) VALUES(?,?,?,?,'READY')",(key,revised_sha,'due',other_id))
        old={'__name__':'scripts._r1r1_baseline_worker'}
        exec(compile(subprocess.check_output(['git','show',BASE+':scripts/v4_16_settlement_worker_v2.py']).decode('utf8'),'frozen_queue.py','exec'),old)
        prior=old['DurableSettlementWorker'](db,'BASELINE_PROOF')
        assert prior.enqueue(due_id,revised_sha,'2026-10-09')==key
        try:worker.enqueue(due_id,revised_sha,'2026-10-09')
        except ValueError as error:assert str(error)=='QUEUE_IDEMPOTENCY_CONFLICT'
        else:raise AssertionError('CONFLICT_NOT_REJECTED')
        assert worker.row(key,revised_sha)['due_id']==other_id
        return dict(origin='ACTIVATION_SIMULATION',real_evidence=False,exact_retry_row=before,
            baseline_conflict_silently_ignored=True,candidate_conflict='QUEUE_IDEMPOTENCY_CONFLICT',
            conflicting_row_retained=True,comparison_fields=['queue_key','evaluation_source_digest','due_kind','due_id'],
            frozen_identity_fields=['namespace','model_contract_id','state_lineage_id','enrollment_id','horizon','due_trade_date','outcome_contract_id'],
            Q03_fixture='Malformed persisted queue row injected with FK temporarily disabled in disposable simulation',
            Q04_fixture='Injected inconsistent immutable-enrollment readback; no persistent fact mutation',
            Q05_evidence='Executed corrected source produces evaluation_revision=2 and retains original outcome')
    finally:
        try:next(fixture)
        except StopIteration:pass

def seal():
    entry=json.loads((ROOT/(PREFIX+'ENTRY_BASELINE.json')).read_bytes())
    assert entry['baseline_commit']==BASE
    changed=[b['path'] for b in entry['tracked_bindings'] if binding(b['path'])!=b]
    assert set(changed)==CHANGES,changed
    protected=[b for b in entry['protected'] if binding(b['path'])==b]
    assert protected==entry['protected']
    deps=json.loads((ROOT/'config/v4_16_runtime_dependencies_v5.json').read_bytes())
    assert deps['contract_id']=='V4_16_RUNTIME_DEPENDENCIES_V5'
    for b in deps['bindings']:assert binding(b['path'])==b,b['path']
    audit=json.loads((ROOT/'data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json').read_bytes())
    assert audit['entries']['A08_CURRENT_RUNTIME']['current_state']=='OPEN_EXTERNAL_REAUDIT'
    from scripts.v4_16_capability_resolution import resolve
    cap=json.loads((ROOT/'config/v4_16_runtime_capability_resolution_v1.json').read_bytes())
    resolution=resolve(cap,audit,['PURE_CORE_STOCK']);assert resolution['admitted'] is False
    from scripts.validate_r25_preflight import selection,disabled
    actual=selection();assert actual['status']=='WAIT_ACCEPTED_DAILY_INPUT'
    activation=json.loads((ROOT/'config/v4_16_runtime_activation_authority_v4.json').read_bytes());disabled(activation)
    absent=[f'data/v4/V4_{n}_ACCEPTED_HEAD.json' for n in range(16,23)]
    assert not any((ROOT/p).exists() for p in absent)
    assert not (ROOT/'data/v4/shadow_real_v1').exists()
    previous=json.loads((ROOT/'reports/full_chain_repair_20261006/PROTECTED_STATE_READBACK.json').read_bytes())
    state=dict(previous,protected_bindings=protected,unchanged=True,A08='OPEN_EXTERNAL_REAUDIT',
        PURE_CORE_STOCK='BLOCK',R25=actual,First_Real_Shadow='NOT_AUTHORIZED',storage_created=False)
    write(PREFIX+'PROTECTED_STATE_READBACK.json',state)
    summaries={};cases=[]
    for name in ('final_targeted','entrypoint_regression'):
        parsed=ET.parse(ROOT/(PREFIX+name+'.xml')).findall('.//testcase')
        assert parsed and not any(c.find('error') is not None or c.find('skipped') is not None for c in parsed)
        failures=[c.attrib['classname']+'::'+c.attrib['name'] for c in parsed if c.find('failure') is not None]
        if name=='final_targeted':assert not failures
        else:
            assert failures==['tests.test_r25_packet::test_f12_valid_latest_decoy']
            inherited=json.loads((ROOT/'reports/full_chain_repair_20261006/SCOPED_REGRESSION_SUMMARY.json').read_bytes())
            assert all(node in inherited['failed_nodes'] for node in failures)
            assert all('EXACT_DEPENDENCY_MISMATCH' in c.find('failure').text for c in parsed if c.find('failure') is not None)
        summaries[name]=dict(passed=len(parsed)-len(failures),failed=len(failures),skipped=0,known_failure_nodes=failures,introduced_failure_nodes=[],xml=binding(PREFIX+name+'.xml'))
        cases.extend(dict(node=c.attrib['classname']+'::'+c.attrib['name'],status='PASS_EXECUTED' if c.find('failure') is None else 'KNOWN_BASELINE_DEBT') for c in parsed)
    for label in ('A01','A02','A03','A04','A05','A06','Q01','Q02','Q03','Q04','Q05'):
        assert any('['+label+']' in c['node'] for c in cases),label
    write(PREFIX+'TARGETED_TEST_SUMMARY.json',dict(suites=summaries,introduced_failure_nodes=0,
        initial_failures='Fixture construction errors retained in initial.xml and targeted.xml; corrected before final execution'))
    write(PREFIX+'NEGATIVE_MATRIX.json',dict(cases=cases,required_labels=['A01','A02','A03','A04','A05','A06','Q01','Q02','Q03','Q04','Q05']))
    write(PREFIX+'ACTIVATION_HEAD_SELECTION_PROOF.json',authority_proof())
    write(PREFIX+'QUEUE_IDEMPOTENCY_PROOF.json',queue_proof())
    keep={}
    for item in entry['pass_keep']:
        seal_path='reports/full_chain_repair_20261006/'+item+'/CANDIDATE_SEAL.json'
        keep[item]=dict(status='PASS_KEEP',prior_evidence=binding(seal_path),code_and_contract_bytes_unchanged=True)
    keep['runtime_shared_binding_refresh']=dict(scope='P0_02_ONLY',changed_existing_paths=sorted(CHANGES),other_repair_implementations_and_migrations_unchanged=True)
    write(PREFIX+'PASS_KEEP_READBACK.json',keep)
    write(PREFIX+'INDEPENDENT_AUDIT_ITEM_REGISTRY.json',dict(
        P0_02_R1R1=dict(scope='EXACT_ACTIVATION_HEAD_AND_QUEUE_IDEMPOTENCY',status='CANDIDATE_REPAIRED_EXTERNAL_AUDIT_PENDING'),
        AUD_R25_F12_HISTORICAL_FIXTURE_BINDING=dict(scope='UNCHANGED_V3_HISTORICAL_SIMULATION_FIXTURE_BINDING',status='OPEN_INHERITED_DEBT',
            node='tests.test_r25_packet::test_f12_valid_latest_decoy',current_evidence=binding(PREFIX+'entrypoint_regression.xml'),
            baseline_evidence=binding('reports/full_chain_repair_20261006/SCOPED_REGRESSION_SUMMARY.json'),
            acceptance='INDEPENDENT_FROM_P0_02_GATE; NO_CHANGE_TO_FROZEN_FIXTURE_OR_OTHER_SIX_PASS_ITEMS')))
    status=dict(P0_02_R1R1='CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',external_acceptance=False,
        first_real_shadow_authorized=False,production=False,next_stage='INDEPENDENT_TARGETED_P0_02_ACCEPTANCE')
    report=f'''# P0-02 R1R1 修复候选完成报告

状态：CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT。

本轮只修 activation_head 精确重启和队列 exact idempotency。重启通过只读事务读取唯一 singleton head，然后精确读取相应 activation fact，并校验 digest、authority_id、authority binding、external acceptance、grant、V5 dependency digest 和 storage identity。A/B 多 activation 历史合法保留，Head 指向哪项就选择哪项；不使用末项、日期或文件排序。

enqueue 在同一事务内 INSERT OR IGNORE 后逐字段核对 queue_key / evaluation_source_digest / due_kind / due_id，再从持久 due 和 enrollment 重新计算冻结身份。相同重试保持原行；冲突报 QUEUE_IDEMPOTENCY_CONFLICT 并回滚，校正 source digest 仍可生成新 evaluation revision。不新增或修改 migration。

定向验收 {summaries['final_targeted']['passed']} 次通过，定向失败和跳过均为 0。包括 A01–A06、Q01–Q05，以及已有 queue、双连接 CAS、V3 rejection、V5 stop/restart、publication rollback、未知 due calendar extension、P0-01 capability 和 P1-03 DB integrity 测试。入口回归 {summaries['entrypoint_regression']['passed']} 次通过，1 项既有 R25 F12 历史夹具绑定债务与基线一致，单独审计跟踪；新增失败为 0。完整六项实现、合同、旧证据和迁移按入口字节核对保持不变。初始夹具失败保留原始 XML。

已实际复现旧 selector 在 Head=A 时错误选择 B，以及旧 enqueue silent ignore；候选实现均拒绝或精确选择。所有新执行数据来自隔离 ACTIVATION_SIMULATION，真实观察计数仍为 0。A08 保持 OPEN_EXTERNAL_REAUDIT；PURE_CORE_STOCK 阻断、R25 WAIT、First Real Shadow 未授权。生产、Focus、Default UI、FEP_PRODUCTION、MODEL_DISPLAY、PRIORITY_USE、CHAMPION、REAL_OOS 保持原状态；V4-16–22 formal Accepted Head 仍缺失。TDX 输入未写入，未执行 scanner。

下一步：独立定点验收 P0-02。代码提交和 push 不代表外审通过或开启运行权限。
'''
    write(PREFIX+'COMPLETION_REPORT.md',report.encode(),raw=True)
    artifacts=[binding(p.relative_to(ROOT).as_posix()) for p in (ROOT/PREFIX).rglob('*') if p.is_file() and p.name!='CANDIDATE_SEAL.json']
    code=[binding(p) for p in sorted(CHANGES|{'config/v4_16_settlement_restart_idempotency_v1.json','scripts/build_settlement_r1r1_contract.py','scripts/seal_settlement_r1r1.py','tests/test_settlement_r1r1.py'})]
    write(PREFIX+'CANDIDATE_SEAL.json',dict(status,evidence=artifacts,code=code,protected_byte_check=True,pass_keep=list(keep)))
    print(json.dumps(status))

if __name__=='__main__':seal()
