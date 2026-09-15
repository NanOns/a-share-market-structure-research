# P12-08F 第二个真实前向观察日验收

## 阶段合同

本阶段依据 `V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md` §17 与 P12-08，以及 P12-08E 的下一步约定，使用已完成的 2026-09-15 publication 重建同日 P12-03 漏斗、P12-04 LOO/排名、P12-06基础包和 P12-08E报告维度包，并封存第二个真实前向观察日。历史回放不计入前向日期，不进入参数校准，不物化未具冻结评价源的后验结果。

日常脚本由硬编码 2026-09-14 改为选择最新 `COMPLETE` research run，并从该 publication 的 `LOCAL_RECONSTRUCTED` snapshot 绑定当日 strength/technical slice。报告对同一交易日的多个不可变修订只选择一个规范修订，优先维度完整者；信号日按不同交易日计数。episode 身份完整性按逐行身份覆盖判断，连续 episode 不再被误判为缺失。

## 验收结果

**DEGRADED_PASS**，第二真实日封存和迁移验收通过，效果观察仍待足量日期。

15日输入绑定 publication `m4-29c93e09369982707899ab863c869ea1`、research run `research-1f70afc1e97d4439bd841c43f4509715` 和 snapshot `m10-mainline-preview-1e7e6c870ee93532`。当日共有58只合格股票，其中 `LAUNCH_CONFIRM` 53只、`TREND_CONTINUE` 5只；`INDEPENDENT` 44只、`SUPPORTED` 14只。维度完整 bundle 摘要为 `32c895eae1f40ffd510b901c688d4815575288e3e7b6dd0e8b7eb2efda3955d2`，58/58具市场强弱和波动。

15日前向观测摘要为 `ddd2da4a585a081935a2dfeb2f2592c01547ab6958726ccd92c51ca800ddf833`。相对14日：50 `ENTERED`、105 `EXITED`、7 `CONTINUED`、1 `MODE_CHANGED`。规范报告现为2/20个真实信号日、163个唯一 episode、171条逐日候选记录，episode 身份覆盖 `AVAILABLE`；市场强弱、波动、流动性及行业/概念关系维度171/171可用。

P12 相关回归 59 passed，compileall 和 `git diff --check` 通过。未修改 TDX，未进入校准。

## 下一步

14日信号的1交易日后验已到期，但当前没有冻结评价源，物化器以 `DUE_ROWS_REQUIRE_FROZEN_EVALUATION_SOURCE` 正确阻断。下一阶段应独立冻结15日评价源并物化14日 h=1 revision；通过验收后，再继续等待第三个真实收盘观察日。
