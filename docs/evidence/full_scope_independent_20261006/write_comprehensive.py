"""Cross-model synthesis follows the fixed independent findings."""
from pathlib import Path
import json
from write_reports import STAGES,ISSUES,HEAD,BASE,ROOT,EVIDENCE,AUDITS,atomic,link

ONLINE={
'V4-00A':('§5','PASS','基线冻结接受可保留；本轮默认全仓收集失败和IA-09测试隔离问题是独立当前验证债务，不推翻Phase0历史范围。'),
'V4-00B':('§5','PASS_REQUIRED_SCOPE','一致：日期有效身份/knowledge time结构成立；全历史AS_RECORDED与法律实体类型不自动完整。'),
'V4-00C':('§5','PASS','一致：publication/revision/namespace工程范围成立；current owner实际读取通过，不只依赖旧PASS文本。'),
'V4-00D':('§5','PASS','一致：输入根只读、有界下载/输出分离；本轮未重新下载全量TDX包。'),
'V4-00E':('§5','PASS_REQUIRED_SCOPE；前次affine缺口已关闭','原Affine非法系数硬化可保留，但“已修复”不覆盖IA-01内部缺口/端点隔离，也不覆盖IA-02板块adapter契合。不能据旧修复概括全部Forward正确。'),
'V4-00F':('§5','PASS_CONTRACT','一致：BaoStock只可选补充，strict-binding不足保持降级，不成为Core总前置。'),
'V4-00G':('§5','PASS','一致：版本contract/AST/producer/窗口框架成立；IA-01同时说明框架存在与消费公式吻合须分别验证。'),
'V4-00H':('§5','PASS','历史rollback/performance合同接受保留；本轮没有当前全市场整链负载实证，不能将旧runtime row count=0 baseline外推为当前SLA。'),
'V4-01':('§6','FULL_PASS_REQUIRED_SCOPE','一致：Bootstrap工程接受可保留；线上引用4035729行/786 sessions是历史外审数据，不是本轮又做了一次raw全扫。'),
'V4-02':('§7','PASS_REQUIRED_SCOPE_WITH_EXPLICIT_DEGRADATION','Canonical核心和9/30 accepted链结论一致；historical first availability不可补造。另IA-10证实DM01直接CLI缺repo-root bootstrap，底层公式接受不代表独立脚本入口可运行。'),
'V4-03':('§8','PASS_AMENDED_SCOPE','一致：Sector full-market责任移到08有正式amendment，不是主架构偏离。'),
'V4-04':('§9','FULL_PASS_REQUIRED_SCOPE','一致：Pure-Core分层和全市场profile已实现；规则分类不等于策略收益已验证。'),
'V4-05':('§10','SCOPED_DEGRADED_PASS','一致：Replay Gate A可在受限capability内成立；历史PIT effectiveness未授权。'),
'V4-06':('§11','PASS_OPTIONAL_SCOPED','一致：Supplemental缺失不阻断07；严格源绑定不足只影响对应补充能力。'),
'V4-07':('§12','ENGINEERING_PASS_SCOPED','一致：BaseSeed Pure-Core whitelist与unknown propagation；真实prior-RPS bootstrap限制仍保留。'),
'V4-08':('§13','ENGINEERING_PASS_CAPABILITY_SCOPED；full surface未完成','一致；进一步区分Amount-A producer工程接受、H21正式consumer和historical consumer。producer接受不关闭A04_H21/HISTORICAL；IA-02是其Forward消费专项，不否定当日Rotation Core。'),
'V4-09':('§14','ALGORITHM_ENGINEERING PASS；A08_CURRENT_RUNTIME排除','版本更新：本轮包含当前A08 V4/active V6传播，ACCEPTED_SCOPED仅工程Shadow依赖；production_blocking仍true，permission=false。线上排除是其当时scope，不能沿用为本轮排除。'),
'V4-10':('§15','FULL_PASS_STAGE_PURPOSE','一致：本stage要求interface/独立向量；完整DAG在14验收。不因旧10 Head NOT_IMPLEMENTED判全stage失败。'),
'V4-11':('§16','ENGINEERING_PASS_CAPABILITY_SCOPED','一致：LAUNCH/RECOVERY正式，另两scenario diagnostic及历史event debt不能误写为四场景全正式。'),
'V4-12':('§17','ENGINEERING_PASS_CAPABILITY_SCOPED','一致：multi-anchor/coordinate/episode/counters实现；真实owner/historical capability受限，历史validator路由债务独立记录。'),
'V4-13':('§18','ENGINEERING_PASS_CAPABILITY_SCOPED','一致：target exclusion在LOO重算之前；current membership与historical membership authority分离。'),
'V4-14':('§19','ENGINEERING_REPLAY_PASS；HISTORICAL_PIT_EFFECTIVENESS未授权','一致：DAG输入绑定、时序和revision replay是工程证据；不是全历史PIT，也不是M14在线增强模块。'),
'V4-15':('§20','ENGINEERING PASS；REAL_MATURITY PENDING；前次修复已通过','实质修订：IA-01/02当前Forward局部REPAIR_REQUIRED；IA-03/04分别为通用API状态和输入边界P2。真实成熟待积累仍正确，但并非全部剩余问题只需等市场时间。'),
'V4-16':('§27','ENGINEERING_READY；stage final未完成','真实grant/样本0结论一致；“工程ready”需缩限：durable worker使用IA-01路径，Sector开放前还需IA-02。不能直接从前次hardening PASS推断当前全Forward范围ready。'),
'V4-17':('§28','ENGINEERING_EXTERNALLY_ACCEPTED；真实end-to-end pending','一致：只读context token/GET/SQLite read-only工程保留；accepted readback为空时无连接、不以目录最新simulation替代。'),
'V4-17G':('§29','NOT_GRANTED / REAL_GATE_PENDING','一致：尚无真实session，不可用reconstructed历史数凑stable/Forward门。'),
'V4-18':('§30','CONTRACT_DESIGN_PASS；runtime未开始','一致：V1_3设计-only，六接口未实现；独立inventory适用226个声明全部覆盖。R23历史工程16表不属active migration，不能报漏表；真正runtime前仍需最终successor exact外审。'),
'V4-19':('§31','CONTRACT_DESIGN_PASS；cutover未实现','一致：capability permissions/writer/CAS/rollback未执行，Focus源未切。'),
'V4-20':('§32','CONTRACT_DESIGN_PASS；default UI cutover未开始','一致：模块逐项permission和mixed routing，当前默认Legacy；不是全局V4生产页。'),
'V4-21':('§33','CONTRACT_DESIGN_PASS；真实累计未开始','一致：native ACCEPTED_ON_TIME归owner，evaluable独立投影；真实继续观察无writer授权。'),
'V4-22':('§34','AUDIT_FRAMEWORK_PASS；FINAL NOT_GRANTED','一致：closure evidence/item authority/schema加固是合同审计；真实前置未完成，且本轮新项未关闭，不能签最终验收。'),
'FEP-E1':('§22','ENGINEERING_ACCEPTED；47/47 mapping','一致：owner字段copy、完整分母/as-of三时间；本轮PG因fixture/DSN不足skip，限制重新验收，真实label和FIRST_OBSERVED尚无。'),
'FEP-E2':('§23','ENGINEERING_ACCEPTED_CAPABILITY_SCOPED','一致：FIRST_PREWATCH×ABS_RETURN:T1工程范围；Fraction日期平权、固定backoff/support。pooled/REENTRY/NEW_CONFIRMED不自动授权。'),
'FEP-E3':('§24','MODEL_ENGINEERING_PASS；MODEL_EFFECTIVENESS NO','一致：split/purge/train-only preprocess/calibration/OOD工程；有效性/OOS不是PASS，NO_INCREMENT/弱coverage应如实保留。'),
'FEP-E4':('§25','OPTIONAL ENGINEERING_PASS；vs E2 NO_INCREMENT','一致：challenger实现可通过而不成为Champion；Outer为见过的诊断复用，不能声称new real OOS。'),
'FEP-E5':('§26','ENGINEERING_COMPLETE_CURRENT_SCOPE；production/display/priority未授权','一致：canonical reconstruction authority、signal binding、slot/deployment/CAS与legacy isolation保留。上游IA-01/02有修复需要，不可将受影响outcome作为有效标签；本轮真实PG验收也不全。'),
}

