from pathlib import Path
import re, json, hashlib, os, shutil, difflib, math

BASE=Path(__file__).parent
SRC=Path('D:/Users/lps/Desktop/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925.md')
OUT=SRC.with_name(SRC.stem+'_codex修改版.md')
LOG=SRC.with_name(SRC.stem+'_codex修改版_修改说明.md')
expected='AC86F92F9CFAA3547A0BA99959E749DA02F0FA7F9C0A1568AD95627DB0200B97'
sha=lambda b:hashlib.sha256(b).hexdigest().upper()
assert sha(SRC.read_bytes())==expected, 'source changed'
doc=(BASE/'draft.md').read_text(encoding='utf8')
original=SRC.read_text(encoding='utf-8-sig')
changes=json.loads((BASE/'changes.json').read_text(encoding='utf8'))
headings=re.findall(r'^#{1,6}\s+(\d+[A-Z]?\d*(?:\.[\dA-Z]+)*)(?=[.\s])',doc,re.M)
refs=re.findall(r'§\s*(\d+[A-Z]?\d*(?:\.[\dA-Z]+)*)',doc)
assert not set(refs)-set(headings)
assert len(headings)==len(set(headings))
fenced=False
for line in doc.splitlines():
    if line.startswith('```'):
        if fenced: assert line.strip()=='```', 'unexpected new fence within block'
        fenced=not fenced
assert not fenced
normative=doc.split('# 历史附录 D：')[0]
assert 'PIT_OBSERVED_FORWARD' not in normative
assert 'min_{i<j' not in doc
allowed={'V4-00'}|{f'V4-{i:02d}' for i in range(1,23)}|{f'V4-00{c}' for c in 'ABCDEFGH'}|{'V4-17G'}
assert set(re.findall(r'V4-\d{2}[A-Z]?',doc))<=allowed

# Numerical counterexamples are independent expected values, not implementation certification.
vectors=[]
for path,expected_value in [([100,110,120],0),([100,80,90],-.2),([100,120,90],-.25),([100,100],0),([100,90],-.1)]:
    result=min(p/max(path[:i+1])-1 for i,p in enumerate(path))
    assert math.isclose(result,expected_value,abs_tol=1e-12)
    vectors.append(f'MDD {path} → {expected_value:g}')
def rps(values):
    n=len(values)
    return [100*(sum(x<v for x in values)+.5*(sum(x==v for x in values)-1))/(n-1) for v in values]
assert rps([1,1,1])==[50,50,50]
assert rps([1,2,3])==[0,50,100]
assert rps([1,1,2])==[25,25,100]
assert math.isclose((2*50+10-4)/2,53)
assert math.isclose(((2*55+10-4)/2)-((2*50+10-4)/2),5)
vectors.extend(['RPS：全同分=50；升序=0/50/100；并列=25/25/100','affine：价格水平包含平移项，差值转换中平移抵消'])

data=doc.encode('utf8'); output_hash=sha(data)
def section_link(title):
    match=re.match(r'(\d+[A-Z]?\d*(?:\.[\dA-Z]+)*)',title)
    if match:
        pattern=r'^#{1,6}\s+'+re.escape(match.group(1))+r'(?=[.\s])'
        for n,line in enumerate(doc.splitlines(),1):
            if re.match(pattern,line): return f'[§{match.group(1)}](<{OUT.as_posix()}:{n}>)'
    return f'[文档](<{OUT.as_posix()}:1>)'

