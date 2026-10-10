# TASK C｜D2六字段与未来Episode出生接口

日期：2026-10-10（Asia/Shanghai）。exact_BASE：`c0b9903fe596c1884c04f5529d6699034548850e`。
本轮工程结论为 `PASS_SCOPED_PENDING_INDEPENDENT_REVIEW`；正式D2仍为 `NOT_GRANTED`。未创建真实历史Episode，未修改受保护Head，未重启28765。

执行依据：桌面总调度TASK C和整体外审R1、仓库V4.2.2 REV4合同第78节、冻结R5 B2机器AST、A05 9/24黄金范围、现有Sector Producer R1与V4-15原结算接口。逐字段代码、原件SHA、合法出生时点和下一次来源时点见 `C_D2_SOURCE_AND_EPISODE_GENESIS_MAP.json`。外部Owner的签收与生产writer权限独立于字节校验，代码不能给自己授予。

## 正式字段与研究输出

| 字段 | 目前真实来源 | 允许当前呈现 | 正式准入缺口 |
|---|---|---|---|
| CONFIRMED | 10/09 V2研究候选，原R5/phase2 AST与日期Core、Native、资格原件 | 研究TRUE/FALSE/UNKNOWN | 新T0合法首获、A05日期范围与逐字段Owner独立批准 |
| WARM | 同一研究候选、原BASE/BREADTH/RECOVERY AST | 研究TRUE/FALSE/UNKNOWN | 上述源，加各分支必需Amount H21等；不能跳过AST中的必需项 |
| frozen_invalidation | 无先前真实Episode | NO_PRIOR_EPISODE；有出生后缺事实UNKNOWN | Creation-bound失效AST与之后真实日期事实Owner |
| episode_invalidation_contract_id | 无先前真实Episode | NO_PRIOR_EPISODE | 原始出生时冻结的contract ID/version/SHA |
| followup_complete | 无先前真实Episode | NO_PRIOR_EPISODE；未到期PENDING；到期缺结算UNKNOWN | 原calendar due plan、T+1/3/5原结算字节和来源身份/时钟 |
| scenario | 无先前真实Episode | NO_PRIOR_EPISODE | 出生当日匹配原件及版本化priority，按优先顺序冻结 |

9/24既有黄金的3,553成员、6,188资格观察、541板块0差异只覆盖其原日期。此处引用既有原件并记录SHA，未再次全量执行黄金。不能据此开放10/09正式D2。原missing_state缺源仍为UNKNOWN，不能以无BAR、ret1可算或当前Native资格直接当FALSE/真资格。

## 可运行候选接口

新增 `src/sector/episode_genesis_candidate_v2.py::create/observe`，保留原候选与冻结R5算法不变。
`create` 从capture、当日板块membership、conditions、priority、price、calendar六个精确字节绑定读取；检查当前真实时钟、原first_available/received/captured先后、日期实体、AS_RECORDED名册与scope、版本/可用时钟、有限正价格。不能把全市场subset充当板块成员原件；priority实际决定primary scenario。创建输出不可覆盖，绑定原成员和原AST，并直接复用V4-15 `due_plan`，不新造结算定义。

`observe` 重验所有出生绑定，使用原冻结AST评价失效，并复用现有followup。无先前Episode返回NO_PRIOR_EPISODE；未成熟PENDING；到期缺合法settlement返回UNKNOWN。结算须有精确原字节、对应Episode/到期日、Creation-bound成员和非未来可用时钟；提前拿未来settlement会失败。真实candidate不能观察未来日期。所有输出 `production=false / formal_D2=NOT_GRANTED`。

该接口是工程候选形态，未加入真实DailyJobs写入或正式D2 consumer。合成fixture明确 `SYNTHETIC_ISOLATED_TEST_ONLY`；周末模拟calendar只用于函数隔离，不能成为真实交易日/来源/分母证据。当前实际Genesis来源尚未发生。最早下一步为10/12真实采集之后逐字段来源外审；日期到达本身不授予任何字段权限。

## 独立rank与非Amount核查

`tools/next_stage_c_oracle.py` 从10/09已冻结候选的绑定技术/成员/calendar读取，使用标准库statistics与计数，未调用strength/cycle/rank producer：

- 从四个日期的原Core/prewatch独立重算 `normal_universe=true + OBSERVED RET5/RET20` 的同日市场median差，检查41,790个RS字段。
- 按板块成员median RS、sector_type独立cross-section、average-rank/N重新计算q20；以真实calendar前3session及原coverage稳定条件重新计算dq5_3。400板块×2字段共800项，0差异。
- 名册是明确的latest-member历史研究回放；数值相符不升级历史PIT。原件和800项SHA回执见 `C_RANK_NON_AMOUNT_INDEPENDENT_ORACLE.json`。

定点反例额外覆盖ties、UNKNOWN rank、分类隔离和新增成员导致cross-section不稳定时dq5_3缺值。原R5 confirmed_raw叶子不依赖Amount A；独立手算边界向量在Amount缺源时仍能给研究CONFIRMED，原正式raw仍UNKNOWN。三个WARM分支都确实含Amount A必需叶子，不能伪称WARM已摆脱H21。H21缺20历史当时成员只阻断该依赖范围，Native/Core读域与无Amount研究CONFIRMED继续独立工作。

## 验收与下一阶段

命令：`python -m pytest tests/test_next_stage_c_episode_genesis.py tests/test_producer_bootstrap_v1.py tests/test_pre_next_t0_publisher.py -q --basetemp=G:/codex_tmp/test_temp/task_c_final_2 -o cache_dir=G:/codex_tmp/pytest_cache_c --junitxml=G:/codex_tmp/C_TEST_RESULT.xml`。TMP/TEMP/TMPDIR均G:/codex_tmp，禁写Python bytecode。

结果：49 passed，0 failed；为工程节点，不是49次交易、真实Episode或正式样本。新接口正向验证完整冻结→失效AST→PENDING→到期UNKNOWN→合法原字节settlement；反向包含历史backfill、未来cutoff、假AS_RECORDED、变化成员/重复成员、错误SHA、迟到first clock、错误scope、缺AST版本、错误scenario、future settlement和错误Episode。

下一阶段：实际未来当日Genesis原件发生后，以六字段各自Owner、cutoff、合法成员与原件独立审查；允许局部申请 `SECTOR_D2_FIELD_ADMITTED`。无独立签收之前研究consumer继续显示；不调用正式reducer，不开放生产D2。
