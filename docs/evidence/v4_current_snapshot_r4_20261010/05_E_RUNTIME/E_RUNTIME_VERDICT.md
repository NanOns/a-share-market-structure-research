# R4-E 生产加载与 FP13

状态：PROD_RESTART_PENDING。真实 PID 41528、启动命令和10路实际HTTP读取均已记录；生产返回 OPERATIONAL_SUCCESSOR_BFF_V1，而不是本轮 CoreProductBFF。运行进程模块SHA未被证明，磁盘SHA不用于替代。现有每日操作handler不提供正常停止入口，没有强制停止。

已准备现有产品正常启动与运行模块取证入口 scripts/start_product_attested_r4.py；占用28765时已实测拒绝启动，不更改原进程。用户按现有正常方式关闭后才可启动该入口。运营Head、严格PIT Head保持原SHA。

浏览器：IAB本机地址返回net::ERR_BLOCKED_BY_CLIENT，Chrome不可用，双尺寸DOM/生产故障恢复未验收，FP13_FULL_NOT_GRANTED。10路HTTP SOURCE_INCOMPLETE只证明缺源表现，不签业务字段PASS。

六维：FORMULA_LOGIC=PASS_SCOPED（正常启动占用门）；DATED_INPUT=PASS_SCOPED（10/09）；FORMAL_OWNER=NOT_AUTHORIZED（新能力）；API_UI_BINDING=NOT_TESTED（新版真实生产DOM）；HISTORICAL_AS_RECORDED_PIT=UNKNOWN；FUTURE_MATURED_OUTCOME=SOURCE_NOT_PRESENT。
