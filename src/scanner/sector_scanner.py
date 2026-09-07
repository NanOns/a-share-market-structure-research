"""Formal current-snapshot sector scanner ruleset v1."""
from __future__ import annotations
import math
from decimal import Decimal
import numpy as np
import pandas as pd

RULE_VERSION = 'sector-scanner-ruleset-v1.2-evidence-binding'
STATISTICAL_VALIDITY_VERSION = 'sector-statistical-validity-v1.1-branch-bound'
MEMBERSHIP_BASIS = 'CURRENT_TDX_MEMBERSHIP'
PRECEDENCE = ('REACCELERATION', 'STABILIZATION', 'CURRENT_STRENGTH')

THRESHOLDS = {
    'coverage_min': .70, 'coverage_low_upper': .85,
    'breadth_expansion_delta': .10, 'breadth_expansion_floor': .55,
    'high_concentration': .60,
    'current_rs20_pct': .80, 'current_breadth20': .60,
    'current_pos60': .60, 'current_mdd20_strict': -.15,
    'stabilization_rs20_low': .35, 'stabilization_rs20_high_exclusive': .75,
    'stabilization_rs5': .60, 'stabilization_breadth5': .55,
    'stabilization_amount': .90, 'damaged_mdd20': -.08, 'damaged_pos60': .50,
    'reacceleration_rs60': .65, 'reacceleration_rs20': .70,
    'reacceleration_rs5': .75, 'reacceleration_breadth5': .60,
    'reacceleration_breadth_delta': .08, 'reacceleration_amount': 1.00,
    'pullback_mdd20': -.03, 'pullback_dist_high20': -.03,
}

EVIDENCE_FIELDS = (
    'sector_ret5_median','sector_ret20_median','sector_ret60_median',
    'sector_rs5_pct','sector_rs20_pct','sector_rs60_pct',
    'sector_breadth_ret5_pos','sector_breadth_ret20_pos','sector_breadth_ret60_pos',
    'sector_pos60_median','sector_dist_high20_median','sector_mdd20_median',
    'sector_amount_ratio_median','top3_concentration','coverage',
)
REQUIRED_FIELDS = {
 'CURRENT_STRENGTH': ('sector_ret20_median','sector_rs20','sector_breadth_ret20_pos','sector_pos60_median','sector_mdd20_median'),
 'STABILIZATION': ('sector_rs20','sector_ret5_median','sector_rs5','sector_amount_ratio_median'),
 'REACCELERATION': ('sector_rs60','sector_rs20','sector_ret20_median','sector_ret5_median','sector_rs5','sector_amount_ratio_median'),
}
MIN_VALID_RATIO=.70;MIN_VALID_COUNT=5

BRANCH_RULES = {
 'STABILIZATION': (
  ('RET20_NONPOSITIVE','sector_ret20_median','<=',0),
  ('MDD20_DAMAGED','sector_mdd20_median','<=',-.08),
  ('POS60_BELOW_50','sector_pos60_median','<',.50)),
 'REACCELERATION': (
  ('MDD20_PULLBACK','sector_mdd20_median','<=',-.03),
  ('DIST_HIGH20_PULLBACK','sector_dist_high20_median','<=',-.03)),
}

