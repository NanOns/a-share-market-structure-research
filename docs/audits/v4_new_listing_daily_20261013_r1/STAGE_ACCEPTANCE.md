# 新股增量修复与日更验证 R1

阶段合同：V4_CURRENT_OPERATIONAL_NEW_LISTING_R1_20261013；用户明确要求修复今日新股并开始日更验证。

修复验收：PASS_CURRENT_IPO_IDENTITY_AND_REAL_DERIVATION_ENTRY。新增股票不再要求与前任证券池完全相同；通过有请求边界的股票基本信息、当日两源原生行情对照、上市日/类型/状态/唯一ID校验后，追加不可变身份。未删除原始行情、未更改旧身份或旧Head。

SZ.301660 的真实股票基本信息上市日为2026-10-13，创业板A股；原5224身份逐行保留，新增1条。独立稳定ID计算一致，当日OHLCV两源精确相同，官方ZIP仅一根13号日线；首日周月边界检查通过。8项日期/错码/重复/冲突/状态负例测试通过；新冻结包导入和PG生命周期QA通过。既有算法和政策资源SHA不变。

新包 V4_PACKAGE_1.0.0_ef5f1ec494dc / PID24736 已在原28765运行，AUTO恢复。第5次真实scheduler任务在新股版source_ready=true后进入DERIVING。当天lifecycle为5225，新身份同时进入generation和实际Core SOURCE_BINDINGS。完整Core/Profile/板块/Focus/周期/PG/发布验证仍在运行，未写日更成功。后台健康计算不中断，不启动重复任务。

发布验收：IN_PROGRESS_NOT_YET_PUBLISHED。当前仍读12号last-good Head。后续退出条件：原数值oracle与生命周期/周期守恒通过，PG原子发布成功，实际IPO Core/history/不足历史UNKNOWN读回及七路API统一13号日期/token；验证程序 scripts/verify_new_listing_daily_r1.py 已准备。

下一阶段：完成正在运行的实际派生及发布读回。本记录不授予全产品/PIT/交易，既有历史接受不被新股事实改写。
