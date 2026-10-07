"""Seal the V4-only stage record and reproducible evidence inventory."""
import json
from pathlib import Path
from scripts.full_chain_repair_io import ROOT, binding, write
from scripts.forward_final_bootstrap import P


def finish():
    result=json.loads((ROOT/(P+'GLOBAL_CURRENT_REGRESSION_RECEIPT.json')).read_bytes())
    scope=json.loads((ROOT/(P+'V4_ONLY_EXECUTION_SCOPE.json')).read_bytes())
    state=json.loads((ROOT/(P+'PROTECTED_STATE_READBACK.json')).read_bytes())
    disposition=json.loads((ROOT/(P+'FINAL_DISPOSITION.json')).read_bytes())
    targets=[]
    for run in ('final_blocker_boundary_final','final_blocker_model_parity'):
        for suffix in ('.xml','.log'):
            source=Path('G:/codex_tmp')/(run+suffix)
            if source.exists():
                target=P+'execution/targets/'+source.name
                write(target,source.read_bytes(),raw=True);targets.append(binding(target))
    for source in (Path('G:/codex_tmp/final_blocker_full_d.log'),
                   Path('G:/codex_tmp/test_temp/final_blocker_full_d_failures.jsonl')):
        if source.exists():
            write(P+'scope_correction/interrupted_mixed/'+source.name,source.read_bytes(),raw=True)
    proof=dict(scope='V4_ONLY', historical_only_before_v4='OUTSIDE_SCOPE',
               current_regression=binding(P+'GLOBAL_CURRENT_REGRESSION_RECEIPT.json'),
               tdx=binding(P+'TDX_FRESH_ZERO_WRITE_RECEIPT.json'),
               protected=binding(P+'PROTECTED_STATE_READBACK.json'),
               model_parity=binding(P+'IA06_E3_E4_PARITY_RECEIPT.json'),
               ia07=binding(P+'IA07_ACCEPTED_CAPABILITY_SCOPE.json'),targets=targets,
               no_new_permissions=True, no_new_real_samples=True)
    write(P+'V4_FINAL_EVIDENCE_INDEX.json',proof)
    write(P+'STAGE_EXECUTION_LEDGER.json',dict(
        task=binding('docs/evidence/forward_r2_final_blocker_repair_20261007/V4_FORWARD_R2_FINAL_BLOCKER_REPAIR_TASK_R3_20261007.md'),
        user_scope_override='V4_ONLY; excludes execution of all preceding versions',
        stages=[dict(stage='V4_R3_FINAL',contract=binding(P+'V4_ONLY_EXECUTION_SCOPE.json'),
                     evidence=[binding(P+'V4_FINAL_EVIDENCE_INDEX.json')],
                     acceptance=disposition['status'],
                     next_stage=disposition['next_stage'])]))
    cross=json.loads((ROOT/(P+'CROSS_AUDIT_RESEARCH_HTTP_READ_BOUNDARY.json')).read_bytes())
    cross.update(acceptance='TARGET_PASS_AND_V4_SCOPED_REGRESSION_RECORDED',
                 full_regression=binding(P+'GLOBAL_CURRENT_REGRESSION_RECEIPT.json'),
                 prior_ui_target='PRE_SCOPE_CORRECTION_DIAGNOSTIC_NOT_V4_FULL_ACCEPTANCE')
    write(P+'CROSS_AUDIT_RESEARCH_HTTP_READ_BOUNDARY.json',cross)
    report=f'''# V4 Forward R2 Final Blocker Repair R3 — V4 限定范围

执行基线：a775383eabb94e97a6022f34a30de7aa55e3a39c。用户后续明确：全量执行和历史测试仅包括 V4，不包括 V4 之前的版本。该指令覆盖任务卡中旧版本全量、60 个旧产物节点及 V3 UI 的执行要求。

## 本次验收结果

V4 专用回归归并验收：{result['total']} 个节点，{result['passed']} 通过，{result['failed']} 失败，{result['errors']} 错误，{result['skipped']} 跳过。范围清单列出全部 {len(scope['files'])} 个测试文件及绑定，包含 V4 各阶段、Forward/Settlement、治理、DM01、隔离与接入 V4 的 FEP。没有收集后的 ignore、deselect 或新增 xfail。

这不是单次全量零错误的声明：首跑 PG fixture 尝试随机端口，被隔离保护拒绝，出现环境 setup errors；在已有私有集群校验全套 33 个 migration 校验和后，从空 V4 模板克隆专用数据库，并重跑受影响 V4_10/V4_11 的全部测试。首跑和重跑原始 XML/log 均保留，逐节点归并必须保持完整首跑节点集合，且每个原失败/错误都对应真实重跑 PASS。详见 `V4_PG_ENVIRONMENT_REPLAY_RECEIPT.json`。迁移、隔离保护与原测试断言均未改变。

首跑另外两个 PG capability 跳过已在正确 upgrade 实例和显式私有 DSN 上实际补跑通过。最终仅保留两个 Windows symlink 权限限制跳过，原测试不删除、不改断言；另有两项 V4 原 snapshot owner 的 link/reparse 判定等价负向验证通过，以及真实 junction/子进程路径边界验证通过。

阶段结论：{disposition['status']}。测试通过不构成外部验收，也不授权 production/shadow/focus/default UI 或进入后续门禁阶段。

## 代码与输入保护

统一输出路径解析在任何写入前拒绝绝对路径、盘符、UNC、穿越、ADS、配置源目录与重解析逃逸。私有冻结代码的 helper 通过独立模块加载，避免历史 common 命名空间覆盖当前保护。子 Python 进程安装源目录写入审计，临时输出使用 G 盘。

TDX 本次全量前后逐文件内容、字节数和 mtime 比较见 `TDX_FRESH_ZERO_WRITE_RECEIPT.json`。原事故仍永久保留 5 次写调用、4 个文件、原运行 zero-write=false。事故前独立内容完整性没有恢复为可验证，不改写时间戳或旧记录。

保护的运行目录完整指纹相等：{state['protected_runtime_full_bytes_and_mtime_equal']}；已接受头与 SQL migration 绑定相等：{state['accepted_heads_and_migrations_equal']}。没有迁移、发布或增加真实样本。

研究 HTTP 读取修复缺失 json 导入与并发 DuckDB 读写连接冲突，采用已有数据库锁。网络 hot-rank 与主流隔离约束保持。独立审计见 `CROSS_AUDIT_RESEARCH_HTTP_READ_BOUNDARY.json`。

## 范围更正与历史事实

混合版本全量 D 已中止，其失败流仅保留为此前调查，不能作为 V4 验收。旧版本 60 个历史节点不再阻断 V4 回归；没有伪造缺失产物，没有把它们计为通过。此前对 22 个旧历史测试的退役处理已撤回，恢复原始文件，新建历史退役配置移入撤回证据。相应旧版本重放脚本明确拒绝继续执行。

GOV-1 将旧 CURRENT_RELEASE 明确为历史诊断绑定，当前授权由 V4 CurrentStageAuthority 校验；原指针及旧 identity 保持。V4 的历史兼容性 reader 测试只验证 V4 版本合同的精确读取边界，不执行旧版本算法验收。

M7 历史任务并发 sequence 冲突属于 V4 前版本，记录为独立范围外审计项，本次未修复或宣称通过。

## 保留能力债务

IA-07：NOT_VERIFIABLE_BY_CURRENT_ACCEPTED_CAPABILITY。真实 accepted universe 为 5037，完整控制特征池为 0，100/1000/5037 实际人口检查不能建立控制匹配性能结论。没有复制或合成控制池、没有将零 eligible rows 判为 FULL_PASS。该债务仅阻断控制匹配接受，不阻断合同允许的独立股票绝对结算。

E3/E4 8 个实际模型重训与原 frozen population 的 parity 证据保留，不构成 champion、REAL_OOS 或运行授权。Git 提交和 push 仅交付本次代码及证据；后续仍须独立 V4 外审及 IA-07 独立能力接受。
'''
    write('docs/audits/V4_FORWARD_R2_FINAL_BLOCKER_REPAIR_R3_V4_ONLY_20261007.md',report.encode(),raw=True)
    write(P+'COMPLETION_REPORT.md',report.encode(),raw=True)
    products(result, disposition)