def main():
    assert set(ONLINE)=={s[0] for s in STAGES}
    test_section=(EVIDENCE/'TEST_RESULTS.md').read_text(encoding='utf8')
    rows='\n'.join(f"| {s[0]} | {ONLINE[s[0]][1]} | {s[2]} | {'修订' if s[0] in ('V4-00E','V4-15','V4-16') else '版本更新' if s[0]=='V4-09' else '一致/补充边界'} |" for s in STAGES)
    text=f'''# 阶段00–22及FEP线上×独立审计综合报告 R1

日期：2026-10-06（Asia/Shanghai）。独立审计HEAD：`{HEAD}`。线上报告HEAD：`b7ca247745976aa390387a0701601b00ac0d8498`。分支：`codex/v4-system-reform`。

## 1. 综合结论

**主架构总体遵循最新设计，历史00–15和FEP的限定工程接受可以保留；当前项目不能签“全能力完成 / 全仓release PASS / V4-22最终PASS”。线上报告“没有发现新的P0/P1代码合同偏离”需修订：本轮复现2项Forward P1，并证实独立的旧测试隔离P1；阶段15受影响实现需要修复，不能将所有剩余问题归为等待真实交易日。**

全阶段覆盖包括00A–H、01–22、17G及FEP E1–E5，共36个审查单元。阶段16真实grant仍未授予、实际样本0；17无真实readback；18–22多数是合同设计完成、真实执行/切换/累计/最终接受未完成。FEP没有real OOS/Champion/display/priority/production授权。没有新证实P0，不等于穷尽证明所有P0不存在。

本轮交付为两份审计MD、逐阶段/逐问题证据及机器登记；不修业务代码，不产生新的accepted head或权限。Git发布是文档/证据交付，不是外部接受或下一阶段授权。

## 2. 两份审计的关系、设计基线与版本差异

独立报告：{link('docs/audits/V4_00_22_FEP_INDEPENDENT_FULL_SCOPE_AUDIT_R1_20261006.md')}。线上报告原字节归档：{link('docs/evidence/full_scope_independent_20261006/online_model_report_input.md')}；其SHA256=`7db50099464314b37c0c000c68dace1a62253b4e4c1058d43081f673dfe25993`，43204字节。用户附件及其中恢复/修复建议只作为审计证据，**不是本次用户授权执行的指令**。

主设计：{link(BASE)}，ID=`DA-MSR-V4.2.2-CODEX-REV4-FEP-R2`，SHA256=`203ff46075b4039d1e2d45d54fd76ce09509535739cd6aaef4dc394de1015205`，224998字节。FEP同时遵循§90及归档R2设计/正式successors。线上声称Drive与repo逐字一致，本轮核验本地设计身份，未独立重做Drive文本比较；不把他方Drive检验声明升级为本轮实证。

独立代码/合同审查与反例先形成，再完整读取线上报告逐stage综合。此报告没有简单按线上PASS投票；同scope结论按当前证据解释，不同版本/工程与真实权限分层。

线上排除了正在执行的A08。本轮HEAD已含后续A08传播、外审和Git发布：current A08 scoped工程接受保留，V4 Current Audit Head仍为治理传播candidate而非通用production grant；active V6依赖已更新但grant=null/runtime禁用/真实样本0。这个差异是版本更新，不能说线上当时判错。反之，IA-01/02涉及的`v4_15_settlement.py`、`v4_15_settlement_successor.py`及冻结Forward contract在两HEAD中**字节完全相同**，证据{link('docs/evidence/full_scope_independent_20261006/cross_model_code_identity.json')}：它们是当时已有但线上未检出的实现问题，不能归因于后续A08改动。

## 3. 综合判定规则

| 结果层 | 可支持的声明 | 不可推导的声明 |
|---|---|---|
| 历史外审接受 / PASS_KEEP | 当时冻结字节、合同、capability的接受保留 | 当前所有新源码自动获授权 |
| 本轮工程审查通过/保留 | 已审核心公式、结构、输入边界与合同相符；未发现新证伪 | 穷尽所有输入空间、全市场性能、生产ready |
| DEGRADED / SCOPED | 设计允许UNKNOWN/NOT_IMPLEMENTED和受限consumer | 全能力完成或可填0/补造历史 |
| REPAIR_REQUIRED | 独立反例已证实具体公式/集成偏离 | 无关阶段全部重开 |
| CONTRACT_DESIGN_ONLY | schema/interface/反例/权限设计范围可保留 | runtime/replay/cutover已实现 |
| REAL_GATE_PENDING / NOT_GRANTED | 时间/样本/真实source/权限不足，正常fail-closed | 真实工程执行成功或阶段最终PASS |
| 测试债务/环境不足 | 当前验证证据不完整或失败 | 自动否定所有历史算法或静默忽略得全绿 |

## 4. 36个审查单元的线上、独立与综合矩阵

| 阶段 | 线上结果（原范围） | 独立/综合结果 | 对照性质 |
|---|---|---|---|
{rows}

## 5. 逐阶段综合审计：代码、算法、通过原因和不通过原因
'''
    for s in STAGES:
        sec,verdict,decision=ONLINE[s[0]]
        text+=f"\n### {s[0]} · {s[1]}\n\n线上报告{sec}：`{verdict}`。本轮独立/综合：**{s[2]}**。\n\n设计合同：{s[3]}\n\n核心代码/结构证据："+'；'.join(link(p) for p in s[4])+f"。\n\n算法与数据结构结果：{s[5]}\n\n通过/保留依据：{s[6]}\n\n未通过/未完整的原因：{s[7]}\n\n综合裁决及差异解释：{decision}\n\n设计偏离与下一步：{s[8]}\n"
    text+='''
## 6. 综合问题清单与独立关闭标准

下列10项独立于stage历史gate登记为OPEN_AUDIT_ONLY；原Current Audit canonical items照旧保留，本轮没有覆盖/关闭它们。不同性质不能混为“10个新算法bug”。完整反例与源行号见独立报告§6及audit_items.json。

| ID | 优先级/类型 | scope / 具体问题 | 综合处置与接受条件 |
|---|---|---|---|
'''
    for i in ISSUES:
        text+=f"| {i['id']} | {i['severity']} / {i['kind']} | {i['scope']}；{i['title']} | {i['acceptance']} |\n"
    text+=f'''
### 6.1 对线上“七项已修复”及“无新P1”的精确修订

**IA-01（Stock Forward）**：T0基准10、末端close11且identity/adjustment/T0 basis均验证，内部日无换基证明时，端点收益应独立保留`R_N=0.1`，MFE/MAE/MDD不可评估。当前successor先遍历全部rows验证，内部失败返回整份`ADJUSTMENT_UNKNOWN / R_N=null`。冻结contract的`ENDPOINT_RETURN_INDEPENDENT_IF_VERIFIED`与设计§46A提供独立oracle；这是额外丢弃合法端点收益，而非设计允许的“整段收益不可用”。worker实际调用该successor，但真实activation未开启，未证明已有真实污染。

**IA-02（Sector Forward）**：等初始权重两个成员10→11，成员端点均有效，Sector subject basket应有0.1绝对收益。旧settle聚合行未带successor必需的adjustment_identity，因此新runtime整段null；回退旧runtime虽返回0.1，却把basket close写成high/low并输出MFE_N/MAE_N，违反§49A.3仅允许板块MFE_CLOSE/MAE_CLOSE的字段语义。当前PURE_CORE_STOCK并未授权Sector，故严重级为对应能力P1，不夸大为全部Stock流P0。

两项均在已复用的历史settle和additive validator拼接处出现。原“非法affine拒绝”和“benchmark surface补齐”验收可保留，但它们不覆盖内部缺口/终点独立性与Sector生成行schema一致性。历史接受不能抹掉本轮精确证伪，也不因此全局重开00–15。

**IA-03/04**：PENDING→DUE同源key复用已复现，限定通用API，durable worker只入队due所以尚未证明其真实故障；负实际价被标OBSERVED已复现，但正式upstream raw producer有校验，本轮未证明该输入可从正式链传来。分别P2，避免人为升为P0/P1。

**IA-09（测试隔离）**：旧M12浏览器fixture实际启动工作区DB，serve的恢复逻辑可能更新真实jobs/重跑任务。本轮发现后中止。没有前DB精确指纹，不能证明零DB写，也没有证明发生具体重发布；tracked业务diff为空只支持代码未改。此项独立于V4金融算法接受，新的全仓复跑须先使用确认过的disposable环境。

**IA-10（独立CLI）**：daily脚本只加入src，而kernel导入scripts包需repo root。独立只读--help探针在继承环境exit1，显式root+src PYTHONPATH后exit0；确认入口bootstrap缺口，但没有执行capture/build/promotion，不否定底层九组件公式或data head。应明确launcher合同，不能将此条误归为缺第三方sklearn。

独立反例：{link('docs/evidence/full_scope_independent_20261006/semantic_probes.py')}与{link('docs/evidence/full_scope_independent_20261006/semantic_probes.json')}；都是SYNTHETIC_AUDIT_COUNTEREXAMPLES，不计REAL/PIT_OBSERVED/maturity/OOS样本。

### 6.2 仍开放的原canonical能力与生产债务

- A04_H21_CONSUMER=ACCUMULATION_CONTINUES，A04_HISTORICAL_AMOUNT_A=BLOCKED_AFFECTED_SCOPE；producer/consumer/历史能力分别验收。
- A03继续真实forward积累，A07与HISTORICAL_PIT_EFFECTIVENESS保留永久/预capture能力限制。
- R3C suspension/adjustment coordinates/D2 prior authenticity/event UNKNOWN、Git portability继续OPEN_EXTERNAL_REAUDIT。
- V4_12_REAL_OWNER、V4_13_REAL_OWNER、15真实cohort maturity和真实matured accepted-source settlement是NONBLOCKING_VALIDATION_DEBT；nonblocking不等于已经取得结果。
- A08 current scoped工程接受已传播，但production_blocking/permission限制仍有效。

这些不是本轮新增P1，也不被上面的10项登记替代。关闭须指定scope、exact authority、独立证据和acceptance，不能只由某stage tests通过或push自动关闭。

## 7. 数据结构、合同、来源与性能专项综合

Foundation 001–009保存namespace/publication/revision/prior session/source guards；010–012为lifecycle/date-valid identity；013–014 supplemental；015 Seed；016–020 Sector/Rotation；021/025 PREWATCH；022–024 State；026–027 Confirmation；028–033 FEP。FEP reconstruction不借live publication authority，signal registry有FK及语义guard，旧engineering ledger只诊断；真实Shadow以R24/queue v2/integrity v2 SQLite独立存储。静态schema吻合不证明本轮实际生产库部署。

18最新版namespace matrix在适用SQL集合下226项全部覆盖。初始广搜包含R23旧simulation schema得到242项；其中16历史表不是active migration源，已按正确范围重核验，不报新漏表。证据{link('docs/evidence/full_scope_independent_20261006/migration_namespace_coverage.json')}。

4797条path/SHA/byte绑定中4777当前literal匹配、20旧引用与工作区不同；20对应15个独立身份都能找到Git原blob，当前CurrentStageAuthority及PREWATCH读取实际PASS。不能将历史差异判为active头损坏；也不能把Git可找回等同于所有旧CLI当前可运行。IA-08与已有Git/production再审项追踪明确版本路由。

M14在线增强不是V4-14 Replay。direct API仅请求时LATEST，collector capture禁用、能力gate三项persist=false，有界HTTP与按源UNAVAILABLE；现路径不落raw/row/batch或改local snapshot身份。旧batch reader不在当前direct API调用链。5项针对性测试通过，本轮不声称在线源重新实测可用。

FEP E1逐row扫描population权重、E3逐row扫描later集合及Forward逐signal controls复算存在二次复杂度风险；旧baseline runtime row count=0不支持当前全市场SLA。IA-07为性能证据债务，未测得timeout，不能写成已发生性能故障。

## 8. 本轮测试、实际执行与未完成验证

{test_section}

## 9. 按证据排列的后续工作

| 次序 | 工作 | 完成依据 | 当前本报告是否授权执行 |
|---|---|---|---|
| 1 | 独立确认IA-01/02；冻结Stock路径隔离及Sector篮子successor修复范围 | 独立oracle、持久化worker/readback向量、exact新工件外审；历史字节保留 | 仅提供审计结论，未执行修复 |
| 2 | 独立处置IA-03/04及已有Forward向量/owner验证债务 | 状态revision与真实source边界证据，不用同实现做oracle | 未执行 |
| 3 | 先修测试环境隔离，再分类全仓收集/失败与PG fresh-upgrade验证 | disposable根/DB、安全前后保护证据、完整未隐瞒的结果；不恢复retired hot-rank capture | 未执行隔离改造/业务修复 |
| 4 | 复核最新版R25 packet与对应能力consumer/grant | 有效daily input、冻结权限、受影响实现关闭、current exact acceptance | 未授予First Real Shadow |
| 5 | 真实16 publication→17 readback→17G按capability稳定/Forward | 真实市场session、成熟outcome/rollback回执，不以replay凑数 | NOT_GRANTED |
| 6 | 18实际migration replay→19 Focus→20默认UI | 实现六接口/生产writer、幂等/reconcile/CAS/rollback、范围permission与独立外审 | NOT_GRANTED |
| 7 | 21持续真实积累→22最终独立审计；FEP独立真实FIRST_OBSERVED/OOS | canonical真实ledger、完整分母、独立封闭审计；FEP仍非主链总前置 | NOT_GRANTED |

线上提出“不要全局重做00–15、不要补造历史、未来按真实gate推进”的方向保留。需要修订的是“当前只剩真实时间/执行门”：本轮Forward具体实现问题和测试/DB证据也必须按受影响scope先处理，不能原样跳至First Real Shadow。

## 10. 审计交付验收与证明边界

本次阶段合同：READ_ONLY_CODE_ALGORITHM_CONTRACT_REVIEW_AND_SYNTHETIC_COUNTEREXAMPLES_V1。结果：36单元审计及交叉综合已交付；10项独立问题登记完成。项目release接受：**NOT_ACCEPTED_AS_FULL_RELEASE**；V4-22最终接受：**NOT_GRANTED**。下一阶段：对新项独立复核/范围修复和安全验证环境建设，须新的明确任务推进。

完整文件清单/语法覆盖不代表2819文件全部逐行或所有数据全量数学证明。本轮未重新全扫数百万TDX日线、重新抓在线源、测全市场实时负载或执行真实migration/恢复/cutover；PG未跑/skip/error不能写PASS。测试中旧真实库服务启动的局限按IA-09公开记录，不包装成纯隔离全仓成功。

Git交付只提交本轮2份MD及独立证据目录，保留起始用户FEP/design/artifacts/tmp未跟踪工作。发布记录见{link('docs/evidence/full_scope_independent_20261006/DELIVERY.json')}；push不等于外部接受或阶段权限。
'''
    atomic(AUDITS/'V4_00_22_FEP_COMPREHENSIVE_CROSS_MODEL_AUDIT_R1_20261006.md',text.encode('utf8'))
    atomic(EVIDENCE/'cross_model_stage_decisions.json',(json.dumps(dict(independent_head=HEAD,online_head='b7ca247745976aa390387a0701601b00ac0d8498',authority='AUDIT_SYNTHESIS_ONLY_NO_PERMISSION',stage_count=len(STAGES),decisions={k:dict(online_section=v[0],online_verdict=v[1],synthesis=v[2]) for k,v in ONLINE.items()}),ensure_ascii=False,indent=2)+'\n').encode('utf8'))

if __name__=='__main__':main()
