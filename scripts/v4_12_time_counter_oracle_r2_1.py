"""Independent R9 handwritten expectations. Imports no detector/AST helper.

Historical 69-row expected book is read from the exact accepted Git baseline.
Only B03_missing's expectation is normatively corrected under section 41D.
"""
import json
import subprocess
from pathlib import Path

def amended_vectors():
    root=Path(__file__).resolve().parents[1]
    pack=json.loads(subprocess.check_output(['git','show','5267c9e482268dfaaf06d1c752e1bb3d09e33b6f:config/v4_12_machine_vectors_v1.json'],cwd=root))
    rows=pack['vectors']
    for row in rows:
        inputs=row['inputs']
        if 'post_creation_sessions' in inputs:
            n=inputs.pop('post_creation_sessions');inputs['post_creation_market_sessions']=n;inputs['post_creation_evaluable_sessions']=n
        if row['vector_id']=='B03_missing':
            inputs.update(post_creation_market_sessions=2,post_creation_evaluable_sessions=1,prior_held_count=0,prior_adjacent_evaluable=False)
            row['expected']='PENDING'
            row['independent_oracle_proof']='41D/R9: T0 created, T+1 missing, T+2 first evaluable hold; market age 2, evaluable count 1, held count 1 -> PENDING. Full independent sequence C01-C04.'
            row['sequence_ref']='config/v4_12_time_counter_vectors_r2_1.json#/sequences/1'
    return rows

def sequence_book():
    # Dates and all expected outputs are literal paper-oracle values.
    # Each sequence runner must derive counts from history rather than supplied ages.
    steps=[
        dict(id='C01',date='2026-09-24',revision='r1',evaluable=True,C=10,expected=dict(market_age=0,evaluable_count=0,held_count=0,breach_count=0,support='IDLE',acceptance='PENDING',stale=False)),
        dict(id='C02',date='2026-09-25',revision='r1',evaluable=False,reason='SUSPENDED',C=None,expected=dict(market_age=1,evaluable_count=0,held_count=0,breach_count=0,support='UNKNOWN',acceptance='UNKNOWN',stale=True)),
        dict(id='C03',date='2026-09-28',revision='r1',evaluable=True,C=10,CLV=.7,expected=dict(market_age=2,evaluable_count=1,held_count=1,breach_count=0,support='RECLAIMED',acceptance='PENDING',stale=False)),
        # 41C rule6: prior RECLAIMED plus next held close -> HELD_TENTATIVE.
        dict(id='C04',date='2026-09-29',revision='r1',evaluable=True,C=10,expected=dict(market_age=3,evaluable_count=2,held_count=2,breach_count=0,support='HELD_TENTATIVE',acceptance='ACCEPTED',stale=False)),
        dict(id='C06_hold_revision',date='2026-09-29',revision='r2',evaluable=True,C=10,expected=dict(market_age=3,evaluable_count=2,held_count=2,breach_count=0,support='HELD_TENTATIVE',acceptance='ACCEPTED',stale=False)),
        dict(id='C06_hold_revision_r3',date='2026-09-29',revision='r3',evaluable=True,C=10,expected=dict(market_age=3,evaluable_count=2,held_count=2,breach_count=0,support='HELD_TENTATIVE',acceptance='ACCEPTED',stale=False)),
        dict(id='C05',date='2026-09-30',revision='r1',evaluable=True,C=9.4,expected=dict(market_age=4,evaluable_count=3,held_count=0,breach_count=1,support='BREACHED_SHALLOW',acceptance='NOT_ACCEPTED',stale=False)),
        dict(id='C06_breach_revision',date='2026-09-30',revision='r2',evaluable=True,C=9.4,expected=dict(market_age=4,evaluable_count=3,held_count=0,breach_count=1,support='BREACHED_SHALLOW',acceptance='NOT_ACCEPTED',stale=False))]
    steps.append(dict(id='C06_breach_revision_r3',date='2026-09-30',revision='r3',evaluable=True,C=9.4,expected=dict(market_age=4,evaluable_count=3,held_count=0,breach_count=1,support='BREACHED_SHALLOW',acceptance='NOT_ACCEPTED',stale=False)))
    sequences=[]
    for reason in ['SUSPENDED','MISSING_BAR','REQUIRED_COORDINATE_UNAVAILABLE']:
        variant=json.loads(json.dumps(steps));variant[1]['reason']=reason
        sequences.append(dict(id='creation_missing_resume_'+reason,available_date='2026-09-24',calendar=['2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-09-30'],steps=variant))
    sequences.append(dict(id='C08_hold_missing_resume_chain_reset',available_date='2026-09-24',calendar=['2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-09-30'],steps=[
        json.loads(json.dumps(steps[0])),
        dict(id='C08_first_hold',date='2026-09-25',revision='r1',evaluable=True,C=10,CLV=.7,expected=dict(market_age=1,evaluable_count=1,held_count=1,breach_count=0,support='RECLAIMED',acceptance='PENDING',stale=False)),
        dict(id='C08_missing',date='2026-09-28',revision='r1',evaluable=False,C=None,reason='MISSING_BAR',expected=dict(market_age=2,evaluable_count=1,held_count=0,breach_count=0,support='UNKNOWN',acceptance='UNKNOWN',stale=True)),
        dict(id='C08_resume',date='2026-09-29',revision='r1',evaluable=True,C=10,expected=dict(market_age=3,evaluable_count=2,held_count=1,breach_count=0,support='HELD_TENTATIVE',acceptance='NOT_ACCEPTED',stale=False)),
        dict(id='C08_second_hold',date='2026-09-30',revision='r1',evaluable=True,C=10,expected=dict(market_age=4,evaluable_count=3,held_count=2,breach_count=0,support='RETESTING',acceptance='ACCEPTED',stale=False))]))
    sequences.append(dict(id='C07_missing_calendar',available_date='2026-09-24',calendar=None,steps=[dict(id='C07',date='2026-09-25',revision='r1',evaluable=True,C=10,
        expected=dict(market_age='UNKNOWN',evaluable_count=1,held_count='UNKNOWN',breach_count=0,support='UNKNOWN',acceptance='UNKNOWN',stale=True))]))
    return sequences

def compatibility_vectors():
    return [
        dict(id='TD01',field='post_creation_market_sessions',parameter='earliest_anchor_test_sessions',expected=True),
        dict(id='TD02',field='post_creation_evaluable_sessions',parameter='acceptance_consecutive_sessions',expected=True),
        dict(id='TD03',field='held_count',parameter='acceptance_consecutive_sessions',expected=True),
        dict(id='TD04',field='post_creation_market_sessions',parameter='acceptance_consecutive_sessions',expected=False),
        dict(id='TD05',field='post_creation_evaluable_sessions',parameter='earliest_anchor_test_sessions',expected=False),
        dict(id='TD06',field='prior_separated_sessions',parameter='support_separated_retest_sessions',expected=True),
        dict(id='TD07',field='body_atr',parameter='impulse_body_atr_min',expected=True),
        dict(id='TD08',field='ATR20',parameter='impulse_body_atr_min',expected=False),
        dict(id='TD09',field='pivot_right_count',parameter='pivot_right_sessions',expected=True),
        dict(id='TD10',field='prior_delta3',parameter='recovery_delta3_threshold',expected=True)]