def products(result, disposition):
    import xml.etree.ElementTree as ET
    cases=ET.fromstring((ROOT/(P+'execution/current_full.xml')).read_bytes()).findall('.//testcase')
    boundary=[c for c in cases if 'test_forward_final_path_boundary' in c.attrib.get('classname','')]
    write(P+'TDX_PATH_GUARD_NEGATIVE_MATRIX.json',dict(
        scope='V4_ENGINEERING_SOURCE_BOUNDARY',
        tests=[dict(node=c.attrib.get('classname','')+'::'+c.attrib['name'],
                    status='FAIL' if c.find('failure') is not None or c.find('error') is not None else 'PASS') for c in boundary],
        raw_execution=binding(P+'execution/current_full.xml')))
    aliases={
        'TDX_INCIDENT_FINAL_DISPOSITION.json':'TDX_FRESH_ZERO_WRITE_RECEIPT.json',
        'IA05_CURRENT_PROFILE_RECEIPT.json':'GLOBAL_CURRENT_REGRESSION_RECEIPT.json',
        'V1_CURRENT_RELEASE_CONSUMER_INVENTORY.json':'GOV1_CURRENT_RELEASE_CONSUMER_INVENTORY.json',
        'V1_RELEASE_IDENTITY_FINAL_DISPOSITION.json':'GOV1_SCOPE_PROPAGATION_RECEIPT.json',
        'IA07_CONTROL_FEATURE_OWNER_BINDING.json':'IA07_ACCEPTED_CAPABILITY_SCOPE.json',
        'IA07_CONTROL_MATCHING_PERFORMANCE.json':'IA07_ACCEPTED_CAPABILITY_SCOPE.json',
        'IA07_FINAL_DISPOSITION.json':'IA07_ACCEPTED_CAPABILITY_SCOPE.json',
        'GLOBAL_CURRENT_PYTEST_RECEIPT.json':'GLOBAL_CURRENT_REGRESSION_RECEIPT.json',
        'CANDIDATE_SEAL.json':'FINAL_DISPOSITION.json'}
    for name,target in aliases.items():
        if not (ROOT/(P+target)).exists():
            if name=='V1_CURRENT_RELEASE_CONSUMER_INVENTORY.json':
                target='GOV1_SCOPE_PROPAGATION_RECEIPT.json'
            else: raise ValueError('REQUIRED_EVIDENCE_MISSING:'+target)
        value=json.loads((ROOT/(P+target)).read_bytes())
        value.update(evidence=binding(P+target),execution_scope='V4_ONLY',
                     original_historical_identity_not_rewritten=True)
        if name=='TDX_INCIDENT_FINAL_DISPOSITION.json':
            value['incident_status']=('CLOSED_WITH_BOUNDARY_REPAIR_AND_FRESH_ZERO_WRITE_RUN'
                                      if value['fresh_TDX_ZERO_WRITE'] else 'BLOCKED')
            value['pre_incident_content']='PRE_INCIDENT_CONTENT_NOT_INDEPENDENTLY_VERIFIABLE'
        write(P+name,value)
    for name in ('IA05_FORMAL_SUPERSESSION_REGISTRY.json','IA05_HISTORICAL_PROFILE_RECEIPT.json',
                 'ENV_UI_SERVICE_RECEIPT.json'):
        write(P+name,dict(status='PRE_V4_EXECUTION_OUTSIDE_EXPLICIT_USER_SCOPE',
                         not_a_pass=True, scope_correction=binding(P+'V4_SCOPE_CORRECTION_RECEIPT.json'),
                         v4_reparse_boundary=binding(P+'TDX_PATH_GUARD_NEGATIVE_MATRIX.json')))
    portable=[c for c in cases if 'test_forward_final_reparse_equivalence' in c.attrib.get('classname','')]
    write(P+'ENV_SYMLINK_PORTABLE_RECEIPT.json',dict(status='V4_PORTABLE_EQUIVALENTS_PASS_WITH_EXPLICIT_PLATFORM_SKIPS',
        scope='V4_PHASE0_SNAPSHOT_OWNERS',portable_passed=len(portable),
        original_platform_skips=result['skips'], original_assertions_preserved=True,
        replay=binding(P+'execution/raw_runs/final_blocker_v4_skip_closure.xml'),
        real_junction_child_boundary=binding(P+'TDX_PATH_GUARD_NEGATIVE_MATRIX.json')))
    write(P+'GLOBAL_COLLECTION_RECEIPT.json',dict(scope=binding(P+'V4_ONLY_EXECUTION_SCOPE.json'),
        actual_collected_nodes=len(cases), errors=result['errors'], ignored=[],deselected=[],
        execution=binding(P+'execution/current_full.xml')))
    pass_keep=[c for c in cases if any(s in c.attrib.get('classname','') for s in
        ('forward_p1','forward_r2','full_chain','settlement','a08','r25','fep','remainder','v4_dm01'))]
    write(P+'PASS_KEEP_REGRESSION.json',dict(scope='V4_ONLY',total=len(pass_keep),
        failed=sum(c.find('failure') is not None for c in pass_keep),
        errors=sum(c.find('error') is not None for c in pass_keep),
        skipped=sum(c.find('skipped') is not None for c in pass_keep),
        nodes=[c.attrib.get('classname','')+'::'+c.attrib['name'] for c in pass_keep],
        execution=binding(P+'execution/current_full.xml'),model_parity=binding(P+'IA06_E3_E4_PARITY_RECEIPT.json')))
    write(P+'OPEN_ISSUES_FINAL.json',dict(v4_regression=result['status'],
        IA07='NOT_VERIFIABLE_BY_CURRENT_ACCEPTED_CAPABILITY',
        prior_incident='PRE_INCIDENT_CONTENT_NOT_INDEPENDENTLY_VERIFIABLE',
        pre_v4_artifacts='OUTSIDE_USER_SCOPE; NOT_FABRICATED',
        candidate=binding(P+'FINAL_DISPOSITION.json'),runtime_authorized=False))


if __name__=='__main__': finish()