RULES = {
 'CURRENT_STRENGTH': [
  ('RET20_POSITIVE','sector_ret20_median','>',0,'PASS_RET20_POSITIVE'),
  ('RS20_TOP20PCT','sector_rs20_pct','>=',.80,'PASS_RS20_TOP20PCT'),
  ('BREADTH20_GE_60','sector_breadth_ret20_pos','>=',.60,'PASS_BREADTH20_GE_60'),
  ('POS60_GE_60','sector_pos60_median','>=',.60,'PASS_POS60_GE_60'),
  ('MDD20_CONTROLLED','sector_mdd20_median','>',-.15,'PASS_MDD20_CONTROLLED')],
 'STABILIZATION': [
  ('RS20_GE_35','sector_rs20_pct','>=',.35,'PASS_RS20_GE_35'),
  ('RS20_LT_75','sector_rs20_pct','<',.75,'PASS_RS20_LT_75'),
  ('SHORT_TERM_POSITIVE','sector_ret5_median','>',0,'PASS_SHORT_TERM_POSITIVE'),
  ('RS5_TOP40PCT','sector_rs5_pct','>=',.60,'PASS_RS5_TOP40PCT'),
  ('BREADTH5_GE_55','breadth_ret5_pos_common','>=',.55,'PASS_BREADTH5_GE_55'),
  ('BREADTH_EXPANSION','breadth_delta_5_20','>=',.10,'PASS_BREADTH_EXPANSION'),
  ('AMOUNT_STABLE','sector_amount_ratio_median','>=',.90,'PASS_AMOUNT_STABLE')],
 'REACCELERATION': [
  ('RS60_TOP35PCT','sector_rs60_pct','>=',.65,'PASS_RS60_TOP35PCT'),
  ('RS20_TOP30PCT','sector_rs20_pct','>=',.70,'PASS_RS20_TOP30PCT'),
  ('RET20_POSITIVE','sector_ret20_median','>',0,'PASS_RET20_POSITIVE'),
  ('SHORT_TERM_POSITIVE','sector_ret5_median','>',0,'PASS_SHORT_TERM_POSITIVE'),
  ('RS5_TOP25PCT','sector_rs5_pct','>=',.75,'PASS_RS5_TOP25PCT'),
  ('BREADTH5_GE_60','breadth_ret5_pos_common','>=',.60,'PASS_BREADTH5_GE_60'),
  ('BREADTH_REEXPANSION','breadth_delta_5_20','>=',.08,'PASS_BREADTH_REEXPANSION'),
  ('AMOUNT_EXPANSION','sector_amount_ratio_median','>=',1.00,'PASS_AMOUNT_EXPANSION')],
}


def finite(value):
    try: return math.isfinite(float(value))
    except (TypeError, ValueError): return False


def compare(value, op, threshold):
    if not finite(value): return False
    return {'>': value > threshold, '>=': value >= threshold,
            '<': value < threshold, '<=': value <= threshold}[op]


def add_percentiles(frame):
    """Strict same-type, sector-valid, finite average ranks; no cross-type pool."""
    frame = frame.copy()
    mapping = {'sector_rs5_pct':'sector_rs5', 'sector_rs20_pct_recomputed':'sector_rs20',
               'sector_rs60_pct':'sector_rs60'}
    for output, source in mapping.items():
        frame[output] = np.nan
        eligible = frame.sector_valid.eq(True) & frame[source].map(finite) & frame.sector_role.ne('EXCLUDE_FROM_THEME_RANK')
        frame.loc[eligible, output] = frame.loc[eligible].groupby('sector_type')[source].rank(
            pct=True, method='average', ascending=True)
    return frame


def hard_gate(row):
    conditions = {
        'SECTOR_VALID': row.get('sector_valid') is True or row.get('sector_valid') == True,
        'COVERAGE_GE_70': compare(row.get('coverage'), '>=', THRESHOLDS['coverage_min']),
        'VALID_MEMBERS_GE_5': compare(row.get('valid_member_count'), '>=', 5),
        'ROLE_ALLOWED': row.get('sector_role') != 'EXCLUDE_FROM_THEME_RANK',
    }
    return all(conditions.values()), conditions


def evaluate_conditions(row, scanner):
    passed, failed, details = [], [], []
    for code, field, op, threshold, reason in RULES[scanner]:
        ok = compare(row.get(field), op, threshold)
        details.append({'code':code,'field':field,'value':row.get(field),'operator':op,'threshold':threshold,'passed':ok})
        (passed if ok else failed).append(reason if ok else 'FAIL_'+code)
    if scanner == 'STABILIZATION':
        tests = BRANCH_RULES[scanner]
        outcomes = [compare(row.get(f),op,t) for _,f,op,t in tests]
        ok = any(outcomes)
        details.append({'code':'PRIOR_DAMAGE_ANY','alternatives':[
            {'code':c,'field':f,'value':row.get(f),'operator':op,'threshold':t,'passed':v}
            for (c,f,op,t),v in zip(tests,outcomes)],'passed':ok})
        (passed if ok else failed).append('PASS_PRIOR_DAMAGE_EVIDENCE' if ok else 'FAIL_PRIOR_DAMAGE_EVIDENCE')
    if scanner == 'REACCELERATION':
        tests = BRANCH_RULES[scanner]
        outcomes = [compare(row.get(f),op,t) for _,f,op,t in tests]
        ok = any(outcomes)
        details.append({'code':'PULLBACK_ANY','alternatives':[
            {'code':c,'field':f,'value':row.get(f),'operator':op,'threshold':t,'passed':v}
            for (c,f,op,t),v in zip(tests,outcomes)],'passed':ok})
        (passed if ok else failed).append('PASS_PULLBACK_EVIDENCE' if ok else 'FAIL_PULLBACK_EVIDENCE')
    return not failed, passed, failed, details

