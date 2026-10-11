from pathlib import Path
import json,hashlib,os,subprocess
ROOT=Path('G:/codex work/大A交易');BASE=Path('G:/codex_tmp/full_system_repair_r3_239fb9b5');OUT=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):
    p=OUT/name;t=p.with_suffix('.tmp');raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode() if not isinstance(value,bytes) else value;t.write_bytes(raw);os.replace(t,p)
files=['src/adjustment/tdx_adjustment_v0_3.py','config/tdx_affine_qfq_v0_3_exact_rational.json','tests/test_audit_repair_adjustment_r3.py']
for name in files:
    p=ROOT/name;p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
for name in ('a4_final_junit.xml','a4_b2_final_junit.xml','a4_final.log','a4_recovery.log','a4_core.log','a4_ranks.log'):
    write(name,(BASE/name).read_bytes().replace(b'\r\n',b'\n'))
recompute=json.loads((OUT/'A4_CANDIDATE_RECOMPUTE.json').read_bytes());core=json.loads((OUT/'A4_B2_CORE_SENSITIVITY.json').read_bytes());ranks=json.loads((OUT/'A4_B2_RPS_SENSITIVITY.json').read_bytes())
write('A4_REPAIR_RESULT.json',dict(contract_id='TDX_AFFINE_QFQ_V0_3_EXACT_RATIONAL',base_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),issue='FA-016',source_bindings=[dict(path=n,sha256=sha(ROOT/n)) for n in files],legacy_engine=dict(path='src/adjustment/tdx_adjustment.py',sha256=sha(ROOT/'src/adjustment/tdx_adjustment.py'),byte_preserved=True,reason='Accepted policy binds legacy SHA; algorithm upgrades not granted in that lane'),evidence=['A4_CANDIDATE_RECOMPUTE.json','A4_CONSUMER_IMPACT.json','A4_B2_CORE_SENSITIVITY.json','A4_B2_RPS_SENSITIVITY.json','a4_final_junit.xml','a4_b2_final_junit.xml'],candidate_price_acceptance='PASS: 5224 stocks / 2162962 bars / 8636512 QFQ cells / zero independent rational-oracle mismatches / all 7 stocks 16 counterexamples corrected',core_sensitivity=dict(compared_fields=core['counts']['compared_fields'],security_dates=core['counts']['security_dates'],changed_cells=len(core['deltas']),current_five_dates_changed=any(r['changed_fields'] for r in core['current_five_dates'])),rank_sensitivity=dict(cases=len(ranks['cases']),changed_rows=sum(r['rank_changed_count'] for r in ranks['cases']),population='Endpoint-valid current-member reconstruction; not legal historical PIT'),consumer_modules=56,full_consumer_acceptance='OPEN: exact transport and full dated Profile/Structure/D0D1D2/Focus/Forward consumer delta/admission; no grant inferred',acceptance='EXACT_NUMERIC_CANDIDATE_PASS_WITH_CONSUMER_GATES_OPEN',production_loaded=False,next='Register v0.3 exact coefficient transport and producer identity; independently review all consumer deltas under legal prior/date population; never overwrite accepted Owner'))
ledger=json.loads((OUT/'EFFECTIVE_AUDIT_ITEMS_R3.json').read_bytes())
for row in ledger['issues']:
    if row.get('audit_item_id',row.get('id'))=='FA-016':row.update(status='EXACT_NUMERIC_CANDIDATE_PASS_CONSUMER_GATES_OPEN',repair_evidence='A4_REPAIR_RESULT.json',effective_location=['src/adjustment/tdx_adjustment.py','src/adjustment/tdx_adjustment_v0_3.py'])
write('EFFECTIVE_AUDIT_ITEMS_R3.json',ledger)
report=OUT/'REPAIR_REPORT_R3.md';write('REPAIR_REPORT_R3.md',(report.read_text(encoding='utf8')+'''\n## A4 / B2 复权消费影响

新增 opt-in v0.3 精确有理数复权：逐事件复合后一次整分 HALF_UP，正负 tie 不依赖 Decimal 上下文。既有 v0.2 受已接受源码 SHA 约束，保持原字节；正式 consumers 未切换。25项最终测试通过，含7股16格及非tie多事件；另50项 FIRST/ANY/FEP scoped检查通过。

全股隔离候选：5,224股、2,162,962根、8,636,512个可用QFQ格，逐事件独立算法零不一致；7股16格全部订正。候选70,684,709字节位于G临时工程根并绑定SHA，旧Owner未覆盖。

报告编排先后出现字段名及编码名错误，完整计算第二次已通过两条全量数值断言后才在消费索引报告出错；恢复从已保存候选逐行核对原始数值、可用性、计数、16差异。保留完整失败日志，不把恢复用时冒充全量重算耗时。

影响不能忽略：7股在2,547个证券日期的39个compute_core输出共99,333次比较，1,081个历史字段值变化，涉及均线/ATR/收益/波动/位置等28字段；五个现行冻结日期这7股Core值没有变化。历史16个收益日期窗口在全截面敏感性计算产生845条rank变化，分母仅为当前成员重建且两端可用的股票，不能写成合法历史PIT分母。56个价格/系数消费者已列索引；完整Profile/Structure/D0D1D2/Focus/Forward输出及精确transport准入仍OPEN。因此FA-016仅数值候选通过，未关闭正式消费门。
''').encode())
for name in ('a4_candidate.py','a4_recover_report.py','a4_core_deltas.py','a4_rank_sensitivity.py','close_a4.py'):
    write('reproduce/'+name,(BASE/name).read_bytes())
assert sha(ROOT/'src/adjustment/tdx_adjustment.py')==hashlib.sha256(subprocess.check_output(['git','show','239fb9b5:src/adjustment/tdx_adjustment.py'],cwd=ROOT)).hexdigest()
print('A4_EXACT_CANDIDATE_CLOSED_WITH_CONSUMER_GATES')
