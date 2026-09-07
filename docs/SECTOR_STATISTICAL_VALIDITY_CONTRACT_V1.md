# Sector Statistical Validity Contract V1

Version: `sector-statistical-validity-v1.1-branch-bound`

Membership coverage (`valid_member_count / total_member_count`) remains a separate identity/state gate: ratio at least 0.70 and count at least 5. It does not authorize a scanner by itself.

Every scanner requires each actually used aggregate to have at least five finite members and a factor-valid ratio of at least 0.70. Its non-optional inputs must also meet a true member-row joint gate with the same thresholds. `CURRENT_STRENGTH`, `STABILIZATION`, and `REACCELERATION` record their joint counts and ratios. For OR evidence, value and coverage are evaluated as one branch; at least one identical branch must satisfy its economic condition, finite-member minimum and coverage minimum. A value pass from one branch cannot be combined with coverage from another.

RET5/RET20 comparisons use `COMMON_VALID_MEMBER_SET`: members valid for the sector with both finite RET5 and RET20. Publications retain original horizon breadth and add `breadth_ret5_pos_common`, `breadth_ret20_pos_common`, `breadth_5_minus_20_common`, common count, and common ratio.

`scanner_quality_status` is one of `ELIGIBLE`, `DATA_INSUFFICIENT`, `MEMBERSHIP_INVALID`, or `EXCLUDED_ROLE`. Data-insufficient scanners emit no hit and are not described as weak or structurally absent. Fixed economic thresholds are unchanged. Current membership is not point-in-time historical membership; `historical_backtest_safe=false`.
