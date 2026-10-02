"""Independent paper/Decimal oracle for DESIGN VECTORS, never a market detector.

State expectations are authored from numbered REV4 rules here, before the
serialized AST is evaluated. This module imports no AST/interpreter/helper.
"""
from decimal import Decimal
from scripts.record_r7_stage_contract import put
from scripts.v4_11_promotion_contract_r1 import bind

def vectors():
    rows=[]
    def case(identifier,target,inputs,expected,proof,kind='AST'):
        rows.append(dict(vector_id=identifier,target=target,inputs=inputs,expected=expected,
                         independent_oracle_proof=proof,kind=kind,scope='SYNTHETIC_CONTRACT_VECTOR_NOT_ACCEPTED_PUBLICATION'))
    # Explicit boundary book: threshold 10 + .1*2 = 10.2; strict >.
    for suffix,close,expected in [('minus','10.199999','NO_BREAKOUT'),('exact','10.2','NO_BREAKOUT'),('plus','10.200001','BREAKOUT_TENTATIVE')]:
        case('B01_'+suffix,'breakout',dict(C=close,prior_high20=10,ATR20=2,CLV=.7),expected,
             '10J: strict C>10.2, CLV>=.7; independently calculated Decimal threshold=10.2')
    case('B01_clv_below','breakout',dict(C=11,CLV='.699999'),'NO_BREAKOUT','10J: CLV below .7 defeats conjunction')
    case('B02','breakout',dict(prior_breakout_exists=True,post_creation_sessions=0,prior_held_count=8,prior_adjacent_evaluable=True),'BREAKOUT_TENTATIVE','13A/10J: creation day age=0; acceptance forbidden even bogus held count')
    case('B03_t1','acceptance',dict(post_creation_sessions=1,prior_held_count=0,C=10,hi=10),'PENDING','41D: only one post-event evaluable close at upper')
    case('B03_t2','acceptance',dict(post_creation_sessions=2,prior_held_count=1,prior_adjacent_evaluable=True,C=10,hi=10),'ACCEPTED','41D: two adjacent post-event evaluable closes >= upper; equality qualifies')
    case('B03_missing','acceptance',dict(post_creation_sessions=3,prior_held_count=1,prior_adjacent_evaluable=False,C=10,hi=10),'NOT_ACCEPTED','41D: missing intervening session resets count; calendar age alone insufficient')
    case('P01','pullback',dict(prior_valid_event=False),'NOT_PULLBACK','10K: known no prior valid event')
    case('P02','pullback',dict(prior_valid_event=True,prior_support_state='BROKEN'),'PULLBACK_FAILED','10K: broken prior Anchor')
    case('P03','pullback',dict(prior_valid_event=True,support_today='HELD_CONFIRMED'),'PULLBACK_HELD','10K: held confirmed prior path evidence')
    case('P04','pullback',dict(prior_valid_event=None),'UNKNOWN','10K: absent prior publication is UNKNOWN; not known absence')
    for suffix,atype,expected in [('ma','MA20_DYNAMIC','PULLBACK_TO_MA'),('impulse','BULLISH_IMPULSE_LOW','PULLBACK_TO_IMPULSE'),('breakout','PRIOR_HIGH','PULLBACK_TO_BREAKOUT')]:
        case('P_touch_'+suffix,'pullback',dict(prior_valid_event=True,anchor_type=atype,L=10,H=11),'%s'%expected,'10K: touched anchor type routing after higher states false')
    case('R01','recovery',dict(close_t_minus_1=None,ma20_t_minus_1=None,C=11,MA20=10),'UNKNOWN','10L/R7 owner authority: unresolved MA20 reclaim preempts lower branch; UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE')
    case('R01_current_false','recovery',dict(close_t_minus_1=None,ma20_t_minus_1=None,C=9,MA20=10,ret1=0),'UNKNOWN','R7: MA20_RECLAIM capability guard precedes predicate; absent owner fields remain UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE even when current C<=MA20')
    for suffix,current,expected in [('minus','2.999999',False),('exact','3',False),('plus','3.000001',True)]:
        case('R02_'+suffix,'relative_recovery',dict(prior_delta3=0,delta3=current,rel_market_1=.01),expected,'10L: branch-only mathematical oracle; current strictly >3, previous <=0; not a grant of overall Recovery capability')
    case('R03','recovery',dict(prior_recovery_exists=True,post_creation_sessions=0,prior_recovery_held_count=9,close_t_minus_1=None,ma20_t_minus_1=None,C=11,MA20=10),'UNKNOWN','10L: new recovery line cannot self-confirm; missing higher-priority MA owner prevents lower claim')
    case('R_confirmed','recovery',dict(prior_recovery_exists=True,post_creation_sessions=2,prior_recovery_held_count=1,prior_adjacent_evaluable=True,recovery_line_view=10,C=11),'RECOVERY_CONFIRMED','10L: frozen prior recovery line, two held post-event sessions')
    case('R_failed','recovery',dict(prior_recovery_failed=True),'RECOVERY_FAILED','10L: failure precedes all confirmation predicates')
    case('S01','support',dict(L=10,H=11,C=10,CLV=.5),'RECLAIMED','41C rule5: first touch with C>=hi and CLV>=.5; test_count first=1')
    case('S02','support',dict(L=8,H=10,C=9.49),'BREACHED_SHALLOW','41C rule3: C<9.5, C>=8.5, first close breach')
    case('S03','support',dict(L=8,H=10,C=9.4,prior_breach_count=1,prior_adjacent_evaluable=True),'BROKEN','41C rule2: two adjacent evaluable close breaches')
    case('S04_missing','support',dict(evaluable=False,prior_support_state='BREACHED_SHALLOW',prior_breach_count=1),'UNKNOWN','41C: missing session observation unknown, preserved prior state; stale true; counts reset')
    case('S04_count','breach_count',dict(evaluable=False,prior_breach_count=1),0,'41C: missing session breaks breach counter')
    case('S04_resume','support',dict(L=8,H=10,C=9.4,prior_breach_count=1,prior_adjacent_evaluable=False),'BREACHED_SHALLOW','41C: first breach after missing day; no unknown counted as recovery or breach')
    case('S05_reclaim','support',dict(L=10,H=11,C=10.2,CLV=.7),'RECLAIMED','41C: first reclaim only')
    case('S05_hold','support',dict(L=11,H=12,C=11.5,prior_support_state='RECLAIMED',prior_test_count=1),'HELD_TENTATIVE','41C rule6: actual post-reclaim held session wholly away from test band')
    case('S05_retest','support',dict(L=10,H=11,C=10.1,CLV=.4,prior_support_state='HELD_TENTATIVE',prior_test_count=1,prior_separated_sessions=1),'RETESTING','41C rule7: prior held re-touch, no reclaim')
    case('S05_confirm','support',dict(L=10,H=11,C=10.2,CLV=.7,prior_support_state='HELD_TENTATIVE',prior_test_count=1,prior_separated_sessions=1),'HELD_CONFIRMED','41C rule4: prior test + at least one fully separated actual session + second touch/reclaim')
    case('S05_after_retesting','support',dict(L=10,H=11,C=10.2,CLV=.7,prior_support_state='RETESTING',prior_test_count=1,prior_retest_qualified=True,prior_adjacent_evaluable=True),'HELD_CONFIRMED','41C: qualified retest episode retains separation evidence through adjacent touch session until reclaim')
    case('S05_no_separation','support',dict(L=10,H=11,C=10.2,CLV=.7,prior_support_state='HELD_TENTATIVE',prior_test_count=1,prior_separated_sessions=0),'TESTING','41C: repeated adjacent touch cannot count as confirmed retest')
    case('S05_test_count','next_test_count',dict(L=10,H=11,C=10.2,CLV=.7,prior_test_count=1,prior_separated_sessions=1),2,'41C: independently qualified second test increments once')
    case('S06','support',dict(prior_support_state='BROKEN',C=100,L=99,H=101),'BROKEN','41C rule1: terminal price-path state cannot revive')
    case('S06_admin','support',dict(prior_support_state='INVALIDATED',evaluable=False),'INVALIDATED','41C rule1: terminal administrative state preserved; independent unknown observation metadata still stale')
    case('S_deep','support',dict(L=7,H=9,C=8.49),'BROKEN','41C rule2: deep strict C<8.5')
    case('S_breach_exact','close_breach',dict(C=9.5),False,'41C strict <; exact .5ATR lower boundary not breached')
    case('S_touch_exact','touch',dict(L=10.25,H=11),True,'41C touch L<=10.25 inclusive boundary')
    # Corporate action outputs are independent affine arithmetic, never a basis identity inferred from coefficients.
    for identifier,alpha,beta,expected,proof in [
        ('A01',1,-1,9,'cash dividend: 1*10-1=9'),('A02',.5,0,5,'bonus shares: .5*10=5'),
        ('A03',.8,.4,8.4,'rights issue source-bound affine example: .8*10+.4=8.4'),
        ('A06',1,-2,8,'same-day new accepted source revision: 1*10-2=8; original remains 10')]:
        case(identifier,'anchor_price_view',dict(anchor_original_price=10,alpha=alpha,beta=beta),expected,
             '41A0 '+proof+'; hypothetical authenticated transform, not corporate action rate inference')
    case('A01_ATR','anchor_atr_view',dict(anchor_original_atr=2,alpha=1,beta=-1),2,'ATR is difference; dividend beta excluded')
    case('A02_ATR','anchor_atr_view',dict(anchor_original_atr=2,alpha=.5),1,'ATR .5*2=1; no additive shift')
    case('A04','coordinate_gate',dict(convertible=False),'UNKNOWN:PRICE_BASIS_MISMATCH','41A0 no deterministic source-bound conversion',kind='GATE')
    case('A05','immutable_anchor',dict(original=dict(price=10,revision='r1'),alpha=.5,beta=0),True,'41A0 original bytes immutable under observation rebase',kind='GATE')
    case('A06_identity','basis_identity',dict(left=['QFQ','r1'],right=['QFQ','r2'],same_coefficients=True),False,'41A0 coefficient equality never proves revision identity',kind='GATE')
    case('A_cross_support','support',dict(lo=9,hi=9,atr_prior_view=1,L=9,H=10,C=9.5,CLV=.7),'RECLAIMED','Cross corporate action: original 10 -> observation9, all price/ATR in same view; first reclaim')
    case('A_return','common_coordinate_return',dict(endpoint_price_view=10,start_price_view=9),str(Decimal(10)/Decimal(9)-1),'Independent Decimal: common-coordinate endpoint/base minus unit; no raw old-basis return')
    for suffix,right,expected in [('t0',0,False),('t1',1,False),('t2',2,True)]:
        case('T01_'+suffix,'pivot_available',dict(pivot_left_count=2,pivot_right_count=right,pivot_low_strict=True),expected,'41A: two actual right sessions; available date is t2 confirmation, no backfill')
    case('T02','support',dict(anchor_type='GAP_ZONE',post_creation_sessions=0),'IDLE','41A: gap registration day cannot test itself')
    case('T02_gap','gap_qualified',dict(L=11,prior_high_view=10),True,'41A gap L>previous high')
    case('T03_today','support',dict(anchor_type='BULLISH_IMPULSE_BODY',post_creation_sessions=0),'IDLE','41B impulse same-day no test')
    case('T03_next','support',dict(anchor_type='BULLISH_IMPULSE_BODY',post_creation_sessions=1,L=10,H=11,C=10.5),'RECLAIMED','41B next market session earliest test')
    case('I_exact','impulse',dict(O=10,C=11,L=10,H=11,atr_prior_view=1,CLV=.7,amount_ratio20=1.2,rel_market_1=.01),True,'41B exact inclusive body/range/CLV/amount; relative strict positive')
    case('I_flat','impulse',dict(O=10,C=11,L=10,H=11,atr_prior_view=1,CLV=None,amount_ratio20=1.2,rel_market_1=.01),'UNKNOWN','41B missing/flat-limit CLV cannot make impulse TRUE')
    case('D01','breakout',dict(C=11,D2={'eligibility':'TRUE'},prior_high20=10,ATR20=2,CLV=.7),'BREAKOUT_TENTATIVE','13A: D2 is not an AST input; perturbation discarded by dependency projection')
    case('D02','breakout',dict(C=11,Focus={'active':True},UI={'state':'CONFIRMED'},prior_high20=10,ATR20=2,CLV=.7),'BREAKOUT_TENTATIVE','13A: Focus/UI not an AST dependency')
    case('D03','future_source',dict(source_available='2026-10-03T00:00:00Z',cutoff='2026-10-02T15:00:00Z'),'REJECT:FUTURE_SOURCE','13A source available after cutoff rejected, not treated as valid today',kind='GATE')
    case('D04','support',dict(post_creation_sessions=0,prior_test_count=10,prior_separated_sessions=10),'IDLE','13A new Anchor cannot self-support regardless historical-looking supplied counts')
    for suffix,values,expected,proof in [
        ('positive',dict(event_close_view=12,base_view=10,observation_close_view=13),1.5,'(13-10)/(12-10)=1.5; not probability'),
        ('zero',dict(event_close_view=10,base_view=10,observation_close_view=13),'NOT_APPLICABLE','zero denominator; no epsilon'),
        ('negative',dict(event_close_view=9,base_view=10,observation_close_view=13),'NOT_APPLICABLE','negative denominator'),
        ('missing',dict(event_close_view=None,base_view=10,observation_close_view=13),'UNKNOWN','missing event price')]:
        case('RET_'+suffix,'retention_value',values,expected,'41D '+proof)
    return rows

