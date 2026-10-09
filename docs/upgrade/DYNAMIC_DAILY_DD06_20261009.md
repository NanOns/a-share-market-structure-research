# DD06 周/月计算合同与验收

执行依据：`V4-DYNAMIC-DAILY-R1.1` DD06 和 `V4_02_FORMAL_RAW_QFQ_PERIODS_V1`。本包新增版本化 IO 适配，私有作用域调用原 `_build_period` 字节码；不修改原算法。按目标 QFQ 坐标重新播放历史日线，RAW/QFQ 独立输出；周期视图由已验证日历计算，不查询远程周期接口。

证据：`docs/evidence/dynamic_daily_20261009/periods/QA.json`，真实 10/08 已接受 Owner 的当前月全市场与 32 证券完整窗口，共 RAW/QFQ 各 13,960 行；32 完整窗口重复执行逐字段一致。三项测试验证跨周月、累计 OHLCV/Amount、部分/收盘状态、停牌、缺口、复权未知与修订后的历史回算。

阶段接受：`PASS_REAL_OWNER_PERIOD_REPLAY`。输入历史首日之前的周期不作完整覆盖声明；对新日更必须绑定目标日完整性 QA 后的窗口。本包不代表动态发布链已完成，也不代替独立外审。下一阶段：DD03 完整 Owner 链绑定周期产物与新日数值验收。
