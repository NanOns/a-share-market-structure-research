"""Formal, fixed-threshold stock scanner ruleset v1."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

RULE_VERSION='stock-scanner-ruleset-v1.0'
CONTRACT_VERSION='stock-scanner-contract-v1.0'
PRECEDENCE=('SECTOR_LEADER','BREAKOUT_PREP','STRONG_PULLBACK','STEADY_TREND')

RULES={
'STEADY_TREND':[('RET20','>',0),('RET60','>',0),('TREND_SLOPE_20','>',0),('TREND_SLOPE_60','>',0),('TREND_R2_20','>=',.55),('TREND_R2_60','>=',.45),('POS60','>=',.55),('MDD20','>',-.15),('MDD60','>',-.25),('DIST_HIGH20','>=',-.15),('RS20','>=',0),('VOLATILITY20','finite',None)],
'STRONG_PULLBACK':[('RET60','>',0),('TREND_SLOPE_60','>',0),('TREND_R2_60','>=',.40),('RS60','>=',0),('POS60','>=',.55),('MDD20','<=',-.03),('MDD20','>',-.18),('DIST_HIGH20','<=',-.03),('DIST_HIGH20','>=',-.18),('RET5','<=field','RET20'),('POS20','<',.85),('MA20','finite',None),('MA60','finite',None),('adj_close','>field','MA60')],
'BREAKOUT_PREP':[('DIST_HIGH20','>=',-.05),('DIST_HIGH60','>=',-.10),('POS20','>=',.75),('POS60','>=',.65),('TREND_SLOPE_20','>',0),('TREND_R2_20','>=',.40),('RS20','>=',0),('RET20','>',0),('AMOUNT_RATIO_5_20','>=',.90)],
'SECTOR_LEADER':[('RET20','>',0),('RS20','>',0),('TREND_SLOPE_20','>',0),('POS60','>=',.60),('MDD20','>',-.18)],
'EARLY_MOVER':[('RET5','>',0),('RS5','>',0),('RET5','>=field','RET20'),('TREND_SLOPE_20','>',0),('AMOUNT_RATIO_5_20','>=',1.0),('stock_rs5_pct','>=',.80)],
}

def finite(v):
    try:return math.isfinite(float(v))
    except (TypeError,ValueError):return False

def condition(row, field, op, target):
    value=row.get(field)
    if op=='finite': return finite(value)
    other=row.get(target) if op.endswith('field') else target
    if not finite(value) or not finite(other): return False
    op=op.replace('field','')
    return {'>':value>other,'>=':value>=other,'<':value<other,'<=':value<=other}[op]

def hard_gate(row):
    sid=str(row.get('security_id',''))
    return (sid.startswith(('SH.','SZ.','BJ.')) and len(sid)==9 and sid[3:].isdigit()
            and row.get('universe_status')=='IN_NORMAL_UNIVERSE'
            and bool(row.get('tradable')) and bool(row.get('latest_factor_row'))
            and not bool(row.get('fatal_quality_error')))

def market_percentiles(frame):
    out=frame.copy()
    mapping={'stock_rs5_pct':'RS5','stock_rs20_pct':'RS20','stock_rs60_pct':'RS60',
             'volatility20_pct':'VOLATILITY20','amount_ratio_pct':'AMOUNT_RATIO_5_20'}
    normal=out.universe_status.eq('IN_NORMAL_UNIVERSE')
    for dst,src in mapping.items():
        out[dst]=np.nan; eligible=normal & out[src].map(finite)
        out.loc[eligible,dst]=out.loc[eligible,src].rank(pct=True,method='average')
    return out

def evaluate(row, name): return all(condition(row,*x) for x in RULES[name])

def scan_row(row):
    r=row.to_dict() if hasattr(row,'to_dict') else dict(row); gate=hard_gate(r)
    hits=[]; reasons=[]; warnings=[]
    for name in ('STEADY_TREND','STRONG_PULLBACK','BREAKOUT_PREP'):
        hit=gate and evaluate(r,name); r[name.lower()]=hit
        if hit: hits.append(name)
    leader=gate and evaluate(r,'SECTOR_LEADER') and bool(r.get('leader_eligible'))
    r['sector_leader']=leader
    if leader:hits.append('SECTOR_LEADER')
    early=(gate and evaluate(r,'EARLY_MOVER') and not bool(r.get('has_current_strength_sector'))
           and not bool(r.get('has_reacceleration_sector')))
    r['early_mover']=early
    if early: reasons.append('EARLY_MOVER_TAG')
    if r['breakout_prep'] and condition(r,'POS20','>=',.95) and condition(r,'RET5','>',.10): warnings.append('LATE_EXTENSION_WARNING')
    if leader:
        reasons += ['PASS_STRONG_SECTOR_CONTEXT','PASS_MEMBER_RS20_TOP20PCT']
        if int(r.get('leader_sector_count',0))>1:warnings.append('MULTIPLE_LEADER_SECTORS')
        if bool(r.get('primary_leader_high_concentration')):warnings.append('HIGH_CONCENTRATION_SECTOR_CONTEXT')
        if bool(r.get('primary_leader_low_coverage')):warnings.append('LOW_SECTOR_COVERAGE_CONTEXT')
    if r['steady_trend']: reasons += ['PASS_RET20_POSITIVE','PASS_RET60_POSITIVE','PASS_TREND20_POSITIVE','PASS_TREND60_POSITIVE','PASS_TREND_R2_20','PASS_TREND_R2_60','PASS_RS20_POSITIVE','PASS_POS60_HEALTHY','PASS_DRAWDOWN_CONTROLLED']
    if r['strong_pullback']: reasons += ['PASS_RET60_POSITIVE','PASS_TREND60_POSITIVE','PASS_TREND_R2_60','PASS_RS60_POSITIVE','PASS_PULLBACK_DEPTH']
    if r['breakout_prep']: reasons += ['PASS_RET20_POSITIVE','PASS_TREND20_POSITIVE','PASS_TREND_R2_20','PASS_RS20_POSITIVE','PASS_NEAR_HIGH20','PASS_NEAR_HIGH60','PASS_AMOUNT_STABLE']
    r['scanner_hits']='|'.join(hits); r['primary_pattern']=next((x for x in PRECEDENCE if x in hits),'NONE')
    r['reason_codes']='|'.join(dict.fromkeys(reasons));r['warning_codes']='|'.join(dict.fromkeys(warnings))
    r['quality_flag']='OK' if gate else 'HARD_GATE_FAILED';r['rule_version']=RULE_VERSION
    return r

def phase4_gate(checks): return 'PASS' if all(checks.values()) else 'BLOCKED'