def freeze_vectors():
    rows=vectors()
    put('config/v4_12_machine_vectors_v1.json',dict(contract_id='V4_12_MACHINE_VECTORS_V1',version='1.0.0',
        scope='CONTRACT_ONLY_INDEPENDENT_ORACLE',expected_generation='HAND_AUTHORED_REV4_RULE_BOOK_AND_INDEPENDENT_DECIMAL_ARITHMETIC; no AST helper imports',
        independent_oracle_source=bind('scripts/v4_12_independent_vector_oracle_r1.py'),vectors=rows,
        defaults=dict(O=10,H=12,L=11,C=11,CLV=.7,ATR20=1,atr_prior_view=1,lo=10,hi=10,
            prior_high20=100,near_high20_state='OTHER',evaluable=True,post_creation_sessions=1,
            prior_support_state='IDLE',prior_test_count=0,prior_separated_sessions=0,prior_breach_count=0,
            prior_held_count=0,prior_adjacent_evaluable=False,distance_zone=1,
            prior_breakout_exists=False,prior_valid_event=False,prior_event_peak_view=10,
            prior_recovery_failed=False,prior_recovery_exists=False,prior_recovery_held_count=0,recovery_line_view=10,prior_retest_qualified=False,
            close_t_minus_1=None,ma20_t_minus_1=None,MA20=12,prior_delta3=1,delta3=0,rel_market_1=0,ret1=0,
            support_today='IDLE',anchor_type='PRIOR_HIGH',prior_hard_invalidated=False,episode_owns_anchor=True)))
    print('INDEPENDENT_VECTOR_ORACLE_EXPECTATIONS_FROZEN:'+str(len(rows)))

if __name__=='__main__':freeze_vectors()
