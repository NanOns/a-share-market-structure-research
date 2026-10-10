# 候选到准入事务

1. W1捕获原字节与真实观察收据，可无grant。
2. 原State全量计算产生prewatch全集，新Producer提取all scenarios、eligible+ineligible，freeze无覆盖；同publication/revision幂等，不同内容需新revision。
3. 独立审源检查完整证券身份、first available、所有模型窗口、成员有效性和Source原件；当前RECONSTRUCTED候选禁止送正式prepare_capture。
4. 当前cohort_first_capture_producer_r1的严格freeze_source_candidate/extract_candidate/独立writer.prepare_capture保留不放宽。只有独立获准的真实State source满足它们契约后才进入该流水线。
5. 独立grant与正式Owner/CAS另签。没有先正式Cohort Owner才能产隔离全集的依赖；但完整严格State源仍未实现，不能称C生产入组闭环。

不回填旧2290，forward仍按真实日历结算，样本未成熟unknown/null，不算胜率。
