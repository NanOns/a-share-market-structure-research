"""Versioned REV2 §10F required-input guard; frozen V3 AST remains intact."""
from math import isfinite
from scripts.v4_04_machine_executor_r4 import execute_rule as frozen_execute_rule

CONTRACT_ID='V4_04_INDEPENDENT_MACHINE_REQUIRED_INPUT_GUARD_V4'

def execute_rule(rules,key,evidence,parameters):
    if key=='COMPRESSION_STATE_V1':
        numeric=('range_ratio','atr_ratio','vol_ratio','amount_ratio20')
        if any(isinstance(evidence.get(k),bool) or not isinstance(evidence.get(k),(int,float)) or not isfinite(evidence[k]) for k in numeric) or not isinstance(evidence.get('minimum_liquidity'),bool):
            return 'UNKNOWN'
    return frozen_execute_rule(rules,key,evidence,parameters)
