# 三个真实多会话递归案例

来源为已有独立 oracle 的实际输入和逐行 expected/actual，不重算既有充分验收样本。均为 corrected replay，历史首次可用未证明；9/30→10/08 按交易会话递进。

## SH.688349：未知前态至真实确认

竞争解释一：新增正式确认事实支持当前升级；更早会话缺必需判定输入，不能解释为当时已确认。

竞争解释二：技术反弹也可能形成同日正向条件；需要后续真实结构保持与失效条件区分，当前不保证持续。

|真实日期|前态|新增 F/R|计数器变化|下一状态与理由|
|---|---|---|---|---|
|2026-09-28|{"maturity": null, "validity": null, "tracking": null}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "FALSE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": null, "next": 0}, "expiry_count": {"prior": null, "next": 0}, "market_age": {"prior": null, "next": 0}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "NONE", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "CLOSED", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|
|2026-09-29|{"maturity": "NONE", "validity": "UNKNOWN", "tracking": "CLOSED"}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "TRUE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 0, "next": 1}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "NONE", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "CLOSED", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|
|2026-09-30|{"maturity": "NONE", "validity": "UNKNOWN", "tracking": "CLOSED"}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "FALSE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 1, "next": 2}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "NONE", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "CLOSED", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|
|2026-10-08|{"maturity": "NONE", "validity": "UNKNOWN", "tracking": "CLOSED"}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "FALSE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 2, "next": 3}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "NONE", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "CLOSED", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|
|2026-10-09|{"maturity": "NONE", "validity": "UNKNOWN", "tracking": "CLOSED"}|{"CONFIRMED": "TRUE", "PREWATCH": "FALSE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "LAUNCH_CONFIRM"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 3, "next": 0}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "CONFIRMED", "health": "IMPROVING", "validity": "VALID", "tracking": "ACTIVE", "final_eligibility": "TRUE", "transition_reasons": ["UPGRADE_IMMEDIATE", "ENROLLED"]}|

下一判别：后继真实会话的正式事实、失效和状态入口；未来未发生部分保持 WAIT_REAL_DAY。以上解释不涉及账户或资金行为。

## SZ.301628：硬失效优先于正向场景

竞争解释一：既有 episode 的硬失效证据优先，退出不被当天正向标签覆盖。

竞争解释二：日线反弹可能改善短期场景，但不证明旧 episode 恢复；新入组必须满足后续合法状态条件。

|真实日期|前态|新增 F/R|计数器变化|下一状态与理由|
|---|---|---|---|---|
|2026-09-28|{"maturity": null, "validity": null, "tracking": null}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "TRUE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": null, "next": 0}, "expiry_count": {"prior": null, "next": 0}, "market_age": {"prior": null, "next": 0}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "NONE", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "CLOSED", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|
|2026-09-29|{"maturity": "NONE", "validity": "UNKNOWN", "tracking": "CLOSED"}|{"CONFIRMED": "TRUE", "PREWATCH": "FALSE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "RECOVERY_TURN"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 0, "next": 0}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "CONFIRMED", "health": "IMPROVING", "validity": "VALID", "tracking": "ACTIVE", "final_eligibility": "TRUE", "transition_reasons": ["UPGRADE_IMMEDIATE", "ENROLLED"]}|
|2026-09-30|{"maturity": "CONFIRMED", "validity": "VALID", "tracking": "ACTIVE"}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "FALSE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 0, "next": 1}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "CONFIRMED", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "ACTIVE", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|
|2026-10-08|{"maturity": "CONFIRMED", "validity": "UNKNOWN", "tracking": "ACTIVE"}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "FALSE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 1, "next": 2}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "CONFIRMED", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "ACTIVE", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|
|2026-10-09|{"maturity": "CONFIRMED", "validity": "UNKNOWN", "tracking": "ACTIVE"}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "FALSE", "core_price_damage": "TRUE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 2, "next": 3}, "exit_session_index": {"prior": null, "next": 790}}|{"maturity": "NONE", "health": "DAMAGED", "validity": "INVALIDATED", "tracking": "FOLLOWUP", "final_eligibility": "FALSE", "transition_reasons": ["HARD_INVALIDATION"]}|

下一判别：后继真实会话的正式事实、失效和状态入口；未来未发生部分保持 WAIT_REAL_DAY。以上解释不涉及账户或资金行为。

## SH.600703：持续未知而非无资格

竞争解释一：现有已见事实可能偏弱，但必需输入未知，尚不足以作正式否定。

竞争解释二：部分条件也可能支持后续改善；缺源期间无法裁决，先补真实输入，不以 UNKNOWN=FALSE 排除。

|真实日期|前态|新增 F/R|计数器变化|下一状态与理由|
|---|---|---|---|---|
|2026-09-28|{"maturity": null, "validity": null, "tracking": null}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "FALSE", "core_price_damage": "TRUE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": null, "next": 0}, "expiry_count": {"prior": null, "next": 0}, "market_age": {"prior": null, "next": 0}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "NONE", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "CLOSED", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|
|2026-09-29|{"maturity": "NONE", "validity": "UNKNOWN", "tracking": "CLOSED"}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "FALSE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 0, "next": 1}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "NONE", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "CLOSED", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|
|2026-09-30|{"maturity": "NONE", "validity": "UNKNOWN", "tracking": "CLOSED"}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "FALSE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 1, "next": 2}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "NONE", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "CLOSED", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|
|2026-10-08|{"maturity": "NONE", "validity": "UNKNOWN", "tracking": "CLOSED"}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "FALSE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 2, "next": 3}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "NONE", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "CLOSED", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|
|2026-10-09|{"maturity": "NONE", "validity": "UNKNOWN", "tracking": "CLOSED"}|{"CONFIRMED": "UNKNOWN", "PREWATCH": "FALSE", "core_price_damage": "FALSE", "frozen_invalidation": "UNKNOWN", "risk": "LOW", "scenario": "UNKNOWN"}|{"downgrade_count": {"prior": 0, "next": 0}, "expiry_count": {"prior": 0, "next": 0}, "market_age": {"prior": 3, "next": 4}, "exit_session_index": {"prior": null, "next": null}}|{"maturity": "NONE", "health": "UNKNOWN", "validity": "UNKNOWN", "tracking": "CLOSED", "final_eligibility": "UNKNOWN", "transition_reasons": ["REQUIRED_FACTS_UNKNOWN_PRESERVE"]}|

下一判别：后继真实会话的正式事实、失效和状态入口；未来未发生部分保持 WAIT_REAL_DAY。以上解释不涉及账户或资金行为。
