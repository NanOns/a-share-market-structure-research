import pandas as pd
from shadow_v2.queue_ranking import rank_queues

def test_queue_ranks_are_independent_and_exact_ties_share_rank():
    board=pd.DataFrame({"security_id":["SZ.000002","SZ.000001","SZ.000003"],**{f"{k}_queue_tier":["CORE","CORE",None] for k in ("steady","pullback","breakout","leader","early")}})
    values={
      "steady":{"up_day_ratio20":.7,"trend_r2_20":.8,"trend_r2_60":.8,"mdd20":-.1,"rs20":.1},
      "pullback":{"v2_pullback_volume_confirmed":True,"pullback_amount_ratio":.5,"TREND_R2_60":.8,"RS60":.1,"MDD20":-.1},
      "breakout":{"range_contraction_ratio":.5,"realized_vol_contraction_ratio":.5,"DIST_HIGH20":-.02,"TREND_R2_20":.8,"RS20":.1},
      "leader":{"quality_dimension_strong_support_count":2,"member_rs20_pct":.8,"member_trend_r2_20_pct":.8,"member_mdd20_quality_pct":.8,"sector_rs20_pct":.8},
      "early":{"stock_rs5_pct":.8,"RET5":.05,"AMOUNT_RATIO_5_20":1.2,"TREND_R2_20":.8,"POS60":.6},
    }
    details={k:pd.DataFrame([{"security_id":sid,**v} for sid in board.security_id]) for k,v in values.items()}
    ranked=rank_queues(board,details).set_index("security_id")
    for key in values:
        assert ranked.loc["SZ.000001",f"{key}_queue_rank"]==ranked.loc["SZ.000002",f"{key}_queue_rank"]==1
        assert pd.isna(ranked.loc["SZ.000003",f"{key}_queue_rank"])
