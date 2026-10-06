"""Atomically author the independent and cross-model audit deliverables."""
from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
AUDITS = ROOT / 'docs/audits'
HEAD = 'e21adab807e7f39960ec555764ab8c9d6b50f47b'
BASE = 'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'

def atomic(path, raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    with tmp.open('wb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)

def link(path, line=None):
    p = (ROOT/path).as_posix()
    if line:p += ':'+str(line)
    return f'[{path}](<{p}>)'

# Each entry is independent source review, not an online-report verdict copy.
STAGES = [
('V4-00A','Baseline Freeze','历史盘点接受可保留；当前全仓回归不可签PASS',
 '设计§70A、§71、§74、§78；历史baseline、备份/恢复与继承审计登记。',
 ['data/v4/V4_DEV_BASELINE_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json','docs/audits/V4_00A_PG_RECOVERY_AUDIT_20260925.md'],
 '冻结基线和保留函数清单是基础盘点；恢复/删除历史记录不替代当前运行授权。数据层采用版本化head，继承问题保持独立登记。',
 '当前stage head的phase0_status=FULL_PASS；基线和恢复证据存在。旧head历史字节可从Git恢复。',
 '本轮没有再次执行真实数据库恢复演练；默认pytest存在收集错误。不能把历史备份成功推导为本HEAD全仓release ready。',
 '未证实盘点设计偏离；GLOBAL-PYTEST为持续开放的跨阶段问题。下一步是独立处置测试债务，不是重跑或删除数据库。'),
('V4-00B','Security Lifecycle / Universe / PIT','日期有效身份工程审查通过；历史PIT能力受限',
 '设计§5、§6、§6A、§7.10；后续identity、source authority及A11正式变更。',
 ['src/workbench_analysis/security_entity_identity.py','src/workbench_analysis/dated_security_alias.py','src/workbench_db/migrations/v4_postgres/001_v4_phase0_foundation.sql'],
 'security_id与源symbol分离；稳定ID来自exchange、anchor symbol、list_date。lifecycle按security_id/effective_from/source_revision复合键保存，Universe用独立snapshot/member主键，保留知识时间。',
 '不能靠当前证券代码直接覆盖旧实体；未知上市日返回未解析，别名关系有独立证据。Foundation表并非一股仅一行。',
 '旧历史legal lifecycle/type和首次可得时间不能完整证明；当前名册不能自动用于存活偏差修正。',
 '这是已声明的能力限制，未发现允许用当前名册冒充历史PIT的新证据。未来按真实源和alias合同扩展。'),
('V4-00C','Publication / Revision / Namespace','发布身份和隔离机制工程审查通过',
 '设计§4、§4.6–4.9、§45A、§51A；namespace/publication/head后续加固迁移。',
 ['src/workbench_db/migrations/v4_postgres/001_v4_phase0_foundation.sql','src/v4/state_identity.py','src/v4/research_state_persistence.py'],
 '物理publication与逻辑输入digest分开；同日revision和前市场会话状态分开。manifest绑定实际消费源；namespace、模型、lineage不隐式跨用；head推进靠约束/事务而非任意最新记录。',
 '当前读取器检查accepted range、current head、owners、日历与data head一致性；读取验证实际通过。',
 '未执行新的生产head推进、跨进程真实发布或数据库部署；本审计没有grant权限。',
 '未发现新的发布身份硬错误。旧global_head_parent的哈希差异是历史引用，不可用原地重写“修复”。'),
('V4-00D','TDX VIPDATA Source Contract','有界源适配与隔离工程审查通过',
 '设计§3E、§3F；源package、下载、重叠与archive合同。',
 ['src/workbench_analysis/tdx_official_daily_source.py','src/workbench_analysis/tdx_snapshot.py','src/workbench_analysis/canonical_source_selection.py'],
 '官方页面发现、大小/timeout边界、下载暂存、ZIP manifest校验；ZIP路径、重复大小写成员、symlink/reparse被拒绝。local-overlap优先，补包填local缺口，同时保存替代字节和冲突计数。',
 'source family/源revision/记录日期有明确identity；不从源symbol直接猜canonical实体，不使用外部复权价格。',
 '本轮不发起下载或重新做全市场源实证；过去A股/非A股分层接受范围仍是权限边界。',
 '抽查调用路径未发现写TDX根的操作；不能据此证明仓库每个历史脚本都绝对无潜在写入口。继续仅用项目staging。'),
('V4-00E','Historical Adjustment / Coordinates','仿射调整工程保留；Forward消费存在新偏离',
 '设计§3B.6、§41A0、§46A；历史调整与anchor坐标合同。',
 ['src/adjustment/engine.py','src/v4/contracts/adjustment.py','src/workbench_analysis/v4_12_anchor_runtime.py','src/workbench_analysis/v4_15_settlement_successor.py'],
 '每10股现金/配股/送股生成alpha/beta；连续事件按后事件复合先事件的仿射变换。anchor保留raw bounds、创建基准与source revision；缺当前换基证据保持UNKNOWN。',
 'compose顺序与a_total/b_total公式可解释；source有效日期截断；新Forward validator检查系数有限、alpha>0、同基准与identity。',
 'A07预capture历史AS_RECORDED不可追补；新Forward校验扩大了区间内部失败对终点收益的影响，见IA-01；板块聚合没有满足新identity，见IA-02。',
 '调整基础公式未证实新错误；消费者隔离出现真实设计偏离。只阻断受影响Forward能力，不撤销基础调整接受。'),
('V4-00F','BaoStock Supplemental Contract','可选补充源降级审查通过',
 '设计§3D、§9、§76；A06 scoped acceptance/tolerance后续政策。',
 ['src/workbench_analysis/baostock_supplemental.py','src/workbench_analysis/baostock_dm01_capability_v2.py','config/baostock_binding_tolerance_policy_r2_candidate.json'],
 'turn百分点评分换成fraction；provider价格仅用于绑定，不作为Core价格权威。请求预算、版本和重试有界；停牌空量不填0。',
 'Core不因BaoStock不可得而失败；未有文档支撑的误差门为null并拒绝strict。',
 'STRICT_BINDING_FALSE等限制仍保留；不能把BOUND_SOFT升格为正式换手因子。',
 '与设计允许的可选降级一致。下一步只能消费事先接受的strict证据，不自行拍定容差。'),
('V4-00G','Algorithm Contract Framework','合同框架/三值/窗口定义工程审查通过',
 '设计§10A0、§72–73、§87A、§78；v1.2/native AST修订。',
 ['src/v4/contracts/algorithm_contract.py','src/v4/contracts/algorithm_contract_v12.py','src/v4/contracts/native_rule_r3.py'],
 'AST显式FIELD/PARAM/比较/算术与enum；拒绝非有限参数，明确除零缺失、identity/producer/quality/window。技术bar、横截面session、Forward市场horizon分立。标准Kleene与某些required UNKNOWN-dominant wrapper分开记录。',
 '因子、Seed、PREWATCH、Rotation、Reducer都有版本合同和参数实例；不能把Kleene FALSE短路当所有消费者都无需缺失质量检查。',
 '合同存在不等于所有scope已冻结，marked benchmark等未冻结门仍拒绝；人工语义审查未覆盖每一AST分支的穷尽证明。',
 '框架没有发现新失效；IA-01表明“有contract”和“实现吻合”必须分开验收。'),
('V4-00H','Capability / Performance / Rollback','当前Phase0接受可保留；性能外推不通过',
 '设计§49A.2、§52A/B、§74–75、§78；Phase0 final和后续治理归一化。',
 ['src/v4/contracts/phase0_gate.py','reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json','reports/v4_phase0/V4_PHASE0_PERFORMANCE_BASELINE_R2.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json'],
 'evaluate_phase0检查00A–H齐全、scope owner、必需能力、不合法FULL_PASS+blocked组合；FULL/DEGRADED/BLOCKED与scanner权限分开。',
 '当前stage authority已记录FULL_PASS，后续正式记录覆盖早期receipt状态，不把旧PENDING重新判为当前全局bug。',
 '2026-09-25性能baseline明确当时v4_runtime_row_count=0，且未运行daily scanner。它不能证明今天全市场DAG、FEP、跨进程路径达到性能预算。marked门未冻结仍受限。',
 'Phase0状态保留；性能/恢复的当前真实验收为未重验，IA-07记录扩容风险。下一步在真实部署前补当前负载测量。'),
('V4-01','TDX History Bootstrap','接受范围内工程审查通过；历史全能力不通过',
 '设计§3B、§5.3、§78；R8/R8.3 alias、identity/source-authority正式处置。',
 ['src/workbench_analysis/tdx_local_snapshot.py','src/workbench_analysis/v4_01_required_scope.py','src/workbench_analysis/v4_01_alias_completeness.py','data/v4/V4_01_ACCEPTED_HEAD.json'],
 'archive/extraction摘要、local snapshot身份、source key→canonical entity别名证据与历史Universe映射；缺失required identity关闭相应scope。',
 'accepted status为FULL_PASS_REQUIRED_SCOPE，有别名/改代码closure链；快照校验防文件变化和路径逃逸。',
 'FULL_PASS_REQUIRED_SCOPE不是两年历史全部生命周期首次可得证据PASS。当前entity修复和historical legal/type范围不可互代。',
 '能力降级按设计保留，未发现必须重建已接受bootstrap的新算法证据。'),
('V4-02','Canonical Daily / PIT Periods','Canonical工程范围通过；历史PIT/制度范围受限',
 '设计§3C、§7.2/7.5、§10N、§59；R6、A10/A12、DM01 R4R2后续约束。',
 ['src/workbench_analysis/v4_02_closure.py','src/workbench_analysis/special_price_phases.py','src/v4/go_forward_r3.py','data/v4/V4_DATA_ACCEPTED_HEAD.json'],
 '原始/调整日线分立；周月由截至asof日线派生，closed与asof period隔离；有bar为ACTUAL，缺bar由日期有效provider status分停牌/数据缺口/UNKNOWN；除权参考用Decimal tick舍入。',
 '当前data head接受日期为2026-09-30，正式状态为EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN；daily bridge验证目标日、源/producer实例及lineage。',
 '实时capture后才可积累知识时间；historical corrected不升格AS_RECORDED；BSE/special price phase缺证据只降级对应规则，不推断正常limit。DM01直接脚本入口缺repo-root导入bootstrap，见IA-10。',
 '未复活旧A12 blocker；未发现当前数据head被历史源静默覆盖。Forward端实际可估值证据仍缺，见阶段15。'),
('V4-03','Pure-Core Factors','amended范围工程审查通过',
 '设计§9A、§10/10A0、§27、§49A.1；Sector ownership正式amendment。',
 ['src/v4/factors/core.py','src/v4/factors/relative.py','src/v4/factors/native.py','data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json'],
 'MA/ATR/HHV/LLV技术bar窗口跳过已确认停牌并对不明缺口UNKNOWN；retN用固定market endpoints，RPS同分midrank；市场参考起点Universe可评估集等权，delta依赖当时prior RPS工件。',
 'asof裁剪、序列唯一递增、调整/source identity和nonfinite输入受检；横截面coverage和input/output/window digest明确。市场参考不是Forward固定篮子。',
 '历史prior RPS首次可得/存活偏差不能因accepted historical重构自动证明；Sector native ownership转到08不等于03漏实现。',
 '与正式ownership修订一致，基础因子抽查无新硬公式错误。保留历史PIT能力边界。'),
('V4-04','Full-Market Core Profile','Pure-Core状态工程审查通过',
 '设计§10A.3、§10B–10G/10I；r4语义closure、Amount-A独立接受。',
 ['src/v4/profile_core.py','src/v4/profile_primitives.py','src/v4/profile_status.py','data/v4/V4_04_ACCEPTED_HEAD.json'],
 '趋势/位置/均线/相对/压缩/量额/extension按冻结阈值顺序和UNKNOWN规则映射；技术长窗要求日期状态与日历一致。UNKNOWN和NOT_IMPLEMENTED不同；Participation缺clv只影响所需分支。',
 'Core Profile不依赖Turnover/sector/advanced；技术停牌与未知缺口有明确区别，branch顺序可解释。',
 'Sector Amount-A producer scoped accepted不能给H21 consumer或Stock AMR20授权；derived原始接口仍要求上游accepted输入合同。',
 '未发现新Pure-Core branch漂移；A04_H21及historical Amount-A继续单独保留。'),
('V4-05','Replay Gate A','DATA_FACTOR_REPLAY_DEGRADED范围保留',
 '设计§53 Gate A、§54–55；R4.1/R4.2 exact candidate绑定及A02下游amendment。',
 ['src/v4/replay_r4_identity.py','src/v4/replay_r4_lfs.py','src/v4/replay_r3_guards.py','data/v4/V4_05_ACCEPTED_HEAD.json'],
 '因子/日线/Universe/坐标重放identity，exact candidate ledger及逻辑摘要；LFS实体与pointer分开，target日期限定Universe身份。',
 'Accepted status明确DEGRADED；当前代码有源和ledger绑定，不单靠测试数量签release。',
 '重构重放稳定并不证明historical AS_RECORDED。旧target日期受accepted artifact限定，不能自动用于新目标日。',
 '未发现新Gate A身份缺陷；全仓pytest不绿是独立测试债务，不能改写历史Gate A范围。'),
('V4-06','Turnover Supplemental','可选DEGRADED范围保留',
 '设计§9、§9A、§76；TURNOVER_CONTEXT_V1与A06 binding tolerance。',
 ['src/workbench_analysis/v4_06_supplemental.py','src/workbench_analysis/baostock_supplemental.py','data/v4/V4_06_ACCEPTED_HEAD.json'],
 'append-only enrichment revision；strict-only历史窗口，confirmed suspension与UNKNOWN分开。证券映射拒绝重复/歧义，换代码须显式accepted映射。',
 '不修改Core publication/资格、不把turn字段变成自由流通换手；补充源异常只影响自身。',
 'strict binding不可证明时上下文继续PENDING/UNAVAILABLE/UNKNOWN，不能自动恢复成正式输入。',
 '设计允许的可选降级，不构成07前置全局block。下一步补充能力需自己的外审。'),
('V4-07','Stock Base Seed / PASS A','接受范围工程审查通过',
 '设计§13A–14；BASE_SEED_V1、参数/field/vector freeze和A02 amendment。',
 ['src/v4/base_seed.py','config/v4_07_base_seed_contract_v1.json','config/v4_07_parameter_set_v1.json','data/v4/V4_07_ACCEPTED_HEAD.json'],
 '仅消费Core原始安全、位置、结构、相对变化；不读Final State、Focus、在线补充。参数ID、comparison、status和值域校验，UNKNOWN保留理由；输出规则路径和谓词。',
 '真实loader验证full-market行数、board/date/publication与receipt/artifact摘要，不把单条成功样本代表全Universe。',
 '历史prior RPS不可得影响对应分支；当前Freeze为candidate本身不授予新目标日生产权限，授权靠接受链。',
 '未发现新反馈/参数偷换；上游质量限制必须继续传播。'),
('V4-08','Sector / Rotation / PASS B','capability-scoped工程保留；全能力不通过',
 '设计§15–21A；R5.2 accepted context、A05 B2 amendment、A04 producer scoped acceptance。',
 ['src/sector/native_r5.py','src/sector/rotation_r5.py','src/sector/accepted_context_r5_2.py','data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json'],
 'membership有效时点、common members、sector等权median/width/rank、Wilson seed width；Rotation冻结pulse basket/denominator，quality四态，missing history关闭分支；不用1/N成员稀释替代重叠诊断。',
 'retention不删除不可得成员；price basis不匹配不算收益；mature-only UNKNOWN不无条件污染early允许分支。',
 'legacy valid-member仅CURRENT_SNAPSHOT范围；Amount-A H21和历史Amount-A未授权，WARM受限制；historical PIT成员不得以现在成员补造。',
 '这些是正式限制。IA-02只涉及Forward板块结算，不能因此否定Rotation当日Core算法。'),
('V4-09','Stock PREWATCH / PASS C','当前producer scoped工程审查通过；生产未授权',
 '设计§22–25、§37–39；r1.1 priority provenance、A08 current runtime最新外审和V4传播。',
 ['src/v4/stock_prewatch.py','config/v4_09_priority_provenance_contract_r1_1.json','config/v4_16_runtime_capability_resolution_v2.json','data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4.json'],
 'raw采用UNKNOWN_DOMINANT_AND(base_seed,mandatory quality)；Emergence/Structure/Risk独立三轴，priority axes有producer/source identity。先遇到未解析HIGH候选不越过它直接选MEDIUM。',
 '当前load_package实际通过；A08_CURRENT_RUNTIME为ACCEPTED_SCOPED，scope shadow blocker false；V6 resolver分issue_id和runtime capability，未知issue fail-closed。',
 'V4 Current Audit Head整体status仍是GOVERNANCE_PROPAGATION_CANDIDATE；A08外审与生产/真实激活权限不能等同。production blocker仍true，permission_granted=false。',
 '相比线上报告的b7ca247基线，A08传播状态更新不是审计分歧；本轮不改变任何正式head。'),
('V4-10','Multi-Axis State Reducer','interface与后续DAG范围工程保留',
 '设计§30–33、§78；authority/lineage/calendar同日修订加固。',
 ['src/v4/research_state.py','src/v4/state_provenance.py','src/v4/research_state_persistence.py','data/v4/V4_10_ACCEPTED_HEAD.json'],
 'model boundary→硬失效→required UNKNOWN→阶段选取→降级hysteresis/health/expiry/reentry；停牌保留旧状态，市场会话计龄，同会话不reentry，episode/invalidation identity冻结。',
 '硬失效优先于UNKNOWN；stock WARM为NOT_APPLICABLE；同日不累加downgrade天数；边界保留followup旧episode，不把新模型偷接旧state。',
 '10本身accepted是interface scope，完整owner DAG由11/12/14验收；仍有R3C item级production/historical re-audit debt。',
 '未发现必须重写reducer的新业务证据；不能把接口PASS叫完整模型实证PASS。'),
('V4-11','Confirmation / Events','D0/scenario scoped工程保留',
 '设计§34A、§71；R5 sealed D2 authority、stock AMR20 semantic erratum。',
 ['src/v4/confirmation.py','src/v4/confirmation_events.py','src/v4/confirmation_d2_candidate_r5.py','src/v4/sealed_owner_authority_r5.py'],
 '原V3.3 detector AST/参数精确提取；D0禁FINAL_STATE/FOCUS/online/future，同日downstream scenario diagnostic-only。prior_session真实state事件diff，logical event与same-day observation分离。',
 '包校验legacy AST/参数；缺required fact保持UNKNOWN；Stock AMR20与Sector Amount-A隔离，不因A04 producer接受就授权stock confirmation。',
 'TREND_CONTINUE中无法纯化的LOO依赖保持diagnostic；R3C prior/停牌/坐标外审item仍开放。',
 '符合“不伪造owner能力”设计；可保留既有scenario范围，不能宣布全部scenario生产完成。'),
('V4-12','Structure / Anchor / Support','multi-anchor/episode scoped工程保留',
 '设计§10J–L、§41A–G；R13 breakout episode、R9会话计数修订及R14 promotion。',
 ['src/workbench_analysis/v4_12_anchor_runtime.py','src/workbench_analysis/v4_12_multi_anchor_state.py','src/workbench_analysis/v4_12_structure_engine.py','src/workbench_analysis/v4_12_breakout_episode.py'],
 '每anchor绑定event/episode，raw坐标不可改；创建当日计数为0且support IDLE，杜绝自确认。selector按距离/日期/ID，不用首项fallback；会话/实际bar计数不同；hard invalidation优先。',
 '多anchor独立owning episode/counter digest；同日revision和unknown按冻结合同处理；coordinate_view缺换基证据UNKNOWN。',
 '真实owner、raw-anchor换基和历史窗口证据未全覆盖，不能从裸日线自行补造accepted结构输入。部分validator当前字节与历史接受SHA不同，旧字节可在Git精确恢复。',
 '限定能力保留；独立追踪historical/production re-audit及IA-08历史validator路由，不原地改接受工件。'),
('V4-13','Advanced Projection / LOO','scoped工程保留；完整真实LOO不通过',
 '设计§20–21、§41F/§65；R16 input binder、projection、publication与R17 active binding。',
 ['src/workbench_analysis/v4_13_input_binder.py','src/workbench_analysis/v4_13_loo_runtime.py','src/workbench_analysis/v4_13_profile_runtime.py','data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json'],
 '先排除目标再native、seed、端点和cross-section重算；primary industry与algorithmic support分开；全候选不完整时不能从已知候选“挑最好”掩盖UNKNOWN。',
 'prior自包含Rotation不冒充独立LOO episode；未知accepted history保持UNKNOWN；raw stock资格不反吃context enrichment。',
 '代码明确历史LOO NOT_VERIFIABLE/legacy B2 NOT_IMPLEMENTED/real support UNKNOWN；当日完整LOO/Rotation不能由这些工程输出宣称有实证。',
 '允许的分层降级，未发现新自反馈证据；当前真实能力仍不足。'),
('V4-14','Replay Gate B / Full DAG','ALGORITHM_STATE_REPLAY_DEGRADED范围保留',
 '设计§13A、§53 Gate B、§54–58；R18 precall consumption/独立oracle/rollback。',
 ['src/workbench_analysis/v4_14_precall_runtime.py','src/workbench_analysis/v4_14_owner_edge_runtime.py','src/workbench_analysis/v4_14_full_dag.py','src/workbench_analysis/v4_14_candidate_rollback_drill.py'],
 'F0→A→B→C→D0/D1→D2→context/projection按owner/input digest边绑定；precall先消费验证而不是结果出来后补伪trace；跨进程重放和rollback有独立记录。',
 '当前owner-head读取验证通过，synthetic事实明确标SYNTHETIC；reconstructed不自动成为historical PIT。',
 'engineered full DAG不是历史首次可得实证；Current Audit仍保留若干R3C/Git portability/real-window item；本轮未重新运行真实整市DAG。',
 '既有scoped Replay B保留；全模型historical PIT effectiveness/生产资格仍NOT_GRANTED。'),
('V4-15','Radar / Cohort / Settlement','历史接受保留；当前Forward局部REPAIR_REQUIRED',
 '设计§36、§45A–49B；R20持久化/independent oracle、R21接受、full-chain successor修复。',
 ['src/workbench_analysis/v4_15_radar_cohort.py','src/workbench_analysis/v4_15_settlement.py','src/workbench_analysis/v4_15_settlement_successor.py','src/workbench_analysis/v4_15_fep_label_time.py'],
 '日账本、logical event、enrollment按独立键；T0参考/controls/固定权重冻结。Forward T+1/3/5/10/20，统一evaluation basis，MDD为路径峰值回撤；outcome append-only，source revision与first/latest分开。',
 '股票公式、未知benchmark不阻断absolute、ITT不因对照后来入选而删除的结构设计成立；A/B/C对照分开。',
 'IA-01区间内部失败错误清空已验证端点R；IA-02板块aggregate少adjustment_identity且旧实现close-only冒充MFE_N。IA-03同源PENDING→DUE被幂等复用。real matured source/跨日换基尚未授权。',
 'IA-01/02为当前实现与合同偏离；IA-03限定通用工程API。不得用historical engineering接受抹掉本轮反例。'),
('V4-16','Realtime Shadow Dual-Run','工程待真实grant；受影响Forward能力先修复',
 '设计§51A、§52B、§77；最新V6 dependencies/authority V5、P0-02 R1R1和A08传播。',
 ['scripts/v4_16_go_forward_shadow_runtime_r4r4.py','scripts/v4_16_settlement_worker_v2.py','migrations/v4_16_real_shadow_integrity_v2.sql','config/v4_16_runtime_activation_authority_v5.json'],
 'grant在源读取/数据库打开之前；exact activation_head决定重启authority；queue由namespace/model/lineage/enrollment/horizon/due/source构造，CAS lease fence及at-least-once delivery；STOP不停止已接受结算义务。',
 'V6绑定核验均匹配；A08只解capability blocker不grant。P0-02已拒绝queue identity冲突和错误activation记录。trigger/FK为publication/slot/event/freeze/enrollment/due/outcome建立关系。',
 '当前grant=null、runtime_authorized=false、real_shadow_authorized=false，真实样本0。worker仍调用IA-01/02的successor；AcceptedPriceSource缺T0_basis_verified/available_at时降级，不能得到成熟OBSERVED。',
 '保持禁用符合设计，不是bug；“所有capability工程ready”不成立。IA-01针对Stock路径质量，IA-02在Sector开放前须修复。'),
('V4-17','Shadow UI','只读工程通过；真实readback未通过',
 '设计§62A–H、§69、§78；R26只读UI/source manifest合同。',
 ['src/workbench_service/shadow_context.py','src/workbench_service/static/shadow-v4.js','src/workbench_service/app.py','config/v4_17_shadow_ui_source_v1.json'],
 'context token绑定namespace/date/publication revision/model/params/lineage/daily input/source/readback manifest。SQLite mode=ro+query_only，路由GET-only，缺来源UNKNOWN。',
 'accepted_readback=null时不发现任意latest文件、不打开DB；simulation只能constructor注入；HTTP写被拒绝。',
 '没有真实publication/component readback外审；UI工程通过不等于真实今日V4页面完整。R26-A01继承V3失败单独保留。',
 '缺真实门符合设计。下一步必须受独立真实manifest接受后才签real UI readback。'),
('V4-17G','Shadow Stable / Provisional Forward Gate','NOT_GRANTED / 真实验收未开始',
 '设计§51–52B、§78；capability cutover policy与R30 native session owner。',
 ['config/v4_capability_cutover_policy_v1.json','config/v4_21_continued_forward_observation_contract_v1.json','config/v4_16_observation_slot_contract_v2.json'],
 '按capability累计连续accepted/evaluable session、漏slot/泄漏/回滚以及独立成熟事件；不把20–60日稳定期当模型盈利证明。',
 '政策区分engineering/forward/production permission，设计oracle不会grant。',
 '真实accepted session和matured event尚不足/为0；Sector/Rotation等未冻结门不能借stock事件取得授权。',
 '正常真实门待满足，不靠补造历史关闭。'),
('V4-18','Migration Replay Gate C','合同设计范围保留；实际runtime未实现',
 '设计§34–35、§53 Gate C、§77–78；最新namespace inventory successor V1_3。',
 ['config/v4_18_migration_replay_contract_v1_3.json','tests/fep/test_v4_18_namespace_successor.py','tests/test_v4_18_migration_contract.py'],
 '逐表REFERENCE/CARRY/NOT_MIGRATED/COPY、读源/写目标/rollback，保留open episode、pending settlement、user pin/note。当前226个适用SQL declaration与namespace matrix相符；旧R23工程schema不在该当前迁移范围。',
 'FEP canonical reconstruction/parallel legacy/033 signal registry与queue/integrity表已入最新矩阵；无生产write target冒领。',
 'future interfaces均未实现，receipts=null，migration_execution=false，accepted head不存在。最新successor不能继承旧版本外审就视为exact runtime接受。',
 '是计划内gate暂停；工程未完成，不能写“Migration Replay已通过”。实现前固化最终successor exact external acceptance。'),
('V4-19','Focus Source Cutover','合同设计保留；实际切换未实现',
 '设计§42–44、§52A/B、§77–78；R28 CUTOVER_V2 scoped policy。',
 ['config/v4_19_focus_source_cutover_contract_v1.json','reports/r28/design_oracle.py','tests/test_v4_19_focus_cutover_contract.py'],
 'Stock Core、Sector Stage、stock-sector、Rotation、risk change权限有依赖图；source route CAS、rollback按affected scope，user state不作为算法证据。',
 'oracle支持混合能力不全局promotion；无receipt、错scope、不足样本都NO_CUTOVER。',
 'route CAS/rollback声明implemented=false，cutover=false，V4_19 head NOT_CREATED；只有设计向量，不是运行迁移器。',
 '与等待17G/18 runtime门一致；不能把设计PASS扩成Focus生产完成。'),
('V4-20','Default UI Cutover','合同设计保留；实际默认切换未实现',
 '设计§62A–H、§68–69、§78；R29 mixed-module/context policy。',
 ['config/v4_20_default_ui_cutover_contract_v1.json','reports/r29/design_resolver.py','tests/test_v4_20_default_ui_contract.py'],
 '模块权限分别路由Legacy/V4/Shadow，context锁publication身份；stale session失效缓存，历史deep link只读，跨mode不静默重绑定。',
 '全模块当前LEGACY_PRODUCTION，显式shadow页面工程只读；模拟resolver不修改真实route。',
 'DEFAULT_UI_CUTOVER=false、生产permission全false，cutover接口尚未runtime实现。',
 '产品目标尚未完成；这是gate保护下的欠交付，不是当前静默切换bug。'),
('V4-21','Continued Forward Observation','native contract设计保留；真实累计未实现',
 '设计§46–52、§78；R30R1 native status/owner binding修订，v1版本1.0.1。',
 ['config/v4_21_continued_forward_observation_contract_v1.json','reports/r30r1/session_authority.py','reports/r30/design_ledger.py'],
 '按owner原生ACCEPTED_ON_TIME/MISSED_OBSERVATION_SLOT等状态与projection evaluable分开；SHADOW_REAL/PRODUCTION_REAL/replay lane隔离；事件/结果/日期计数不同。',
 '错拼status、错owner SHA、诊断lane混真实计数、MISSED却evaluable被拒绝；production native owner未绑定则不能计real gate。',
 'REAL_CONTINUED_FORWARD_OBSERVATION=NOT_STARTED，当前真实production status authority=null；设计模拟不能算真实累计。',
 '合同修复有效，实际持续观察仍未交付/未开始。先解决Forward局部错误和真实activation，再按授权积累。'),
('V4-22','Independent Audit','final audit合同设计保留；最终验收BLOCKED',
 '设计§51、§80–81、§85、§78；R31R2 fail-closed/item closure/exact reconstruction修订。',
 ['config/v4_22_independent_audit_contract_v1.json','reports/r31/audit_oracle.py','reports/r31r2/build_contract.py','tests/test_v4_22_r31r2_repair.py'],
 'closure evidence与closing authority分开exact path/SHA/contract校验；canonical digest本身不足。诊断lane先完整校验再过滤，最终verdict由open items、真实gates、accepted receipt共同构成。',
 '版本1.0.2避免旧builder无条件制造新canonical版本；OPEN-09非blocking语义独立保留。模拟final formula成立仍acceptance_granted=false。',
 '真实shadow/forward/migration/cutover/rollback和本轮IA-01/02未关闭，最终final pass NOT_GRANTED，head未创建。',
 '本审计是输入证据，不能自称V4-22最终独立接受或替用户授予下一stage。'),
('FEP-E1','Dataset / Identity / Registry','47-field工程范围保留；真实标签/观测未授权',
 '设计§90 FEP.1–6、FEP R2；E1 R2 final owner/governance及028–030 migration。',
 ['src/workbench_analysis/fep_e1/observation.py','src/workbench_analysis/fep_e1/feature_owner.py','src/workbench_analysis/fep_e1/labels.py','src/workbench_analysis/fep_e1/datasets.py'],
 'observation按scope/entity/date/signal逻辑身份；feature从exact accepted owner取47字段，不重算；label复制V4-15权威revision、source/mature/revision三时间。完整分母/每partition asof selection、缺失不删除。',
 'per-fold日期/episode不跨partition；不回填FIRST_OBSERVED；历史owner仅reconstruction。real adapter即使调用者传horizon字典也明确拒绝。',
 'FEP_REAL_FIRST_OBSERVED_ENTRY与REAL_MATURED_LABEL未授权；当前E1 live owner传输不同于E2历史工程数据。IA-06：本轮真实PG环境未完整复验，历史fresh/upgrade接受仅范围保留。',
 '已知接口缺口按设计fail-closed；不得宣传实时训练标签已可用。IA-07记录dataset权重算法扩容风险。'),
('FEP-E2','Conditional Statistics Baseline','FIRST_PREWATCH:T1工程范围保留',
 '设计§90 FEP统计/backoff/support；E2 R1R2 event strata及support policy v1_1。',
 ['src/workbench_analysis/fep_e2/conditional.py','src/workbench_analysis/fep_e2/support.py','src/workbench_analysis/fep_e2/event_strata.py','config/fep_e2_support_policy_registry_v1_1.json'],
 '桶内每日期总权1/D，同日每样本1/(D*n_d)，Fraction精确权重；逆经验CDF分位数；固定L4→L3→L2→L1 backoff，支持度不按收益选。count按rows/dates/nonoverlap blocks/entities/episodes，完整分母缺失与TV诊断。',
 '连续/类别/any-event不同口径，类别必须NONE，any-event不强行归一化；unsupported只diagnostic，不grant display/priority。首次事件stratum不以每日landmark替代。',
 '已接受scope只有FIRST_PREWATCH:T1；其他目标、事件、horizon/quality support未自动通过；descriptive频率不是个人预测概率。',
 '代码与当前工程统计合同抽查一致，无新hard backoff/weight错误；全样本/真实预测效力仍不可宣称。'),
('FEP-E3','Interpretable Models / Calibration','工程范围保留；有效性/OOS不通过',
 '设计§90 FEP建模；protocol v1_1 FIRST_PREWATCH:T1 reconstruction scope。',
 ['src/workbench_analysis/fep_e3/protocol.py','src/workbench_analysis/fep_e3/models.py','reports/fep_e3_r1/LOCAL_ACCEPTANCE_MATRIX.json'],
 'TRAIN/TUNE/CALIBRATION/OUTER按日期chronological且purge event_end/知识cutoff/shared episode；scaler/OOD只TRAIN fit，调参只INTERNAL_TUNE；Huber点模型与线性quantile分开。',
 '固定feature manifest/无插补；rearrangement事前注册；回归calibration为diagnostic，不伪称概率校准；JOINT_OOD UNSET不能global_OOD_OK。',
 '已记录MODEL_EFFECTIVENESS=NO_INCREMENT、REAL_OOS=false。Outer按重构知识时间评估，不是历史当时可用模型。本轮模型fit重演因当前Python缺sklearn受限（IA-06）。',
 '没有增益不是工程失败，也不阻断E5 baseline。新增概率分类/全horizon模型不在当前scope。'),
('FEP-E4','Optional Tree Challenger','optional diagnostic工程范围保留',
 '设计§90 optional challenger；E4 protocol和2026-10-06外部接受reconciliation。',
 ['src/workbench_analysis/fep_e4/challenger.py','config/fep_e4_challenger_protocol_v1.json','reports/fep_e4_reconciliation_final_audit_r1/FINAL_CLOSURE_READBACK.json'],
 'exact复用E3 fold/feature/preprocessing/OOD；HGB固定seed、无early stopping外侧选择，试验次数bounded；数值树序列化与sklearn预测parity阈值1e-12。',
 'seen Outer强制SEEN_OUTER_DIAGNOSTIC_ONLY/TEST_PREVIOUSLY_SEEN，失败trial保留，不把mixed表现选最好后声称冠军。',
 'CHAMPION=false、PROMOTION/priority/display未授权，无独立新OOS；sklearn private _predictors依赖版本锁，升级需重新parity。本轮4个实际tree parity用例因缺sklearn未完成（IA-06）。',
 '当前optional工程保留，不能宣传模型优越/生产替代。'),
('FEP-E5','Projection / Priority Shadow','canonical工程范围保留；真实display/priority未授权',
 '设计§90独立prediction ledger/API/CAS/rollback；R1R1C canonical metadata接受、full-chain033 hardening。',
 ['src/workbench_analysis/fep_e5/projection.py','src/workbench_analysis/fep_e5/canonical_ledger.py','src/workbench_analysis/fep_e5/metadata_binding.py','src/workbench_db/migrations/v4_postgres/033_fep_signal_contract_integrity_v1.sql'],
 'slot/model固定选择cutoff与deadline，输出不许覆盖identity；transaction中prediction/run/receipt一起accept；revision parent精确匹配。canonical fep.*通过FK/registry trigger检查signal family/predicate；deploy CAS head与rollback不修改预测历史。',
 '历史canonical reconstruction无live publication_id，由独立reconstruction authority绑定；旧parallel schema是显式历史工程范围，不能凭它打开生产。baseline可直接接E5。',
 'SHADOW_INFERENCE工程权限不是MODEL_DISPLAY/PRIORITY_USE。real FIRST_OBSERVED/OOS不足，CURRENT real source label gate未开放；PG负向测试本轮受环境限制。',
 '既有工程接受可保留；新增全scope/实时预测须独立授权和证据。上游IA-01/02不关闭前，不能把受影响outcome投射成可靠标签。'),
]

ISSUES = [
 dict(id='IA-01',severity='P1',kind='NEW_REPRODUCED_CONTRACT_DEVIATION',scope='V4-15/16 Stock Forward绝对终点收益与路径质量隔离',
      title='区间内部不可得使已验证终点收益被整体清空',
      sources=[('src/workbench_analysis/v4_15_settlement_successor.py',16),('config/v4_15_forward_price_path_contract_v1.json',None),('scripts/v4_16_settlement_worker_v2.py',82)],
      evidence='semantic_probes.json → UNKNOWN_INTERIOR_VALID_ENDPOINT：P0=10、终点close=11且身份/坐标已验证，内部行close/high/low缺失且verified_adjustment=false；实际R_N=null/outcome_status=ADJUSTMENT_UNKNOWN。独立预期R_N=0.1，路径指标不可评估。',
      cause='successor在计算endpoint前遍历全部actual row，任一valid_row失败直接返回整份invalid结果；它把路径坐标缺失提升成端点坐标失败。冻结unknown_gap明确ENDPOINT_RETURN_INDEPENDENT_IF_VERIFIED，设计§46A要求未确认内部缺口只限制路径指标。',
      impact='缺失内部价格/换基时，合法endpoint的absolute结果、对照结果和相应FEP ABS标签被多余删除。当前real activation禁用，未证明已经污染真实结果；缺失少报也属于算法合同偏离。',
      acceptance='保持endpoint/T0坐标严格验证；仅endpoint无效时R_N不可用。内部缺口限制MFE/MAE/MDD并给路径reason。独立向量覆盖missing/invalid interior、有效endpoint、无效endpoint/T0、确认停牌、公司行为，持久化worker/readback同预期；accepted历史字节不改。'),
 dict(id='IA-02',severity='P1',kind='NEW_REPRODUCED_INTEGRATION_AND_SCHEMA_DEVIATION',scope='V4-15/16 Sector自身篮子Forward与字段语义',
      title='板块聚合路径不满足新结算identity；旧实现把close极值写入价格MFE字段',
      sources=[('src/workbench_analysis/v4_15_settlement.py',196),('src/workbench_analysis/v4_15_settlement_successor.py',16),('src/workbench_analysis/v4_15_settlement_successor.py',67)],
      evidence='semantic_probes.json → SECTOR_BASKET_VALID_ENDPOINT：2成员P0=10、终点11，等初始权重均验证。historical R_N≈0.1，successor R_N=null、ADJUSTMENT_UNKNOWN；聚合生成行没有adjustment_identity。historical同时MFE_N≈0.1，high/low实际上都由basket close代替。',
      cause='successor通过FunctionType复用原settle字节码并替换price_path；原Sector分支产生单位指数close/high/low而没有新validator必需的identity。设计§49A.3只允许板块MFE_CLOSE/MAE_CLOSE，不应提供由close冒充的盘中MFE_N/MAE_N。',
      impact='即使全部成员端点有效，Sector absolute Forward也不能成熟；回到旧runtime会恢复R却保留字段语义问题。当前PURE_CORE_STOCK grant不授权Sector，不是现有Stock whole-chain P0。',
      acceptance='独立Sector篮子path及lineage合同定义每成员同basis到聚合指数的identity；有效篮子R正确、partial保持UNKNOWN而不重权，输出MFE_CLOSE/MAE_CLOSE；不得伪填股票high/low。n<2的股票relative-sector和Sector自身篮子分别验收。'),
 dict(id='IA-03',severity='P2',kind='NEW_REPRODUCED_GENERIC_API_STATE_COLLISION',scope='V4-15通用engineering SettlementRuntime；未证明当前durable real worker受影响',
      title='同一evaluation source的PENDING结果覆盖后续DUE幂等查询',
      sources=[('src/workbench_analysis/v4_15_settlement.py',195),('src/workbench_analysis/v4_15_settlement.py',227)],
      evidence='semantic_probes.json → PENDING_THEN_DUE_SAME_EVALUATION_DIGEST：首次cutoff=T0写PENDING；次次cutoff=T+1同源，返回same_ref=true、due_status=PENDING，未新增成熟结果。',
      cause='outcome key=enrollment/horizon/contract/source SHA；未到期记录与到期记录使用同一key。existing lookup在成熟计算后优先返回旧PENDING。',
      impact='通用工程API/readback和future source snapshot复用场景可能永远不成熟。现durable worker只允许due后enqueue，因此不能把反例直接称为已激活真实worker故障。',
      acceptance='pending保持在独立due/planner层或冻结明确的状态revision规则，禁止覆盖历史outcome。验收同源pre-due→due、重复due、corrected source、first/latest、重启和持久化读取；保持设计唯一键，不简单把执行时间塞key破坏幂等。'),
 dict(id='IA-04',severity='P2',kind='NEW_REPRODUCED_BOUNDARY_HARDENING',scope='Forward数值输入边界；正式上游可达性未证实',
      title='有限但非法的实际价格仍被标OBSERVED',
      sources=[('src/workbench_analysis/v4_15_settlement_successor.py',16),('src/workbench_analysis/v4_15_settlement.py',51)],
      evidence='semantic_probes.json → INVALID_NEGATIVE_ACTUAL_PRICE：close=-1、high=-0.5、low=-2、P0=10，系数identity，实际R=-1.1、MAE=-1.2、OBSERVED。',
      cause='新validator检查finite和alpha正，未检查actual OHLC正价格/包络。它信任上游verified flags。',
      impact='当前已接受原始源有价格校验，本轮没有证明正式producer会输出此输入；不能夸大成真实数据污染P0。新adapter或错误flag可将非法结果传入FEP。',
      acceptance='明确上游保证与消费者check责任；actual-price不合法拒绝/降级，终值退市0走独立terminal路径且保留证据，不能拒绝合法terminal=0；验收raw OHLC包络，变换后价格允许域按最新合同独立冻结，不凭本报告任意定义。'),
 dict(id='IA-05',severity='P1',kind='EXISTING_OPEN_CROSS_CUTTING_TEST_DEBT',scope='全仓回归与release证据；独立于各stage historical gate',
      title='默认pytest收集失败，全仓回归不能签绿',
      sources=[('tests/upgrade_m14/test_online_batches.py',9),('src/workbench_online/collector.py',1),('docs/audits/V4_GLOBAL_PYTEST_COLLECTION_AUDIT_ITEM_R1_20260929.md',None)],
      evidence='pytest_full.log/xml：ImportError _commit_raw_and_batch；继续收集全仓复跑已中止，无完整JUnit，不报通过数量。后续阶段/FEP限定测试的失败/错误/skip见pytest_summary.json、pytest_stages.log/xml。',
      cause='已于2026-09-29登记OPEN/NOT_ACCEPTED。hot-rank capture后来被retire为request-time-only，但旧测试仍导入capture函数；其他历史exact/设计断言与隔离DB条件也须逐项处置。',
      impact='不能宣称全仓回归通过或本HEAD release ready；同样不能把默认收集错误直接等于已接受V4 Pure-Core算法失败。',
      acceptance='复用原global audit item，按失败node独立分类、baseline、正式supersession或修复，DB测试先验证隔离环境；保留退役写入口禁用；最终默认完整pytest无收集错误且失败有独立验收。禁止删测/静默ignore冒充绿。'),
 dict(id='IA-06',severity='P1',kind='VERIFICATION_AND_DEPLOYMENT_EVIDENCE_GAP',scope='本轮FEP/阶段DB fresh-upgrade/权限/trigger及模型依赖实证复验',
      title='隔离库fixture/DSN和模型依赖不足，当前环境验证未完成',
      sources=[('tests/fep/conftest.py',16),('tests/test_full_chain_fep_db.py',9),('src/workbench_db/migrations/v4_postgres/033_fep_signal_contract_integrity_v1.sql',1),('src/workbench_analysis/fep_e3/models.py',70)],
      evidence='首轮281 skip中214+2缺canonical fixtures、62缺FEP_E1_TEST_DSN、1缺disposable DB DSN、2缺symlink权限；没有PG连接error记录。38个setup errors均为旧V4_13_STAGE authority拒绝。E3/E4另有5项缺sklearn失败。逐node原文见pytest_stages.xml/inventory；历史fresh/upgrade readback不是本轮重跑结果。',
      cause='隔离库显式env gates和当前Python依赖与历史验收环境不同；E盘basetemp与tempfile根不一致还导致68 fixture namespace拒绝，已独立更正环境复验，原失败保留。static DDL/FK/trigger和模型源码存在不能证明当前部署可运行。',
      impact='工程历史接受范围可保留；本轮不能独立确认全部真实PG表约束、role/search_path、fresh/upgrade与模型fit/parity效果。不得在market_research生产库重置来取证。',
      acceptance='仅使用已确认disposable隔离DB，冻结空库/升级迁移列表，逐项negative insert/权限/CAS/rollback实证；冻结兼容模型runtime依赖并完成fit/parity，统一E/F TEMP及fixture安全根。记录当前source SHA；环境验证不自动grant生产。'),
 dict(id='IA-07',severity='P2',kind='PERFORMANCE_VALIDATION_DEBT_NOT_PROVED_TIMEOUT',scope='FEP E1 dataset/E3 purge、全市场Forward controls与整链负载',
      title='若干二次复杂度路径尚缺当前规模性能证据',
      sources=[('src/workbench_analysis/fep_e1/datasets.py',54),('src/workbench_analysis/fep_e3/protocol.py',104),('src/workbench_analysis/v4_15_settlement.py',21),('reports/v4_phase0/V4_PHASE0_PERFORMANCE_BASELINE_R2.json',None)],
      evidence='E1对每row重新扫描rows构建population/Counter；E3对每row扫描later rows；controls为每signal冻结complete population。早期性能baseline的runtime row count=0。',
      cause='正确性向量覆盖不能替代当前负载测量。无本轮CPU/RAM/全市场daily/LOO/FEP真实负载回执。',
      impact='支持大数据规模的SLA未证实；没有实测timeout，所以不判当前性能故障P0/P1。重复snapshot可能扩大工件体积。',
      acceptance='按合同规模测elapsed/peak memory/output bytes；必要时预聚合population weights、partition边界和复用固定features，保留完全相同logical digest/selection/weight。'),
 dict(id='IA-08',severity='P2',kind='HISTORICAL_PROVENANCE_ROUTING_DEBT',scope='旧head/validator exact身份；非当前active head损坏',
      title='历史引用需显式版本路由，不能与当前工作区字节等同',
      sources=[('data/v4/V4_09_ACCEPTED_HEAD.json',None),('data/v4/V4_12_ACCEPTED_HEAD.json',None),('src/workbench_analysis/v4_portable_exact.py',21),('src/workbench_analysis/v4_13_accepted_contract_package.py',50)],
      evidence='4797条绑定4777匹配、20 mismatch；20引用对应15个(path,expected SHA)身份全部Git可找回。PortableExact对这些旧绑定返回UNREGISTERED_ACCEPTED_BINDING，当前CurrentStageAuthority与V4_09 load_package均PASS。',
      cause='旧head保存当时code/validator及parent状态，新head/validator已推进。历史库精确字节与当前文件不同是事实；Git可追溯不等于每个旧CLI都能在当前checkout直接运行。例：v4_13_accepted_contract_package.current_contracts只接受stage range到12/13，现到15则UNAUTHORIZED_V4_13_STAGE，38个setup errors来自此旧entry。',
      impact='历史验收不能直接给当前代码授权，旧validator重跑可能失败；必须使用明确historical reader/checkout。未发现active V6 literal dependency mismatch，不能据20数量全局重开历史阶段。',
      acceptance='复用Current Audit已开放Git/production再审item，固定旧字节回放路由或新successor外审；所有current consumers绑定新scope的源码，禁止generic normalize/改历史SHA。'),
 dict(id='IA-09',severity='P1',kind='NEW_CONFIRMED_TEST_ISOLATION_DEFECT',scope='全仓旧UI测试fixture与审计运行环境；独立于V4算法stage gate',
      title='旧浏览器测试直接启动实际工作区数据库的发布恢复入口',
      sources=[('tests/upgrade_m12/test_browser_behavior.py',41),('src/workbench_service/app.py',2297),('src/workbench_publish/service.py',272)],
      evidence='全仓继续收集复跑观察到python子进程37788以root实际data/database/market_research.duckdb启动serve（parent39176）。serve先_recover_startup，再监听；recover_interrupted更新RUNNING jobs/attempts且对active任务启后台重跑。已中止进程，partial log最后84%，没有完整JUnit。详情global_rerun_interruption.json。',
      cause='fixture把真实ROOT/DB传给通用可恢复服务，而不是disposable clone；read-only浏览器断言不等于服务启动read-only。本轮复跑前隔离检查不足，未捕获DB前指纹。',
      impact='理论上可改变真实job状态或恢复发布任务。未证实本轮发生具体业务重发布，也不能证明零DB写；无TDX写命令、业务tracked diff为空，后者不能证明ignored DB零变化。不能用这种测试作为纯只读验收证据。',
      acceptance='fixture只使用已冻结disposable数据库/根目录，启动前对绝对路径fail-closed；测试显式选择无生产恢复入口的服务或隔离恢复，校验test前后production heads/jobs/artifacts无变更。重复全仓之前先完成安全环境验证；不修改TDX源。'),
 dict(id='IA-10',severity='P2',kind='NEW_CONFIRMED_STANDALONE_CLI_BOOTSTRAP_GAP',scope='DM01 R4/R4R1 daily直接脚本启动；非底层九组件数值算法',
      title='DM01脚本仅加入src，未满足kernel的scripts包导入',
      sources=[('scripts/run_v4_dm01_daily_increment.py',12),('src/workbench_analysis/dm01_incremental_component_builders_r3_3.py',18),('tests/v4_dm01_r4/test_runtime.py',122)],
      evidence='test_actual_entrypoint_no_capture实际子进程报ModuleNotFoundError:scripts。独立cli_bootstrap_probe.json只执行--help：继承环境exit1，显式PYTHONPATH=repo root+src后exit0。没有执行capture/build/promotion。',
      cause='该入口只sys.path.insert(ROOT/src)，Python直接跑scripts/file.py将scripts目录置于sys.path而非repo root；kernel又from scripts.v4_02_build_raw_selected_v2导入。隐含依赖外部PYTHONPATH，直接运行合同/测试不能成立。',
      impact='直接daily维护CLI在进入session gate前即失败，不能声称独立入口工程可运行；明确设置bootstrap或模块式launcher可绕过，因此不否定组件公式或当前已接受data head，也不认定当前所有launcher故障。',
      acceptance='冻结支持的直接CLI/模块launcher及root+src环境bootstrap合同，在干净child环境验证--help和future-session WAIT/no capture；补实际已授权session的隔离入口向量，保留历史字节，依赖/入口修复不自动grant数据发布。'),
]

def main():
    stage_rows='\n'.join(f'| {s[0]} | {s[1]} | {s[2]} |' for s in STAGES)
    issue_rows='\n'.join(f"| {i['id']} | {i['severity']} | {i['kind']} | {i['title']} | OPEN_AUDIT_ONLY |" for i in ISSUES)
    text=f'''# 阶段00–22及FEP独立全阶段代码、算法、数据结构、合同审计 R1

日期：2026-10-06（Asia/Shanghai）。审计代码HEAD：`{HEAD}`。分支：`codex/v4-system-reform`。

## 1. 独立总裁决

**当前项目不能签“全能力完成 / 全仓release PASS / V4-22最终PASS”。阶段00–15及FEP既有能力限定的历史接受总体保留，但当前Forward实现存在2项新复现的P1合同/集成偏离。阶段16没有真实激活grant；阶段17缺真实readback；18–22主要仍处于合同设计及真实门等待。**

本轮新发现Forward算法/集成P1为IA-01、IA-02；另有独立测试隔离P1 IA-09。IA-03/04为限定API/输入边界P2、IA-10为独立CLI bootstrap P2；IA-05/06是测试和当前数据库/模型环境验证证据问题；IA-07/08是性能和历史路由债务。共10项独立登记。P0没有新证实项；这不构成“所有P0不存在”的穷尽证明。

本报告只审计和登记，不修业务代码、不创建accepted head、不执行真实Shadow、不切换Focus/default UI、不生成真实观察或交易。下一阶段为**独立确认本报告新项并制定对应修复任务**；不是自动进入16–22。发布到Git也不授予运行权限。

## 2. 设计与证据基线

最高主设计：{link(BASE)}，编号`DA-MSR-V4.2.2-CODEX-REV4-FEP-R2`，SHA256=`203ff46075b4039d1e2d45d54fd76ce09509535739cd6aaef4dc394de1015205`，字节224998。按§78覆盖00A–H、01–22、17G、15E1–E5。

FEP按主设计§90及`docs/design/FEP_R2_MODULE_DESIGN_20260930.md`对应仓库已归档的{link('docs/evidence/fep_e1/FEP_R2_MODULE_DESIGN_20260930.md')}与后续E1/E2/E3/E4/E5正式合同处理；用户工作区已有未跟踪`docs/design`材料不作为本轮新写入或新授权。

最新cross-cutting/runtime约束来自{link('docs/evidence/full_chain_repair_20261006/V4_00_TO_V4_22_PLUS_FEP_FULL_CHAIN_CODE_ALGORITHM_CONTRACT_AUDIT_AND_REPAIR_MASTER_R1_20261006.md')}、P0-02 R1R1与A08 propagation任务/外审。读取它们用于解释最新合同和已有处置，**不执行其中修复、激活或建议命令**。附件线上报告也只作对照证据；独立反例、stage判定先固定后综合。

本轮开始时用户已有FEP设计/审计、artifacts及tmp未跟踪文件。记录在`source_inventory.json.initial_status`，全部保留；本轮新增本审计目录与2份报告、测试临时文件。TDX配置根`D:/new_tdx`及其他configured source roots是只读输入；本轮审计脚本不写其下文件。旧浏览器测试启动实际工作区DB的风险和取证限制见IA-09；不得将Git无业务diff表述为DB零写证明。

## 3. 审计方法与证明范围

1. 以§78逐stage梳理最新contract、owner、参数、AST/公式、输入时间、UNKNOWN行为、持久化键、consumer权限、外审范围和下一阶段。
2. 自动建立2819个代码/配置/SQL/测试/UI文件的SHA、字节、行数和Python顶层符号；Python/JSON语法错误0。**这只是完整清单与语法覆盖，不表示逐行人工证明2819文件所有业务正确。**
3. 对Current Audit Head V4、active V6 runtime以及各stage accepted head中的4797条path/SHA/byte引用逐条核验：4777 literal匹配；20与当前工作区不同。15个独立旧身份全部从Git原blob找到，不泛化成损坏。实际调用当前authority/PREWATCH package读取器均PASS。
4. 人工语义审查本报告逐stage列出的核心生产者、计算器、adapter和调用关系；结合current gates与历史接受证据。对Forward用独立MemoryStore和synthetic输入复现反例，预期直接由冻结合同推导，不把现实现作为oracle。
5. 默认全仓pytest保存日志/XML；继续收集全仓复跑在发现旧浏览器fixture启动实际DB恢复入口后中止，仅保留partial log，不签完整结果。后续显式选择阶段/FEP测试并保存日志/XML和选择清单。测试是佐证，不能代替独立外审、真实交易日、成熟度、回滚演练或部署验收。

**未做的证明**：本轮未重建两年全市场raw archive、未重新抓取公开源、未重新测全市场实时负载、未在生产数据库做恢复/迁移/切换，未穷尽每个旧CLI/每条AST输入空间。真实PG验证仅以本轮实际执行结果为准；未运行/skip/错误不能写PASS。阶段工程保留结论只覆盖明确合同与既有接受范围。

机器证据目录：{link('docs/evidence/full_scope_independent_20261006/audit_baseline.json')}；清单、heads、逐引用、historical provenance、active reader、synthetic probes、pytest日志和分组统计均随本报告提交。

## 4. 全阶段判定矩阵

“工程审查通过/保留”指限定scope内代码/合同/既有接受可解释，不是本轮签发正式accepted permission。“未通过”区分代码缺陷、证据不足、正常gate等待；不把SHADOW_ONLY当全局实现错误。

| 阶段 | 设计交付 | 本轮独立判定 |
|---|---|---|
{stage_rows}

## 5. 每个阶段的代码、算法、数据结构、通过与未通过原因
'''
    for stage,name,status,design,sources,algorithm,passed,failed,deviation in STAGES:
        text+=f'\n### {stage} · {name}\n\n**本轮判定：{status}。**\n\n设计与最新适用合同：{design}\n\n核验代码/数据结构/权威：'+ '；'.join(link(p) for p in sources)+f'。\n\n算法与结构结果：{algorithm}\n\n为什么可通过/保留：{passed}\n\n为什么不能全通过：{failed}\n\n是否偏离及下一步：{deviation}\n'
    text+=f'''
## 6. 独立跨阶段问题登记

登记scope、证据和acceptance独立于stage gate。`OPEN_AUDIT_ONLY`表示本轮发现/复验登记，未写入正式Current Audit Head，也不自动关闭原canonical issue。

| ID | 优先级 | 分类 | 问题 | 状态 |
|---|---|---|---|---|
{issue_rows}
'''
    for item in ISSUES:
        text+=f"\n### {item['id']} · {item['title']}\n\n优先级：**{item['severity']}**。分类：`{item['kind']}`。Scope：{item['scope']}。状态：`OPEN_AUDIT_ONLY`。\n\n代码证据："+'；'.join(link(p,n) for p,n in item['sources'])+f"。\n\n复现/证据：{item['evidence']}\n\n为何不通过：{item['cause']}\n\n影响与证明边界：{item['impact']}\n\n独立关闭标准：{item['acceptance']}\n"
    text+='''
## 7. 数据结构专项结论

| 层 | 核验对象 | 结构结果 | 未取得的能力 |
|---|---|---|---|
| Foundation | source revisions/lifecycle/universe/publication/model namespaces | 日期和源revision进入键；双时间和namespace可表达；不是每股仅一行 | 历史first availability不足不能补造 |
| Daily/Profile | raw/adjusted日线、closed/asof周期、factor/profile rows | 原始价与调整价分离，field/window/source digest存在，UNKNOWN与NOT_IMPLEMENTED区别 | special/bse/长期历史能力按scope保留 |
| Sector/Rotation | membership snapshots、native results、pulse episode/basket | common成员和冻结分母/原权重；stock target exclusion先于LOO重算 | Amount-A H21、historical Amount-A、历史LOO |
| State/Event | research_state lineage/authority、confirmation/event records | logical event与同日observation独立，prior session/calendar/episode不混 | 某些historical/production item外审未关闭 |
| Cohort/Forward | immutable store T0/controls/due/outcome revisions | 有固定T0、独立基准和对照、revision键；局部数值/状态缺陷见IA-01..04 | 尚无真实matured OBSERVED证据 |
| Real Shadow | SQLite facts与integrity_*、queue v2 | 触发器/FK验证slot→publication→event/freeze/enrollment→due/outcome；CAS fencing保护claim | 真实activation及首次publication未授权 |
| FEP canonical | 028–033 migration、observation/snapshot/labels/dataset/models/slot/prediction/deploy | signal registry不是随意同名字段；source/mature/revision三时间，permission/CAS和reconstruction authority分离 | 本轮PG fresh/upgrade全实证未确认；display/priority未授权 |
| Migration | V1_3 namespace matrix | 226项当前适用SQL声明覆盖；旧R23工程库16表不在该迁移范围，不能强行算漏表 | 执行reader/writer/reconciler/CAS/rollback未实现 |

静态schema有约束并不自动证明其已在当前真实库部署；历史fresh/upgrade日志只支持当时范围。本轮不在生产库执行DDL。

### M14在线增强边界（跨阶段专项）

M14在线增强与V4-14 Replay Gate B不是同一模块。核验`config/online_source_registry_v3.json`、`config/m14_runtime_capabilities_v1.json`、`src/workbench_online/base.py`、`collector.py`、`src/workbench_service/online_hot_rank.py`以及`app.py:256`：实际API仅LATEST，AS_OF/batch_id拒绝；collector两capture入口无条件抛HOT_RANK_CAPTURE_DISABLED，direct flow持有内存rows但未写raw/row/batch。能力gate要求DIRECT_EPHEMERAL_LATEST及三个persist=false；HTTP预算timeout≤30秒、response≤2MB、retries=0，direct总响应预算12秒、失败按源UNAVAILABLE。外部quotes仅display enrichment，无local snapshot身份回写。旧batch reader仍存在但不在当前API direct调用链；其存在不能算当前落盘。默认collection失败来自旧capture测试导入退役函数，不能为修测试恢复写入口。本轮未重新抓取在线源或证明网络可用性，只确认这些静态调用边界与当前direct约束一致。

## 8. 当前仍开放的既有能力项

本轮从Current Audit Head V4读取，而非根据旧报告批量关闭：

- A04_H21_CONSUMER：ACCUMULATION_CONTINUES；H21/source consistency/arithmetic/consumer外审缺一不能grant。
- A04_HISTORICAL_AMOUNT_A：BLOCKED_AFFECTED_SCOPE。
- A03：真实forward积累继续；A07与HISTORICAL_PIT_EFFECTIVENESS为永久或预capture能力限制。
- R3C accepted suspension/adjustment coordinate/D2 prior authenticity/event UNKNOWN、Git exact portability：OPEN_EXTERNAL_REAUDIT。
- V4_12_REAL_OWNER、V4_13_REAL_OWNER、REALTIME_ACCEPTED_COHORT_MATURITY、REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT：NONBLOCKING_VALIDATION_DEBT，不能因为nonblocking而声称已通过。
- A08_CURRENT_RUNTIME：新V4为ACCEPTED_SCOPED但production受限；无blocking不是runtime grant。

未扩展任何scope，也未以本轮报告关闭上述items。

## 9. 测试与环境结果

__TEST_SECTION__

## 10. 执行边界、接受结果与下一阶段

审计阶段合同：READ_ONLY_CODE_ALGORITHM_CONTRACT_REVIEW_AND_SYNTHETIC_COUNTEREXAMPLES_V1，HEAD固定，真实permission不变。证据：本目录及逐stage代码/合同引用。审计交付结果：**全阶段覆盖完成；局部Forward修复需要、全仓测试不绿、真实gate未通过**。本轮报告不是外部release接受。

下一步顺序：先独立复核IA-01/02，制定additive successor及其范围修复/向量；IA-09隔离环境先于新的全仓复跑；IA-03/04/07/08作为独立审计项处置；全仓/DB证据独立补齐。真实Shadow仅在冻结grant、有效daily input、对应consumer修复和独立验收齐全后，由新的授权任务推进。不得从本报告直接推断可切换生产。

本轮报告与证据需单独commit/push；保留起始用户未跟踪文件。没有改业务code/config/head/source输入。Git发布记录见同目录DELIVERY.json；发布不等于阶段外审或新权限。
'''
    text=text.replace('__TEST_SECTION__',(EVIDENCE/'TEST_RESULTS.md').read_text(encoding='utf8'))
    atomic(AUDITS/'V4_00_22_FEP_INDEPENDENT_FULL_SCOPE_AUDIT_R1_20261006.md',text.encode('utf8'))
    atomic(EVIDENCE/'audit_items.json',(json.dumps(dict(head=HEAD,authority='INDEPENDENT_AUDIT_ONLY_NO_PERMISSION_GRANT',items=ISSUES),ensure_ascii=False,indent=2)+'\n').encode('utf8'))

if __name__=='__main__':main()
