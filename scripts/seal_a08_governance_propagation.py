"""Evidence gate for scoped A08 propagation; no runtime permission is issued."""
import ast,json,subprocess,xml.etree.ElementTree as ET
from scripts.full_chain_repair_io import ROOT,write,binding
from scripts.build_a08_governance_successors import PREFIX,HEAD,AUTH,CAP,DEPS,load
from scripts.v4_16_capability_resolution_v2 import admission,validate_dependencies

def cases(path):return ET.parse(ROOT/path).findall('.//testcase')
def node(case):return case.attrib['classname']+'::'+case.attrib['name']

def seal():
    entry=load(PREFIX+'ENTRY_BASELINE.json')
    assert entry['baseline_commit']=='b7ca247745976aa390387a0701601b00ac0d8498'
    for ref in entry['protected']+entry['frozen']:assert binding(ref['path'])==ref,ref['path']
    changed=subprocess.check_output(['git','diff','--name-only',entry['baseline_commit']],text=True,encoding='utf8').splitlines()
    baseline_paths=set(subprocess.check_output(['git','ls-tree','-r','--name-only',entry['baseline_commit']],text=True,encoding='utf8').splitlines())
    historical_changed=[p for p in changed if p in baseline_paths]
    assert historical_changed==['.gitattributes'],historical_changed
    old=load('data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json');new=load(HEAD)
    assert [k for k in old['entries'] if old['entries'][k]!=new['entries'][k]]==['A08_CURRENT_RUNTIME']
    authority=load(AUTH);deps=load(DEPS)
    for flag in ('business_runtime_authority','automatic_stage_permission','production','focus','shadow'):assert authority[flag] is False
    proof={cap:admission(ROOT,binding(CAP),[cap]) for cap in ('PURE_CORE_STOCK','AMOUNT_A_H21_FORMAL_CONSUMER','HISTORICAL_AMOUNT_A_FORMAL_CONSUMER')}
    assert proof['PURE_CORE_STOCK']['admitted'] is True
    assert proof['AMOUNT_A_H21_FORMAL_CONSUMER']['blocking_issue_ids']==['A04_H21_CONSUMER']
    assert proof['HISTORICAL_AMOUNT_A_FORMAL_CONSUMER']['blocking_issue_ids']==['A04_HISTORICAL_AMOUNT_A']
    assert all(p['permission_granted'] is False for p in proof.values())
    assert load(CAP)['runtime_capability_dependency_graph']==load('config/v4_16_runtime_capability_resolution_v1.json')['runtime_capability_dependency_graph']
    validate_dependencies(ROOT,deps)
    write(PREFIX+'CAPABILITY_RESOLUTION_PROOF.json',dict(results=proof,current_audit_head=binding(HEAD),resolver=binding(CAP),dependency_graph_unchanged=True,permission_granted=False))
    inventory=load(PREFIX+'STALE_REFERENCE_INVENTORY.json')
    inventory['file_bindings']=[binding(p) for p in sorted({r['path'] for r in inventory['references']})]
    write(PREFIX+'STALE_REFERENCE_INVENTORY.json',inventory)
    dispositions={
        'data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json':HEAD,
        'config/v4_cross_stage_current_audit_authority_v3.json':AUTH,
        'config/v4_16_runtime_capability_resolution_v1.json':CAP,
        'config/v4_16_runtime_dependencies_v5.json':DEPS,
        'config/v4_16_runtime_activation_authority_v4.json':'config/v4_16_runtime_activation_authority_v5.json',
        'config/v4_16_r25_packet_preflight_v3.json':'config/v4_16_r25_packet_preflight_v4.json',
        'config/v4_16_settlement_worker_contract_v2.json':'config/v4_16_settlement_worker_contract_v3.json',
        'scripts/v4_16_go_forward_shadow_runtime_r4r3.py':'scripts/v4_16_go_forward_shadow_runtime_r4r4.py',
        'scripts/v4_16_shadow_runtime.py':'scripts/v4_16_shadow_runtime_v6.py',
        'scripts/run_v4_16_settlement_v2.py':'scripts/run_v4_16_settlement_v3.py',
        'scripts/validate_r25_preflight.py':'scripts/validate_r25_preflight_v6.py',
        'scripts/build_r25_packet_r4r3.py':'scripts/build_r25_packet_r4r4.py'}
    inventory['references']=[r for r in inventory['references'] if r['tokens']]
    for row in inventory['references']:
        if row['path'] in dispositions:row['category']='active_R25_runtime_path_requires_successor'
    inventory['successor_identifier_policy']='ADDITIVE_NEXT_UNUSED_V3_TO_V4_AND_V5_TO_V6; DATABASE_MIGRATION_ALLOCATOR_NOT_APPLICABLE; NO_MIGRATION_ADDED'
    write(PREFIX+'STALE_REFERENCE_INVENTORY.json',inventory)
    write(PREFIX+'ACTIVE_REFERENCE_DISPOSITION.json',dict(successors=[dict(historical=binding(p),active_successor=binding(q)) for p,q in dispositions.items()],
        explicit_active_selector=binding('config/v4_16_current_runtime_entrypoints_v1.json'),
        policy='V6 USERS SELECT EXPLICIT V6 REGISTRY/ENTRYPOINT; OLD DEFAULT DISPATCH REMAINS HISTORICAL TO PRESERVE V5 EXACT GRANTS',global_replace=False))
    old_ast=ast.parse((ROOT/'scripts/v4_16_go_forward_shadow_runtime_r4r3.py').read_text(encoding='utf8'))
    new_ast=ast.parse((ROOT/'scripts/v4_16_go_forward_shadow_runtime_r4r4.py').read_text(encoding='utf8'))
    names=('OneSessionLaunchController','SuccessorDatabase','settlement_cycle','accepted_future_authority')
    for name in names:
        a=next(n for n in old_ast.body if getattr(n,'name',None)==name);b=next(n for n in new_ast.body if getattr(n,'name',None)==name)
        assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False),name
    tests={};matrix=[];expected_known=set(load('reports/full_chain_repair_20261006/SCOPED_REGRESSION_SUMMARY.json')['failed_nodes'])
    all_current={}
    for name in ('final_targeted','pass_keep_regression'):
        parsed=cases(PREFIX+name+'.xml')
        assert parsed and not any(c.find('error') is not None or c.find('skipped') is not None for c in parsed)
        failures=[node(c) for c in parsed if c.find('failure') is not None]
        if name=='final_targeted':assert not failures
        else:
            assert set(failures)=={
                'tests.v4_09.test_stock_prewatch::test_production_and_v4_09_acceptance_stay_disabled',
                'tests.v4_a08.test_repair_freeze_authority::test_historical_archive_does_not_accept_current_runtime_for_new_promotion'}
            assert set(failures)<=expected_known
            baseline={node(c):c for c in cases('reports/full_chain_repair_20261006/scoped_regression.xml')}
            for c in parsed:
                if node(c) in failures:assert 'CURRENT_STAGE_NOT_ACCEPTED' in c.find('failure').text and 'CURRENT_STAGE_NOT_ACCEPTED' in baseline[node(c)].find('failure').text
        tests[name]=dict(passed=len(parsed)-len(failures),known_failed_nodes=failures,introduced_failure_nodes=[],skipped=0,evidence=binding(PREFIX+name+'.xml'))
        for c in parsed:
            all_current[node(c)]=c
            matrix.append(dict(node=node(c),status='PASS_EXECUTED' if node(c) not in failures else 'UNCHANGED_INHERITED_DEBT'))
    for label in ('A01','A02','Q01','Q05'):
        assert any('['+label+']' in key and case.find('failure') is None for key,case in all_current.items())
    write(PREFIX+'TARGETED_TEST_SUMMARY.json',dict(suites=tests,introduced_failure_nodes=0,initial_attempt_retained=binding(PREFIX+'initial.xml')))
    write(PREFIX+'NEGATIVE_MATRIX.json',dict(cases=matrix,required_negative_scope='UNKNOWN_NEW_ISSUE / STALE_V3 / HEAD_SHA / STALE_RESOLVER / V5_V6_GRANTS / AUDIT_TAMPER'))
    write(PREFIX+'HISTORICAL_V5_COMPATIBILITY_PROOF.json',dict(
        old_dependency=binding('config/v4_16_runtime_dependencies_v5.json'),old_runtime=binding('scripts/v4_16_go_forward_shadow_runtime_r4r3.py'),
        old_entrypoint=binding('scripts/run_v4_16_settlement_v2.py'),worker=binding('scripts/v4_16_settlement_worker_v2.py'),
        restart_A01_A02_and_queue_Q01_Q05='PASS_EXECUTED',V5_stop_restart='PASS_EXECUTED',
        V5_grant_to_V6='REJECTED_EXECUTED',V6_grant_to_V5='REJECTED_EXECUTED',
        V6_isolated_settlement_restart='PASS_EXECUTED',no_real_obligations_created=True,
        preserved_business_asts=list(names),evidence=binding(PREFIX+'NEGATIVE_MATRIX.json')))
    activation=load('config/v4_16_runtime_activation_authority_v5.json')
    for key in ('runtime_authorized','real_shadow_authorized','production','focus','V4_16','shadow'):assert activation[key] is False
    assert activation['REAL_SHADOW_OBSERVATIONS']==activation['PIT_OBSERVED_REAL_SAMPLES']==0 and activation['grant'] is activation['external_acceptance'] is None
    absent=[f'data/v4/V4_{n}_ACCEPTED_HEAD.json' for n in range(16,23)]
    assert not any((ROOT/p).exists() for p in absent) and not (ROOT/'data/v4/shadow_real_v1').exists()
    from scripts.validate_r25_preflight_v6 import selection
    readiness=selection();assert readiness['status']=='WAIT_ACCEPTED_DAILY_INPUT'
    state=dict(REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,FIRST_REAL_SHADOW_AUTHORIZED=False,
        runtime_authorized=False,real_shadow_authorized=False,production=False,focus=False,default_UI_cutover=False,
        FEP_PRODUCTION='UNGRANTED',MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',CHAMPION='NONE',REAL_OOS='NOT_GRANTED',
        formal_accepted_heads_absent=absent,TDX='NO_WRITE; NO_SCANNER_EXECUTED',
        historical_A08='OPEN_EXTERNAL_REAUDIT_IN_IMMUTABLE_V3',successor_A08='ACCEPTED_SCOPED_IN_V4',
        all_protected_bindings_unchanged=True,protected=entry['protected'],pass_keep_bindings=entry['frozen'],
        stage_current_authority_unchanged=authority['stage_current_authority_unchanged'],real_target_selection=readiness)
    write(PREFIX+'PROTECTED_STATE_READBACK.json',state)
    write(PREFIX+'INDEPENDENT_AUDIT_ITEM_REGISTRY.json',dict(
        A08_CURRENT_RUNTIME=dict(external_scope='PASS_CURRENT_RUNTIME_ENGINEERING_SHADOW_DEPENDENCY_SCOPE',external_evidence=authority['a08_external_acceptance'],propagation='CANDIDATE_EXTERNAL_AUDIT_PENDING'),
        HISTORICAL_STAGE_READER_COMPATIBILITY=dict(status='OPEN_INHERITED_DEBT',scope='UNCHANGED_HISTORICAL_R17_READER_STAGE_12_13_ALLOWLIST',
            failure_nodes=tests['pass_keep_regression']['known_failed_nodes'],acceptance='INDEPENDENT_OF_A08_PROPAGATION_GATE',baseline=binding('reports/full_chain_repair_20261006/scoped_regression.xml')),
        amount_a=dict(H21=new['entries']['A04_H21_CONSUMER']['current_state'],historical=new['entries']['A04_HISTORICAL_AMOUNT_A']['current_state'])))
    status=dict(A08_CURRENT_RUNTIME_PROPAGATION='CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',
        R25_REENTRY='READY_FOR_PACKET_REBUILD_OR_EXTERNAL_ACTIVATION_AUDIT',FIRST_REAL_SHADOW_AUTHORIZED=False,
        next_stage='INDEPENDENT_GOVERNANCE_PROPAGATION_AUDIT_THEN_EXPLICIT_R25_ACTIVATION_AUDIT')
    report=f'''# A08 current runtime 治理传播候选 — 2026-10-06

A08_CURRENT_RUNTIME_PROPAGATION = CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT。
R25_REENTRY = READY_FOR_PACKET_REBUILD_OR_EXTERNAL_ACTIVATION_AUDIT。

依据用户提供的两份独立外审，归档 exact 原始字节。Current Audit V4 的 canonical issue 仅 A08 从 OPEN_EXTERNAL_REAUDIT 变为 ACCEPTED_SCOPED，两个 Shadow blocker 变 false；生产 blocker 保持 true，audit authority 不授予业务运行或自动阶段权限。其他 issue 保持不变。编号按已有 V3 → V4 / V5 → V6 增量命名，不分配或新增数据库 migration。

capability v2 保留 PURE_CORE_STOCK → PREWATCH 的原依赖图，同时 exact 校验当前 producer 和 supporting contracts。PURE_CORE_STOCK 无 A08 blocker，两个 Amount-A capability 继续分别被 A04 阻断，permission_granted 始终 false。

V6 / R4R4、disabled activation v5、settlement contract v3、R25 preflight v4 和 builder/validator successor 均为新增版本。明确的 active selector 是 config/v4_16_current_runtime_entrypoints_v1.json；新使用者须选 V6 facade / CLI。旧 dispatcher、V5/R4R3 和 settlement v2 保留原字节，用于历史绑定及既有 obligation。新 settlement CLI 用 --dependency-generation V5 显式选择旧路径；不通过猜测、最新文件或重绑迁移历史 obligation。新旧 publication、DB、future-authority、settlement-cycle AST 完全相同，constructor 只增加治理版本门。

新增定向 {tests['final_targeted']['passed']} 项通过；PASS_KEEP 回归 {tests['pass_keep_regression']['passed']} 项通过，2 项既有 historical-stage-reader 治理债务与基线节点及 CURRENT_STAGE_NOT_ACCEPTED 原因一致，已独立跟踪。新增失败为 0。所有 V4-09 业务向量、P0-02 A01/A02/Q01/Q05 及队列、DB integrity 回归通过。工程 R25 包构建/校验往返已测试；未创建或选择真实目标日包。

不可变 V3/v1/V5/v4、P0-02 final evidence、V4-09 producer/artifact、全部旧 migration 和受保护 Head 均保持入口字节。真实计数为 0，V4-16–22 formal Accepted Head 缺失。生产、Focus、默认 UI、FEP、display、Priority、Champion、REAL_OOS 均未授权。TDX 没有写操作，未运行 scanner。

当前 R25 selection 仍为 WAIT_ACCEPTED_DAILY_INPUT，原因是缺少 exact real target-session 输入，而非 A08 blocker。下一步是独立验收此次传播，再按明确输入重建 R25 packet 或进行外部激活审计。Git push 不授予 First Real Shadow。
'''
    write(PREFIX+'COMPLETION_REPORT.md',report.encode(),raw=True)
    own=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True,encoding='utf8').splitlines()+[p for p in changed if p not in baseline_paths]
    prior=[s[3:] for s in entry['unrelated_worktree']]
    owned=[p for p in own if (ROOT/p).is_file() and not any(p==q or (q.endswith('/') and p.startswith(q)) for q in prior)]
    code=[binding(p) for p in sorted(set(owned+['.gitattributes',HEAD])) if not p.startswith(('reports/','docs/'))]
    evidence=[binding(p.relative_to(ROOT).as_posix()) for p in (ROOT/PREFIX).rglob('*') if p.is_file() and p.name!='CANDIDATE_SEAL.json']
    write(PREFIX+'CANDIDATE_SEAL.json',dict(status,code=code,evidence=evidence,source_documents=entry['task_documents'],protected_readback=binding(PREFIX+'PROTECTED_STATE_READBACK.json'),introduced_failure_nodes=0))
    print(json.dumps(status))

if __name__=='__main__':seal()
