---
stage_id: V4_R21_R4_DM01_CONFIGURED_PATH_AND_PG_ACCEPTANCE_WIRING_R67_20261017
branch: codex/v4-workspace-cleanup
status: PARTIAL_CONFIGURED_PATH_CODE_LANDED_DM01_ORCHESTRATION_ADMISSION_BLOCKED
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 48
open_callsite_rows: 210
ingress_adapters_open: 8
remaining_open_or_ingress: 218
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# V4 R21-R4 DM-01 path and acceptance wiring R67

日期：2026-10-17（Asia/Shanghai）。执行前重新读取正式 R21-R4 Drive 任务卡，并核对分支、Issue #2、PR #3 和 CI。R67 延续 R66 的实际日更路径，处理当前 DM-01 入口的 TDX 路径及 BaoStock runtime acceptance。

## 可提交代码与待解决编排

- `run_dm01_a01_next_session_r1.py` 的 GBBQ 源目录从中央配置解析；GBBQ probe API 改为必须显式传入已解析源根，移除隐藏盘符默认值。
- 在工作副本中，我还将活跃日更、lifecycle、special-phase、source-freeze 和 BaoStock 入口改为中央路径及 PG runtime acceptance。代码与受控回归在工作区通过，但暂不纳入提交。
- `tools/git_repository_policy.py --staged` 对六个上述编排脚本报告 `PROCESS_DATA_DEPENDENCY`：它们仍在同一模块读取 `reports/v4_*` 历史/动态业务证据。不能靠改名或豁免解决。需要先把对应数据映射到语义正确的 PG Head/Owner/source relation，并让消费链从该 PG relation 读取。
- DM-01 正式采集成功后会由 `accept_dynamic_daily_baostock_v2.py` 调用 `append_from_files` 写入 PG runtime acceptance fact；这是可复用的真实写入适配器。尚未证明 lifecycle、special-phase、source-freeze 及其历史输入在 `v4_daily_source_ingest_r6`、Owner `forward_facts` 或 scheduler relation 中有等价身份。尤其不能把这些不同业务事实拼进 scheduler job-progress。

## 验证与限制

- 工作区定向回归：**74 passed**，覆盖当前配置路径、GBBQ probe、BaoStock acceptance 调用和 daily executor PG bridge。
- 另一次包含较宽 `tests/v4_dm01_r4/test_runtime.py` 的回归为 **2 failed、1 error**：两项历史链测试因隔离测试副本中的固定归档 SHA 与 registry 字节不符失败；一个测试因 `G:/codex_tmp/v4_full_closeout_20261012/denominator` 目录缺失无法写历史时钟凭据。没有更改历史基线或补写该凭据。
- 未运行外网 BaoStock smoke、实际 PG append/read、TDX 源采集或业务 Head CAS。没有 PG DSN 时，日更现场步骤会停在 PG 权威读写错误；没有写入尝试。

## 原 266 项核对及准入状态

本批文件没有引入可独立匹配到原 266 清单的新稳定 ID，也没有满足 live readback/业务验收条件的既有 ID。故原 P1 正式完成仍为 **0/266**，正式剩余 **266/266**。矩阵当前为 **48 项代码级 PG 读取待现场/库存对账、210 OPEN、8 ingress OPEN；合计 218 OPEN 或 ingress，22 条 reference edge 未映射**。其中 28 条其他业务读取为 4 项代码级路径待对账、23 OPEN、1 ingress；200 条 Owner 读取为 44 项代码级路径待对账、149 OPEN、7 ingress。

R67 可提交部分只覆盖 next-session probe 的 TDX 路径和 GBBQ probe API；这些不匹配新增 266 ID。另有日更链改动仍留在工作副本，不计作交付或正式完成。BaoStock supplemental schema adapter 当前仍带 `CANDIDATE_SCHEMA_ADAPTER_PENDING_EXTERNAL_REVIEW`，不能擅自提升为批准合同；其正式 Registry 身份/审批仍需合同审批现场条件。

## 后续

继续推进可安全接入现有 PG Authority 的 Head、descriptor、Owner/BFF 和其他业务消费者；逐项登记原 ID 与正反向证据。DM-01 admission blocker 要通过识别真实 lifecycle/special-phase/source-freeze Owner 关系解决，完成映射前不得提交仍触发 `PROCESS_DATA_DEPENDENCY` 的编排脚本。保持真实 PG 读写、正式 Head CAS 与历史合同审批现场步骤为明确阻塞，同时继续其他代码、测试和 CI。
