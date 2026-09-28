# V4-01 源级指纹阈值校准审计项 R1

- 审计项 ID：`AUDIT-V4-01-SOURCE-FINGERPRINT-CALIBRATION-20260929`
- 状态：`OPEN`
- 日期：2026-09-29
- 所属阶段：`V4-01-SOURCE-FINGERPRINT-CANDIDATE-STUDY`
- 独立于：`V4-01 Gate A / official code-change event index coverage`

## 范围

评估 `V4_01_SOURCE_FINGERPRINT_CANDIDATE_V1` 的研究阈值能否在跨板块、跨样本 source 行为上稳定地产生候选，不赋予该候选 SAME_ENTITY 权限。

当前 R1 仅有：

- 两个同实体代码更名正样本，均来自深圳市场；
- 两个吸收合并后继负样本；
- 只有一个正样本同时有本地旧/新 TDX `.day` 文件可作成对历史字段比较；
- 四案结果为 TP=2、FN=0、FP=0、TN=2。

## 已知限制

1. TDX volume exact ratio `0.95` 仅由一个直接成对 TDX 正样本覆盖，尚未校准。
2. BaoStock 活跃历史匹配率 `0.99` 只在当前四案小样本上观察；不代表市场总体误报/漏报率。
3. 全部样本都来自 SZ，尚未验证 SH_MAIN、STAR 的 source 行为差异。
4. current TDX 对 000022 不含旧代码文件；其检测路径依赖 new-code backfill、BaoStock overlap 和 lifecycle metadata，不能代替 TDX 成对验证。
5. 本轮标签与 detector 分离，但没有外部独立评审员的盲审。

## 关闭条件

- 收集更多正式文件/公告绑定的代码更名正样本与 merger-successor/distinct 反例；
- 至少再获得两个具备旧/新 TDX 文件成对 overlap 的正样本；
- 覆盖 SZ 与 SH/STAR 等可获得的 Required Scope 市场，报告缺失样本的原因；
- detector 推断过程不加载 expected labels，标签证据由独立评审复核；
- 对 amount precision、volume agreement、停牌空值/零值归一分别报告严格值与候选值，不把未经校准的容差写成 accepted fact；
- 冻结 FP/FN 结果与候选合同版本，所有生产 identity mutation 继续由现有官方/独立接受证据政策单独确认。

## 当前处置

候选合同保持研究专用。此次 `PASS_BOUNDED_BLIND_VALIDATION` 仅代表四案数据采集完整、标签 hash 验证通过、四个输出符合冻结标签，以及 TDX 输入不变；本审计项继续开放，不阻断本候选研究报告，但也不改变 V4-01 Gate A。

**验收结果：`OPEN_NEEDS_MORE_PAIRED_AND_CROSS_SCOPE_SAMPLES`**

**production identity mutation：`PROHIBITED`**
