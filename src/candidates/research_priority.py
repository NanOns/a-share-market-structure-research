"""Daily cross-sectional research priority ruleset v1."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

RULE_VERSION='research-priority-ruleset-v1.1-correctness'
CANDIDATE_CONTRACT_VERSION='candidate-pool-contract-v1.0'
PRIORITY_CONTRACT_VERSION='research-priority-contract-v1.1-correctness'
BASES={'SECTOR_LEADER':40,'BREAKOUT_PREP':34,'STRONG_PULLBACK':32,'STEADY_TREND':28,'EARLY_MOVER_ONLY':22}
PATTERN_SORTS={
 'SECTOR_LEADER':[('best_sector_rs20_pct',False),('primary_member_rs20_pct',False),('stock_rs20_pct',False)],
 'BREAKOUT_PREP':[('stock_rs20_pct',False),('DIST_HIGH20',False),('TREND_R2_20',False)],
 'STRONG_PULLBACK':[('stock_rs60_pct',False),('MDD20',False),('RS20',False)],
 'STEADY_TREND':[('stock_rs20_pct',False),('TREND_R2_20',False),('MDD20',False)],
 'EARLY_MOVER_ONLY':[('stock_rs5_pct',False),('AMOUNT_RATIO_5_20',False),('RET5',False)],
}

def valid_id(v): return isinstance(v,str) and len(v)==9 and v[:3] in ('SH.','SZ.','BJ.') and v[3:].isdigit()
def pool_gate(r):
    structure=bool(r.get('steady_trend') or r.get('strong_pullback') or r.get('breakout_prep') or r.get('sector_leader') or r.get('early_mover'))
    return valid_id(r.get('security_id')) and bool(r.get('in_normal_universe')) and bool(r.get('tradable')) and r.get('quality_flag')!='HARD_GATE_FAILED' and structure
def effective_pattern(r): return 'EARLY_MOVER_ONLY' if r.get('primary_pattern')=='NONE' and bool(r.get('early_mover')) else r.get('primary_pattern')

def assign_pattern_ranks(frame):
    out=frame.copy();out['effective_pattern']=out.apply(effective_pattern,axis=1);out['within_pattern_rank_pct']=np.nan
    for pattern,keys in PATTERN_SORTS.items():
        idx=out.index[out.effective_pattern.eq(pattern)];n=len(idx)
        if not n:continue
        cols=[x[0] for x in keys]
        tuples=out.loc[idx,cols].apply(lambda r:tuple((-float(v) if pd.notna(v) else float('inf')) for v in r),axis=1)
        ordered=sorted(tuples.items(),key=lambda x:x[1]);position=1;i=0
        while i<n:
            j=i+1
            while j<n and ordered[j][1]==ordered[i][1]:j+=1
            average_rank=(position+(position+j-i-1))/2
            out.loc[[ordered[k][0] for k in range(i,j)],'within_pattern_rank_pct']=(n-average_rank+1)/n
            position+=j-i;i=j
    return out

def sector_points(r):
    if r.get('effective_pattern')=='SECTOR_LEADER':
        if r.get('primary_leader_pattern')=='REACCELERATION':return 20,'SECTOR_REACCELERATION_CONTEXT'
        if r.get('primary_leader_pattern')=='CURRENT_STRENGTH':return 18,'SECTOR_CURRENT_STRENGTH_CONTEXT'
    if bool(r.get('has_reacceleration_sector')):return 14,'SECTOR_REACCELERATION_CONTEXT'
    if bool(r.get('has_current_strength_sector')):return 12,'SECTOR_CURRENT_STRENGTH_CONTEXT'
    if bool(r.get('has_stabilization_sector')):return 6,'SECTOR_STABILIZATION_CONTEXT'
    return 0,'NO_STRONG_SECTOR_CONTEXT'

def quality_points(warnings):
    tokens=set(str(warnings or '').split('|'))
    deductions={'LATE_EXTENSION_WARNING':3,'HIGH_CONCENTRATION_SECTOR_CONTEXT':2,'LOW_SECTOR_COVERAGE_CONTEXT':3}
    return max(0,10-sum(v for k,v in deductions.items() if k in tokens))

def rating(pct):
    if pct>=.95:return 'A+'
    if pct>=.85:return 'A'
    if pct>=.65:return 'B'
    return 'C'

def score(frame):
    out=assign_pattern_ranks(frame)
    if out.empty:
        # A valid empty candidate pool still has a stable, explainable schema.
        for name,default in {
            'primary_pattern_base':pd.Series(dtype='float64'),'pattern_rank_points':pd.Series(dtype='float64'),
            'sector_context_points':pd.Series(dtype='float64'),'quality_context_points':pd.Series(dtype='float64'),
            'priority_score':pd.Series(dtype='float64'),'research_priority_pct':pd.Series(dtype='float64'),
            'research_priority':pd.Series(dtype='object'),'candidate_status':pd.Series(dtype='object'),
            'priority_score_semantics':pd.Series(dtype='object'),'research_priority_semantics':pd.Series(dtype='object'),
            'priority_reason_codes':pd.Series(dtype='object'),'scanner_hit_count':pd.Series(dtype='int64'),
            'supporting_patterns':pd.Series(dtype='object'),'rule_version':pd.Series(dtype='object')}.items():
            out[name]=default
        return out
    out['primary_pattern_base']=out.effective_pattern.map(BASES)
    out['pattern_rank_points']=30*out.within_pattern_rank_pct
    sp=out.apply(sector_points,axis=1);out['sector_context_points']=[x[0] for x in sp];sector_reasons=[x[1] for x in sp]
    out['quality_context_points']=out.warning_codes.map(quality_points)
    out['priority_score']=(out.primary_pattern_base+out.pattern_rank_points+out.sector_context_points+out.quality_context_points).round(4)
    out['research_priority_pct']=out.priority_score.rank(pct=True,method='average',ascending=True)
    out['research_priority']=out.research_priority_pct.map(rating);out['candidate_status']='IN_CANDIDATE_POOL'
    out['priority_score_semantics']='RESEARCH_ORDERING_SCORE'
    out['research_priority_semantics']='DAILY_CROSS_SECTIONAL_CANDIDATE_POOL_RELATIVE'
    def reasons(r,sr):
        z=['BASE_'+r.effective_pattern]
        if r.within_pattern_rank_pct>=.90:z.append('PATTERN_RANK_TOP_DECILE')
        elif r.within_pattern_rank_pct>=.75:z.append('PATTERN_RANK_TOP_QUARTILE')
        z.append(sr);w=set(str(r.warning_codes or '').split('|'))
        if 'LATE_EXTENSION_WARNING' in w:z.append('DEDUCT_LATE_EXTENSION')
        if 'HIGH_CONCENTRATION_SECTOR_CONTEXT' in w:z.append('DEDUCT_HIGH_CONCENTRATION')
        if 'LOW_SECTOR_COVERAGE_CONTEXT' in w:z.append('DEDUCT_LOW_COVERAGE')
        return '|'.join(z)
    out['priority_reason_codes']=[reasons(r,sr) for (_,r),sr in zip(out.iterrows(),sector_reasons)]
    out['scanner_hit_count']=out.scanner_hits.fillna('').map(lambda x:0 if not x else len(set(x.split('|'))))
    out['supporting_patterns']=out.apply(lambda r:'|'.join([x for x in str(r.scanner_hits or '').split('|') if x and x!=r.primary_pattern]+(['EARLY_MOVER'] if r.early_mover else [])),axis=1)
    out['rule_version']=RULE_VERSION
    return out

def phase5_gate(checks):return 'PASS' if all(checks.values()) else 'BLOCKED'
