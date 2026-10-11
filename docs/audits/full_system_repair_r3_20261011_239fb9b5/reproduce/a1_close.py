exec(compile(Path('G:/codex_tmp/full_system_repair_r3_239fb9b5/prepare.py').read_text(encoding='utf8').split('from workbench_analysis.operational_successor_v1 import accepted_api')[0],'prepare-prefix','exec'))
import shutil
for name in ('a1_junit.xml','a1_initial_fixture_failure.xml'):
    write(name,Path('G:/codex_tmp/full_system_repair_r3_239fb9b5',name).read_bytes())
effective=json.loads((OUT/'EFFECTIVE_AUDIT_ITEMS_R3.json').read_bytes())
fa12=next(r for r in effective['issues'] if r['audit_item_id']=='FA-012')
assert all((ROOT/p).is_file() for p in fa12['effective_location'])
for r in effective['issues']:
    if r.get('audit_item_id')=='FA-001':r.update(status='ENGINEERING_FIXED_EXTERNAL_PENDING',current_block='EXTERNAL_RECHECK_PENDING',repair_evidence='A1_REAL_FIVE_DAY_READBACK.json',disposition_contract='HOME_EVENT_SELECTION_R2')
write('EFFECTIVE_AUDIT_ITEMS_R3.json',effective)
write('A1_REPAIR_RESULT.json',dict(contract_id='HOME_EVENT_SELECTION_R2',issue='FA-001',source_sha256=sha(ROOT/'src/workbench_service/core_product_bff_r1.py'),test_sha256=sha(ROOT/'tests/test_audit_repair_home_r3.py'),evidence=['A1_REAL_FIVE_DAY_READBACK.json','a1_junit.xml'],initial_attempt='a1_initial_fixture_failure.xml: synthetic source ref omitted sha256, corrected fixture only',acceptance='ENGINEERING_PASS_EXTERNAL_PENDING',production_loaded=False,next='A2/A3/A4/A5/A6 and independent audit B'))
write('REPAIR_REPORT_R3.md',('''# 全系统修复与续审 R3

基线 `239fb9b545ac25305af02a645a77d82246cbb71a`，总状态 **AUDIT_INCOMPLETE**。

## AR2-E01 / A1

新有效问题视图逐条保留历史引用，FA-012 通过 effective_location 指向三个真实 Amount A 配套合同。R1/R2 原件及 SHA 保留在 STAGE_CONTRACT；程序读取 EFFECTIVE_AUDIT_ITEMS_R3.json。

首页按 INVALIDATED→EXITED→WEAKENED→UPGRADED→REENTERED→NEW 保留每实体首条，风险与净信息分母从同一选择结果计算。1,956 种非空有序子集通过；五个真实冻结运营日只读重放通过。真实源各日没有多事件类型实体，因此这是潜在缺陷修复，不宣称已发生线上事故。

首次测试夹具漏 source sha256，修正夹具后通过；保留首次失败原件。业务修复仅工程验收，生产进程未重启，不能声称已加载新代码。

## 后续批次

A2/A3/A4/A5/A6及 B 类继续独立执行。B4 不重复既有通过数值；H21仍缺20个合法PIT观察。C等待真实新交易日来源，D等待完整成熟/OOS，E实体Windows验收须另有明确授权。没有外部接受或生产Grant。
''').encode())
pointer='''# 全系统代码审计当前入口

当前修复与续审：**R3 / 2026-10-11 / AUDIT_INCOMPLETE**；执行基线 `239fb9b545ac25305af02a645a77d82246cbb71a`。

- [修复报告](full_system_repair_r3_20261011_239fb9b5/REPAIR_REPORT_R3.md)
- [有效问题视图（自动消费者入口）](full_system_repair_r3_20261011_239fb9b5/EFFECTIVE_AUDIT_ITEMS_R3.json)
- [本轮独立复审输入](full_system_repair_r3_20261011_239fb9b5/INDEPENDENT_REAUDIT_INPUT.md)
- [历史 R2 报告（字节保留）](full_system_audit_r2_20261011_58faf74e/V4_FULL_SYSTEM_CODE_AUDIT_CONTINUATION_REPORT_R2_20261011.md)

各批次工程结果见报告和独立 REPAIR_RESULT。正式PIT/H21/Cohort/FEP/Windows门未解除；提交和push不代签外部接受。
'''
p=ROOT/'docs/audits/FULL_SYSTEM_AUDIT_CURRENT.md';t=p.with_suffix('.tmp');t.write_bytes(pointer.encode());os.replace(t,p)
