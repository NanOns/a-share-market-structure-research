# 独立审计项：Focus 停牌缺口使价格路径永久不可用

## 范围与证据

横跨股票观察价格路径及股票到期结果；与连续交易日谓词、板块 NAV 算法分开验收。旧 `reanchor_from_frozen_coefficients` 要求信号日至观察日每个主交易日都有实际行情，因此中间已证实停牌、后来复牌的路径仍返回空。未核实的数据缺口不能与停牌合并处理。

## 修复

新增 `FOCUS_ACTUAL_TRADED_PATH_V1`。仅在首尾有实际行情、且中间缺口全部由生产数据状态合同标记 `CONFIRMED_SUSPENSION`，同时 `trade_status_known=true`、`is_synthetic_fill=true` 时，用实际成交日的本地同一复权坐标计算累计收益、MFE、MAE、回撤。`INFERRED_GAP`、`MISSING_DATA`、`FILE_MISSING` 或未知缺口仍使价格指标不可用。记录缺口总数、停牌数、未核实缺口数及对应日期；输入摘要包含完整主日历、原始切片和实际参与日期。观察输入升级为 `FOCUS_OBSERVATION_INPUT_V2`，到期结果计划升级为 `FOCUS_OUTCOME_TARGET_PLAN_V2`。连续谓词继续按完整主交易日历，停牌日不能算作实际行情。

## 独立验收

合成四日路径（第 2 日审计确认停牌、第 3 日复牌、第 4 日观察）得到 READY，收益 0.3、MFE 0.4、MAE -0.1、当前/最大收盘回撤 0；结果路径覆盖率 0.75。把缺口改为 MISSING_DATA 则两条路径均不可用；把停牌设在首日或目标日同样不可用；两日连续失效谓词遇停牌维持 UNKNOWN。状态标记与审计标记矛盾会失败关闭。Focus 测试 121 项通过。

用户提示的星帅尔 `SZ.002860` 在 9 月 21 日曾是 V3.3 候选，但不在 23 日 Focus episode 或冻结板块篮子。23 日已接受标准化数据的 22、23 日状态均为 `MISSING_DATA`，没有后续复牌行情，也没有 `CONFIRMED_SUSPENSION` 审计状态。对该真实切片的只读路径返回 `DATA_UNAVAILABLE`，`gap_count=2`、`suspended_dates=[]`、未核实日期为 22、23 日、收益为空。该结果验证未知缺口失败关闭，不能充当已确认停牌复牌的正向样本。全量标准化文件目前 `CONFIRMED_SUSPENSION` 行为 0。
