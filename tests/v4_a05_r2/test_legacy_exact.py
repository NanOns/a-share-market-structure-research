from pathlib import Path
import ast
import json
import math
import pandas as pd
import pytest
from sector.legacy_valid_member_a05_v1 import exact_value,produce
ROOT=Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('source,state,expected',[
    ('SH.600000','BAR',True),('INVALID','BAR',False),('SZ.000001',None,False),
    ('SZ.000001','SUSPENDED',True),('BJ.920001','NOT_LISTED_YET',True),
    ('SH.600000','FILE_MISSING',False),('SH.600000','DELISTED_OR_INACTIVE',False),
    ('SH.60000','BAR',False),('SH.600000',float('nan'),False),('SH.600000','UNKNOWN',True),
])
def test_original_ast_golden_vectors(source,state,expected):
    # Direct vectorized legacy expression is the oracle, not a rewritten gate.
    ids=pd.Series([source]);states=pd.Series([state])
    actual=(ids.str.fullmatch(r'(SH|SZ|BJ)\.\d{6}') & states.notna() & ~states.isin(['FILE_MISSING','DELISTED_OR_INACTIVE'])).iloc[0]
    assert bool(actual)==expected and exact_value(source,state)==expected

def test_actual_ast_is_frozen_exactly():
    contract=json.loads((ROOT/'config/a05_legacy_valid_member_exact_v1.json').read_text(encoding='utf8'))
    module=ast.parse((ROOT/contract['source']['path']).read_text(encoding='utf8'))
    prepare=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='prepare')
    assignment=next(n for n in prepare.body if isinstance(n,ast.Assign) and 'valid_member' in ast.unparse(n.targets[0]))
    assert ast.dump(assignment,include_attributes=False)==contract['exact_ast']

def test_exact_candidate_does_not_self_accept_legacy_authority():
    row=dict(source_security_id='SH.600000',missing_state='BAR',trade_date='2026-09-24')
    ref=dict(path='immutable/observation.json',sha256='1'*64)
    result=produce(row,trade_date=row['trade_date'],source_binding=ref)
    assert result['value'] is True and result['quality']=='CANDIDATE' and result['production'] is False
    with pytest.raises(ValueError,match='EXTERNAL_ACCEPTANCE'): produce(row,trade_date=row['trade_date'],source_binding=ref,accepted_observation=True)
    with pytest.raises(ValueError,match='TIME_ROLE'): produce(row,trade_date='2026-09-25',source_binding=ref)
    with pytest.raises(ValueError,match='SOURCE_BINDING'): produce(row,trade_date=row['trade_date'],source_binding={})

def test_real_541_original_byte_bound_outputs_match_exact_recovery():
    from scripts.verify_a02_a05_candidate_readback_r1 import verify_a05
    result=verify_a05()
    assert result['mismatches']==0 and result['real_sector_outputs_checked']==541 and result['original_bytes_match_legacy_receipt'] is True
    assert result['real_golden_member_values_checked']==3553

def test_old_v4_08_head_is_immutable_and_b2_formal_gate_stays_unknown():
    proof=json.loads((ROOT/'reports/audits/A05_EXACT_RECOVERY_EVIDENCE_R2.json').read_text(encoding='utf8'))
    from hashlib import sha256
    ref=proof['v4_08_accepted_head']
    assert sha256((ROOT/ref['path']).read_bytes()).hexdigest()==ref['sha256']
    assert proof['formal_consumer_enabled'] is False