def factor_coverage(row,scanner):
    fields={}
    for field in REQUIRED_FIELDS[scanner]:
        count=row.get(field+'__valid_count',0);ratio=row.get(field+'__valid_ratio',0)
        fields[field]={'valid_count':count,'valid_ratio':ratio,'passed':compare(count,'>=',MIN_VALID_COUNT) and compare(ratio,'>=',MIN_VALID_RATIO)}
    if scanner in ('STABILIZATION','REACCELERATION'):
        count=row.get('breadth_5_20_common_valid_count',0);ratio=row.get('breadth_5_20_common_valid_ratio',0)
        fields['breadth_5_20_common']={'valid_count':count,'valid_ratio':ratio,'passed':compare(count,'>=',5) and compare(ratio,'>=',.70)}
    branch_rules=BRANCH_RULES.get(scanner,())
    branches={'not_applicable':not bool(branch_rules)}
    for code,field,op,threshold in branch_rules:
        coverage_ok=(compare(row.get(field+'__valid_count',0),'>=',MIN_VALID_COUNT)
                     and compare(row.get(field+'__valid_ratio',0),'>=',MIN_VALID_RATIO))
        condition_ok=compare(row.get(field),op,threshold)
        branches[code]={'field':field,'condition_passed':condition_ok,
                        'coverage_passed':coverage_ok,'passed':condition_ok and coverage_ok}
    key=scanner.lower();joint_count=row.get(key+'_joint_valid_count',0);joint_ratio=row.get(key+'_joint_valid_ratio',0)
    joint_ok=compare(joint_count,'>=',5) and compare(joint_ratio,'>=',.70)
    branch_ok=branches['not_applicable'] or any(v['passed'] for k,v in branches.items() if k!='not_applicable')
    return all(x['passed'] for x in fields.values()) and joint_ok and branch_ok, {'fields':fields,'branches':branches,'joint_valid_count':joint_count,'joint_valid_ratio':joint_ratio,'joint_passed':joint_ok}


def scan_row(row):
    values = row.to_dict() if hasattr(row,'to_dict') else dict(row)
    values['breadth_delta_5_20'] = values.get('breadth_5_minus_20_common',np.nan)
    gate, gate_conditions = hard_gate(values)
    low = gate and compare(values.get('coverage'), '<', .85)
    breadth = (gate and compare(values['breadth_delta_5_20'], '>=', .10)
               and compare(values.get('breadth_ret5_pos_common'), '>=', .55)
               and compare(values.get('breadth_5_20_common_valid_count'),'>=',5)
               and compare(values.get('breadth_5_20_common_valid_ratio'),'>=',.70))
    concentration_available = finite(values.get('top3_concentration'))
    concentrated = gate and concentration_available and compare(values['top3_concentration'], '>=', .60)
    hits=[]; reasons=[]; failed={}; detail={};coverage_results={}
    for scanner in ('CURRENT_STRENGTH','STABILIZATION','REACCELERATION'):
        ok, passed, misses, conditions = evaluate_conditions(values,scanner)
        coverage_ok,coverage_detail=factor_coverage(values,scanner);coverage_results[scanner]=coverage_detail
        hit = gate and coverage_ok and ok
        values[scanner.lower()] = hit
        if hit: hits.append(scanner); reasons.extend(passed)
        failed[scanner] = ([] if gate else ['FAIL_HARD_GATE']) + ([] if coverage_ok else ['FAIL_FACTOR_COVERAGE']) + misses
        detail[scanner] = conditions
    if breadth: reasons.append('BREADTH_EXPANSION')
    if concentrated: reasons.append('HIGH_CONCENTRATION_WARNING')
    if low: reasons.append('LOW_COVERAGE_WARNING')
    overlap=values['current_strength'] and values['stabilization']
    if overlap: reasons.append('RULE_OVERLAP_STABILIZATION_CURRENT_STRENGTH')
    primary=next((p for p in PRECEDENCE if p in hits),'NONE')
    if not gate: quality='EXCLUDED_ROLE' if values.get('sector_role')=='EXCLUDE_FROM_THEME_RANK' else 'MEMBERSHIP_INVALID'
    elif not all(factor_coverage(values,s)[0] for s in ('CURRENT_STRENGTH','STABILIZATION','REACCELERATION')):quality='DATA_INSUFFICIENT'
    else:quality='ELIGIBLE'
    values.update(scanner_hits='|'.join(hits),primary_pattern=primary,
        breadth_expansion=breadth,high_concentration=concentrated,low_coverage=low,
        concentration_tag_status='AVAILABLE' if concentration_available else 'UNAVAILABLE',
        rule_version=RULE_VERSION,reason_codes='|'.join(dict.fromkeys(reasons)),
        failed_conditions=';'.join(f'{k}:{",".join(v)}' for k,v in failed.items() if v),
        rule_overlap_stabilization_current_strength=overlap,
        scanner_quality_status=quality,statistical_validity_version=STATISTICAL_VALIDITY_VERSION,
        current_strength_factor_valid_min_ratio=min((x['valid_ratio'] for x in coverage_results['CURRENT_STRENGTH']['fields'].values()),default=0),
        rule_audit={'hard_gate':gate_conditions,'factor_coverage':coverage_results,'scanners':detail})
    return values


