# 大A V4｜R4.3 R2 最终独立准入、最小兼容核对与 10/08 生产切换任务卡

- 版本：R4.3-R2 / 2026-10-09；唯一输入 `NanOns/a-share-market-structure-research` 分支 `codex/v4-fp14-r2-repair`，当前 HEAD `4e344156564338cda185fd44505c1273cf8bfdca`，启动时先核对最新 HEAD 和 `AGENTS.md`。
- 正式依据：《V4_R43_R1_独立复审与生产阻塞根因_20261009.md》、旧 R4.3 四日数据合同、R4.3 R1 工程交接；唯一候选 `R43_OPERATIONAL_SUCCESSOR_CANDIDATE_V2.json` SHA256 `9c42365c777df3facf13b31639102f11c4e8321536de33af965213f71e04c55e`。任何修改候选则更新摘要并重新审签。
- **本卡不授权修复代理自签外审、手填 PASS、绕过 CAS 或将最新 TDX 成员冒充历史 T0。** 但授权其一次性准备完整、可复核、可执行的独立签收与正式发布程序。外审有真实通过后，必须继续执行生产切换；不得再以旧阶段授权泛称停工。
- 总顺序：P0 复核/修复 → W7 独立外部验收签收 → W7 正式运营 Head CAS/真实服务读回 → Drive 归档 → 开始 FP01–FP14 页面完整性任务。

## P0-A：禁止重做已经过数值复核的四日基础 Owner

1. 确认 4 日 canonical RAW 5210/5211/5213/5209、停牌 12/12/11/15、原价/复权/Core/Profile/ RPS、最新单一 TDX S `44f6d2c7...` 与 55,136 成员关系及所有 400 板块计算继续沿用原真实冻结 SHA。对原 9/30 frozen Head 不写入。
2. 最新 S 是 `RECONSTRUCTED_LATEST_MEMBERSHIP`、`AS_RECORDED=false`、`PIT_ELIGIBLE=false`、`survivorship_bias_risk=true`，401 个源组中 1 个 T00 无有效成员不造假；行业为 110 合法叶级+22 派生父级+1 T00，占位不算第23个父级；BaoStock CSRC 不替代 TDX。
3. Git LFS 实际对象及既有 Drive 17 段原正式归档按必要范围取证；审计者独立验证 SHA/输入域、数值样本、真实来源与 10/08 可见性。**Full Rotation 状态机如未独立验算，仅保留 `VALIDATION_ONGOING` 或具名质量状态，不得声明独立全量 PASS**；先提出非状态机域可独立放行的明确矩阵。

## P0-B：真实发布前的最小控制面一致性修复

1. 审查 `src/workbench_service/v4_server.py`：现 `/api/v4/context` 随运营 Head 读取 10/08，但 `/api/operations/status` 仍调用旧 `CurrentAcceptedV4Reader`，会在切换后向运营监控继续报告 9/30。必须明确区分 `current_operational_trade_date` 与 `strict_pit_legacy_trade_date`；若界面要求当前日期，只取同一个真实运营 head/token。保留旧历史接口可见，不重写原 9/30 Head。
2. `src/workbench_service/r43_operational_bff.py`、兼容 JS 已通过隔离测试，务必在正式外审范围下复核真正 `SIX_ENTRY` 主页面没有被 `r43-operational-preview` 顶替；灰度状态下所有已经正式接入的 stocks、sectors、market、focus 同版本读数一致。
3. 对未接的 Forward 统计、完整行情图表、replay/compare、Market 子页等标注准确 `SOURCE_INCOMPLETE`。旧页面若已有依赖这些路由不能无提示全白屏；最小读取修复属于切换 QA，不提前执行 FP 全量产品建设。

## W7-C：签发真正独立且按域限定的外部验收对象（不可由 Codex 自签）

在 `docs/evidence/.../R43_R2_EXTERNAL_REVIEW_SCOPE_AND_DISPOSITION.md` 形成逐域 PASS/FAIL/NOT_VERIFIABLE：原始 4 日、源哈希、GBBQ 事件、证券身份/BJ optional、复权 Core/Profile、TDX 最新 S、400 板块/LOO、Rotation 边界、UI 路由、权限与回滚。分别写明所审实际文件 SHA、候选摘要、审查人/时间/工具、未覆盖域与准入边界。