log=f'''# V4.2.2 codex修改版：修改说明与文档验收记录

日期：2026-09-25。本次工作为全文合同修订，直接在原文副本替换、合并和补充正文规则；不是只在末尾增加勘误。原件保持不变。

## 文件与范围

- [原文档](<{SRC.as_posix()}>)：{len(original.splitlines())} 行。
- [codex修改版](<{OUT.as_posix()}>)：{len(doc.splitlines())} 行，文档编号 `DA-MSR-V4.2.2-CODEX-REV1`。
- 原件 SHA256：`{expected}`。
- 修改版 SHA256：`{output_hash}`。
- 全文处理包含 {len(changes)} 组章节替换/补充，另有跨章字段、枚举、版本标识、引用及措辞统一。行数减少主要来自重复规则和冲突任务表合并，不表示仅检查了被替换的章节。

## 本次结论和适用边界

文档状态是 `DOCUMENT_REVISED / READY_FOR_BASELINE_AND_CONTRACT_WORK`。已将发现的合同冲突、公式错误、循环依赖和缺失处置规则写入正文，不把文档修订等同于代码已实现、真实数据通过或算法效果被证明。

本次补齐的趋势、压缩、流动性、风险、留存、状态迟滞、排序、对照匹配及切换样本等数值，是明确可审查的**工程候选规则**。它们会改变算法行为，不能当作纯文字勘误；需按§72注册参数和版本，再在首次消费阶段冻结机器合同、独立正反向向量及证据。用户未要求实际执行交易或改代码，本次没有执行这些动作。

真实源单位与复权事件、官方制度规则表、Legacy AST提取、历史身份/成员覆盖、性能预算、Amount A、Focus真实Forward等仍需独立证据。其约束已改为明确能力范围和对应阶段门，不能通过标注“已修订”自动关闭，也不应阻断无依赖的本地主流程。

## 上轮审计逐项处置

| 原审计项 | 修改位置及处置 |
|---|---|
| A01 同日反馈 | §13A/21A：B只读声明的当前纯Core事实与冻结历史；C与D不能回写B，Rotation独立状态机。 |
| A02 Core后置依赖 | §7.4/10A/10J–L/41F/87A：Core与补充字段分层，结构事件依赖整体后移V4-12。 |
| A03 Anchor换基 | §3B.6/41A0：价格水平仿射换基、差值只缩放，冻结原坐标；真实源样本仍须验证。 |
| A04 双时间PIT | §6A：有效时间、系统可见时间和实际消费manifest分开，晚到更正不冒充当时可见。 |
| A05 Supplemental污染 | §3/3A/9A/10I：TDX本地Core权威，BaoStock仅补充/交叉核验；turnover不改正式资格或排序。 |
| A06 合同不完整 | §10A0/10B–M/72/81.4/87A：具体窗口、比较、未知分支、参数与首次消费阶段门。 |
| A07 修订前驱 | §4.7/34A：固定上一会话实际revision，同日修订与跨日状态前驱分离。 |
| A08 Forward定义 | §45–49B：市场日horizon、MDD/MFE/MAE、到期缺失、冻结篮子和对照结算。 |
| A09 Shadow与真实观察 | §4.6/51A/52A：执行方式与证据身份正交，真实观察slot和原始样本不可事后重选。 |
| A10 降级门 | §52B/78：FULL/DEGRADED/BLOCKED携带能力scope，Optional不可全局阻断。 |
| A11 跨域审计 | §70A：Amount A等保留OPEN和独立接受条件，未关闭前限制正式消费者。 |
| A12 冗余Seed路径 | §14：Seed路径和annotation分离，不重复计作独立支持。 |
| B01 多套当前规范 | §3/4.6/7.4/10B–M/78/87A/附录B：统一权威、枚举、字段producer和唯一阶段表。 |
| B02 回撤公式错误 | §46A：按包含T0的滚动峰值求非正回撤；上涨路径=0，排除T0盘中高低点。 |
| B03 切换等待未交付结算器 | §46/52A/78：V4-15交付结算器，V4-16运行，V4-21继续积累。 |
| B04 冻结门自锁 | §10A0/72/81.4：全局框架先行，每模块在首次消费前冻结，不要求未来模块先实现。 |
| B05 状态早于Detector | §13A/31/77B：Confirmation与Structure事实先算，State后归约，Event最后投影。 |
| B06 事件修订及前驱漂移 | §4.7/45A/77B：逻辑事件和revision observation分层，原始enrollment保留，撤销只影响对应当前投影。 |
| B07 查询不能证明实际消费 | §6A/51A：实际消费manifest、knowledge time、观察deadline共同约束。 |
| B08–B10 | 按本轮审计原始条目标题及逐章变更表核对；相关窗口、独立审计权限、统计及降级规则均直接修改正文，不沿用原文自动CLOSED声明。 |

## 全文新增修订重点

1. 事实表不预填下游Seed/状态结果；数值、质量、原因和来源分列，证券代码复用建立不同实体身份。
2. 停牌、数据缺口、退市和未知明确区分；Core连续市场窗口、turnover历史窗口、Forward市场horizon分别定义。
3. 板块变化使用共同成员比较，披露覆盖；LOO完整重算历史和当前，成员变动不能冒充扩散改善。
4. 结构新Anchor最早下日评估，旧episode失效条件冻结；日线不能臆测盘中先后顺序。
5. 同日硬失效优先于确认；未知不算FALSE，不新增或错误退出样本；重入建立新episode，旧结算继续。
6. 风险变化不被当前eligible筛选隐藏；排序枚举、缺失顺序、展示cap和去重确定化，允许零结果。
7. 对照保留意向处理主样本，未来入选不反向删样本；板块日线篮子只提供明确命名的close-only极值。
8. 接受事务、head CAS、outbox、副作用和重试幂等明确；补充来源及到期结算独立运行。
9. 每日观察slot、cutoff和deadline预先冻结；后补跑不能制造真实Forward样本。
10. 历史附录明确非当前规范，移除重复阶段表和已完成式声明；回滚保留研究证据及用户跟踪记录。

## 逐章修改记录

以下按修订执行记录列出。某章在全文复查中再次修改，可能出现多条记录；链接指向最终文本。

| 序号 | 位置 | 修改说明 |
|---|---|---|
'''
for i,(title,reason,*_) in enumerate(changes,1):
    log+=f'| {i:02d} | {section_link(title)} {title.replace("|","/")} | {reason.replace("|","/")} |\n'