def scan(frame):
    ranked=add_percentiles(frame)
    existing=ranked.loc[ranked.sector_valid & ranked.sector_rs20.notna(),['sector_rs20_pct','sector_rs20_pct_recomputed']]
    if len(existing) and not np.allclose(existing.iloc[:,0],existing.iloc[:,1],atol=1e-12):
        raise ValueError('PHASE2_RS20_PERCENTILE_RECOMPUTE_MISMATCH')
    rows=pd.DataFrame([scan_row(row) for _,row in ranked.iterrows()])
    # Main publication contains all valid sectors and no invalid or excluded rows.
    rows=rows[rows.sector_valid & rows.sector_role.ne('EXCLUDE_FROM_THEME_RANK')].copy()
    rows['membership_basis']=MEMBERSHIP_BASIS; rows['pit_membership']=False
    rows['historical_backtest_safe']=False; rows['market_context_version']='market-regime-factor-v1.0'
    rows['quality_flag']=np.where(rows.scanner_quality_status.eq('DATA_INSUFFICIENT'),'DATA_INSUFFICIENT',np.where(rows.low_coverage,'LOW_COVERAGE_WARNING','OK'))
    rows.loc[rows.high_concentration,'quality_flag']=rows.loc[rows.high_concentration,'quality_flag'].map(
        lambda x: ('HIGH_CONCENTRATION_WARNING' if x=='OK' else x+'|HIGH_CONCENTRATION_WARNING'))
    add_display_ranks(rows)
    return rows


def add_display_ranks(rows):
    rows['display_rank']=pd.array([pd.NA]*len(rows),dtype='Int64')
    sorts={'CURRENT_STRENGTH':['sector_rs20_pct','sector_breadth_ret20_pos'],
           'STABILIZATION':['sector_rs5_pct','breadth_delta_5_20'],
           'REACCELERATION':['sector_rs5_pct','sector_rs20_pct']}
    for pattern,columns in sorts.items():
        mask=rows.primary_pattern.eq(pattern)
        order=rows.loc[mask].sort_values(columns+['sector_type','sector_id'],ascending=[False,False,True,True]).index
        rows.loc[order,'display_rank']=range(1,len(order)+1)


def snapshot_guard(input_dates, cutoff, membership_date):
    normalized=[int(pd.Timestamp(d).strftime('%Y%m%d')) for d in input_dates]
    if membership_date != cutoff or not normalized or any(d != cutoff for d in normalized):
        raise ValueError('CURRENT_SNAPSHOT_ONLY_NO_HISTORY_OR_FUTURE')


def phase3_gate(checks):
    return 'PASS' if all(checks.values()) else 'BLOCKED'
