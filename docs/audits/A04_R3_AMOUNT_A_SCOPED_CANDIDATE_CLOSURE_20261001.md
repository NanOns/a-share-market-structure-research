# A04 R3：板块 Amount A scoped candidate

本轮基线 `66ef2e342dd339cc9795c2d1fd774b8edec4c345`。读取 Master R2、A04 R3 卡及独立 10 卡验收；实际独立审计只接受既有 A04 工程机制，仍标 `ENGINEERING_PASS_FORMAL_AUTHORITY_BLOCKED_R3`。本轮不把这项历史工程接受升级为新 formal authority。

## Namespace 与权限

machine-readable namespace 合同冻结 `Amount A = SECTOR.amount_a_value`，映射旧 sector_amount_vs_prior20 / amount_A / current_sector_amount_vs_prior20。明确排除 STOCK.amount_ratio20、STOCK.amr20_mean_prior、AMOUNT_VOLUME_STATE_V1、普通原始 AMOUNT 与成员个股金额比中位代理。普通金额是算术输入；它的 owner 不是 Amount A 的 owner。A04 status/rows 不得成为个股 stock confirmation 的 gate。

## 5 / 0.80 的实际归属

已按原字节绑定并逐行考古：

- M10_AMOUNT_A_DESIGN_DECISION_V1 §2.2 和 M7-M15 §27.2.2 将 5 与 0.80 标为首版预览工程质量参数，明确不证明最佳经济参数。
- MAINLINE_STATE_V2_4_PREVIEW 将它们纳入自身 Amount A local preview quality gate；sector_amount.py 的常量是该预览参数的实现默认值。
- 最高 REV4 SECTOR_FACTORS_V1 / SECTOR_QUALIFICATION_V1 的 5 与 0.8 是 Core member_count / quote_coverage 安全门。报价覆盖分母不能替代 Amount A 的 comparable-member / H21 amount coverage。
- V4-08 parameter set 对 Core 门同样标 FROZEN_CANDIDATE，不能转成 Amount A universal accepted threshold。

因此新 producer 没有统一 threshold，不把 5/.8 擅自声明为 universal authority。消费者使用权限由逐 consumer 的版本化已接受 gate 决定，本轮所有新 formal adoption 均 false。

## 算术与 consumer gate 分离

新 `AMOUNT_A_FORMAL_AUTHORITY_GO_FORWARD_V1` 输出 amount_a_value、comparable_member_count、target_member_count、coverage、window_coverage、quality reasons 和 contract_id，并保存精确 H21 session list、共同成员、CNY 分子/前 20 session 均额分母。

完整 source/membership 且分母正时直接输出算术值，即使成员不足 5 或 coverage 低于 0.8；这些都不是新 producer 的 universal gate。测试证明完整三成员得到 5/3，完整共同两成员但新增成员使 coverage=2/7 时仍有值 2，consumer permission 继续 false。成员来源、原始金额、dated status、单位缺失仍 UNKNOWN；真实确认停牌零额可以产生已知 0，未确认零不补造。前 20 合法 market sessions 不能用 20 rows 或更早缺口填补。

## 真实 H21 与 go-forward warmup

搜索并分类 baseline 的 23 个 membership 相关 source/head/evidence artifact，当前唯一可证明的 sector accepted/PIT observation 日期是 2026-09-30，真实 accepted facts 50,162 行。historical identity/current interval 不是历史 sector PIT authority。

从已接受 Data Head 9/30 的 exact RAW_DAILY / IDENTITY_UNIVERSE / TRADING_STATUS 与 exact V4-08 accepted membership source 建立不可变 observation。它覆盖 378 个行业/概念板块。candidate 378 行全部是 WARMUP/UNKNOWN：H21 的前 20 session 没有 accepted/PIT membership，因此历史 formal Amount A 为 `PRE_BASELINE_HISTORICAL_AMOUNT_A_NOT_FORMALLY_RECONSTRUCTABLE`。不把当前快照回填历史，不等待未来 21 个交易日。

R3.1 source-admission layer 又验证完整 V2 accepted chain/component hashes，并沿已接受 Stage Head → V4-08 Accepted Head → membership binding 校验输入，拒绝自行声明 accepted 的任意 JSON head。源 admission replay 产生原 observation / candidate identity，旧 R3 工程证据保持原字节。

当前日命令 `E:/python/python.exe scripts/run_a04_go_forward_r3_1.py` 幂等追加实际 accepted observation 并生成 immutable candidate。后续新的正式 Data/membership publication 必须经相应版本化、独立接受的 source contracts 入场；命令不会自行升级 source trust root 或移动 Head。

## Consumer 逐项隔离

inventory 分别记录 V4-08 legacy B2 Amount A rules、M10 NEW/REACCELERATING、M10 FADING、research sector potential、UI/API display 和 stock confirmation。

V4-08 B2 的 Amount A rules 继续 diagnostic/UNKNOWN，未来 go-forward 使用须同时独立接受 producer、B2 amendment、B2 自身质量门及其他 exact AST 输入。M10 NEW/REACCELERATING 单日 A 需要 H21，FADING 独立共同集合变化仍需要 24 session，不能直接拿两个单日 A 相减。旧 local preview 不改义；R3 候选不注入旧消费者。UI 仅展示 diagnostic quality/lineage，不把显示值当资格。Stock confirmation 完全不依赖 A04。

## 候选结束边界

工程、真实当前 observation、exact replay、threshold archaeology、H21 scope 和 consumer inventory 已交付；targeted tests 及跨模块测试的最终实测证据绑定在 handoff。完整 clean checkout 由 root 批次收口记录，不以本包定向测试冒充独立外部接受。

结束状态仅 `A04_R3_GO_FORWARD_FORMAL_AUTHORITY_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT`。历史 capability 继续 scoped BLOCKED，formal consumer / accepted owner registration / Production / Shadow / Focus / Global mandatory 全 false；Stage Head 与 Data Head 保持，V4-12 未执行。统一 commit/push 后 STOP。
