# AUD-LEGACY-IDENTIFIER-REGEX R2 版本化订正

BASE_SHA：5f4cc15f4809ee4e50ff283ce6b92115fda9f253。原报告保留，不覆盖。

正式撤回原报告“冻结 phase2 与 legacy A05 使用双转义错误”的归因。两份旧源均为正确单转义；错误实际来自本轮新增 operational_candidate_v1 的复制/再写。FROZEN_SOURCE_ORACLE.json 与 frozen_source/ 提供四份原字节、路径、字节数、SHA 和纯 Python 实际反例。原 V1 标准 SH/SZ/BJ 全失败，旧 phase2/A05 与 V2 全通过。新定点测试再以 pandas prepare 原函数和纯 Python exact_value 成对复核。

原 400 板块全 FALSE 主要受错误 adapter 影响，不能证明旧正式算法故障。R2 79 TRUE 属未经完整资格口径审计的研究诊断，不能业务准入。此次修 V1 适配器，V3 在新路径追加审计诊断；旧 V1/V2 数据原件与第一次诊断未重写。正式 A05、phase2、AST 和两个 Head 均未改变。

旧资格为 identifier、missing_state.notna、排除 FILE_MISSING/DELISTED_OR_INACTIVE 的合取。NOT_LISTED_YET 或其他非空未知字符串在旧表达式中仍可能 TRUE；Lifecycle ACTUAL_TRADED/SUSPENDED 映射并不等价。原值缺失（字段不存在）是 UNKNOWN，显式 null 的旧表达式结果才是 FALSE。缺 source_security_key 不能算观察到的 FALSE。测试涵盖正常、停牌、未上市、退市、更名、缺源与边界。

市场资格分母还受 IN_NORMAL_UNIVERSE 限制；板块成员资格不自动叠加市场 normal，而 sector_valid 另受总数、有效数、70%覆盖和 role 门约束。不能把这三个维度混为一体。资格合同仅 CURRENT_SNAPSHOT_ONLY，同一目标日期；不允许以 10/10 重建证明 10/09 首获。REAL_1009_QUALIFICATION.json 提供逐来源三值及抽样；V3_APPEND_ONLY_REPLAY.json 是单独追加研究结果，独立 golden 9/24 不足开放 10/09。

独立审计项继续 OPEN：缺失 legacy missing_state 的真实源仍需独立 Owner 复核。工程订正可复验；正式 A05/D2 未授权。验收不以维持 79 个 TRUE 为目标。