1. 审查人不等于执行修复任务代理；不得以 `R43_R1_SCOPED_NUMERIC_REVIEW_RECEIPT.json` 这份开发方自测签名冒充外审；没有实际触达的 Git LFS 字节要保留 NOT_VERIFIABLE。
2. 检查源码中的正式门需要固定路径 `data/v4/R43_OPERATIONAL_EXTERNAL_ACCEPTANCE.json`，`status=EXTERNALLY_ACCEPTED_R43_OPERATIONAL`、`candidate_digest=9c423...`、`historical_PIT_permission=false`。这只是运行时字段校验，**还需在流程上对审查身份/证据真实性追溯**，不得生成无独立审查者的同名文件。
3. 如果某项只有领域级未签，不得阻止与该项完全无依赖、已真实可证的研究展示；但也不得因为产品急于上线而改写合同假冒完整 Rotation/PIT/实时分时数据。确立显式子域准入版本，所述范围须与 `cas()` 的验证合同一致。用户早已授权运营研究产品切换，不需要重新要求用户批准“可以开发切换脚本”。

## W7-D：独立记录通过后，立刻执行真实 10/08 CAS，不能再只演练

1. 建立/使用一个受控、一次性 **正式运营发布 CLI**（例如 `scripts/promote_r43_operational_v1.py`），从指定候选加载并检查精确 SHA、外部签收、完整源/代码 Registry、expected predecessor、服务停写/锁、头指针路径、回滚；支持 `--dry-run` 与显式 `--promote`，绝不能静默创建假的签收。工程主体现已有 `workbench_analysis.r43_operational_publication.cas()`，不要重写一套数值生产者。
2. 有真正独立的 R43 外部接受后，调用生产 CAS 更新 **`data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json`**，历史 `data/v4/V4_DATA_ACCEPTED_HEAD.json` 完全不改。若签收仍缺，只交准确外审未决事项，不许重算 RAW 也不许称已生产上线。
3. 实际运行中的服务须真实发 HTTP：`/api/v4/context` 的 `accepted_trade_date=2026-10-08`；其余同 token `stocks`、`sectors`、`relative_sector`、`rotation`、`market`、`focus` 等 4 日范围可核查；`/v4`、`/v4/` 仍为原正式研究页面；`/v4/operational-preview` 仍独立；`/api/operations/status` 与 context 的运营最新时间一致，旧 `original-0930` 保持 9/30。检查跨日期流量/旧 token 拒绝、CAS 回滚和服务重启后的同版读取。
4. 出具 `R43_R2_LIVE_CUTOVER_HTTP_AND_ROLLBACK_RECEIPT.json`，必须包括本机服务 URL/端口、真实生产 head SHA before/after、旧 Head SHA、HTTP 响应摘要、token、页面 HTML 摘要及最终发布结果。**没有真实这些证据则 `FOUR_SESSION_PRODUCTION_ACCEPTANCE_PASS` 不成立。**

## P1：归档与进入 FP 后续

- 本轮 R1 本地增量 `E:/codex_tmp/R43_R1_TARGETED_REPAIR_DELTA_20261009.zip`，964,009 字节 / 68 文件，工程计算 SHA `ec27612dd557a4bfff681f40c0cbcc9c8d77992bfb1a25cca4f4b208e5a3f093`；Codex 局域上传失败时可交由 Google Drive 连接器代理传输，或从 GitHub/LFS 字节在可联网端恢复打包并上传。之前 R4.3 Drive 17 分段已归档，不需重传 1.13GB 整包。
- 同轮上传 R4.3 R2 外审签收、实际切换、最终收尾文档并回读。Drive 成功为正式归档闭环；单纯本地 ZIP 不能谎报云端已同步。
- 真实 R4.3 运营数据与 API 最终 PASS 后，自动进入已归档 FP01–FP14 的完整前端缺失模块修复；不等待未来20天数据积累或胜率统计成熟。

## Codex 一段式启动指令

以 `4e344156` 为起点严格执行 R4.3 R2。不要再重抓四日行情、重算稳定的 55,136 TDX S 和原 528 QFQ。先审计生产 `context` 与 `operations/status` 两套时间口径，在合法运营 Head 情境下修复控制面混用 9/30 的风险；确认现有6入口页面依然正常、已有领域可读、无证领域明确降级。整理供真正独立审查者签收的最终候选 SHA `9c42365c...` 和所有真实 source/numeric/UI 证据，不自签 `EXTERNALLY_ACCEPTED_R43_OPERATIONAL`。拿到外部真实准入后必须实际调用 `r43_operational_publication.cas()` 并完成生产 10/08 `/api/v4/context`、股票/通达信行业概念/LOO/市场/Focus、页面和回滚的真实同 token 读回，不允许再次只交隔离 CAS PASS 后停止。若签收仍未获得，只报告精确证据缺口及唯一待外部动作；并行归档 R1 增量证据至 Drive。正式切换通过才进入 FP01–FP14。