# Preserve exact B08-B10 audit title mapping rather than guessing their labels.
audit=Path('docs/audits/V4_2_2_CONTRACT_REAUDIT_20260925.md').read_text(encoding='utf8')
extra=[line.removeprefix('## ') for line in audit.splitlines() if re.match(r'## V422-B(?:08|09|10)\b',line)]
log+='\nB08–B10原始审计标题（用于追踪，不代表已完成独立验收）：\n\n'
log+='\n'.join('- '+x for x in extra)+'\n'
log+='''
## 本次已完成的检查

- 全文编号章节无重复，所有显式§引用都能找到目标章节；Markdown代码围栏正确闭合。
- 阶段引用在V4-00总括及§78的唯一阶段集合内；当前规范不再含旧PIT_OBSERVED_FORWARD枚举。
- 旧错误MDD公式已移除；下列数值反例通过独立预期检查。
'''
log+='\n'.join('- '+v for v in vectors)+'\n'
log+='''
- 输出采用桌面同目录临时副本后原子替换，写后回读核对；原件SHA256不变。
- 未对实现代码进行本轮功能验收；没有运行真实行情、外部接口、迁移或Forward观察，文档检查不能代替这些验收。

## 阶段回执及下一步

本次阶段：DOCUMENT_REVISION。合同：用户授权复制并全面修改最新版方案；依据项目只读TDX、原子产物、Phase 0和独立审计约束。证据：原件/修改版摘要、逐章记录、结构检查和数值反例。接受结果：DOCUMENT_REVISED（非RELEASE_PASS）。下一阶段：按§78先复核V4-00A基线和已有Phase 0状态，逐项冻结实际消费合同；其余模块仅在相应能力门满足后实施。
'''
assert not OUT.exists() and not LOG.exists(), 'refuse overwrite existing deliverable'
for target,content,copy_original in [(OUT,data,True),(LOG,log.encode('utf8'),False)]:
    temp=target.with_name('.'+target.name+'.tmp')
    assert not temp.exists()
    if copy_original: shutil.copy2(SRC,temp)
    with temp.open('wb') as f:
        f.write(content); f.flush(); os.fsync(f.fileno())
    os.replace(temp,target)
    assert target.read_bytes()==content
assert sha(SRC.read_bytes())==expected
(BASE/'full.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),doc.splitlines(True),fromfile=SRC.name,tofile=OUT.name)),encoding='utf8')
result={'source_unchanged':True,'section_edits':len(changes),'output_lines':len(doc.splitlines()),'output':str(OUT),'changelog':str(LOG),'output_sha256':output_hash,'checks':'DOCUMENT_CHECKS_PASS; IMPLEMENTATION_NOT_VERIFIED'}
(BASE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
