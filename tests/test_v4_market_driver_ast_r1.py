import json
from pathlib import Path
import pytest
from workbench_analysis.operational_market_context_correction_r1 import driver_scope

def test_approved_driver_pair_rejects_formula_change():
    root=Path('G:/codex work/v4-production-20261012')
    policy=json.loads((root/'data/v4/exact_daily_policies_v2/8e6abfc22c1a7a996c293113defa92ccee5a9d93a55dee1e43cb8dcc4e3171e1/POLICY.json').read_bytes())
    binding=next(b for b in policy['accepted_algorithm_bindings'] if b.get('module_path')=='src/workbench_analysis/r43_market_replay.py')
    old=(root/binding['path']).read_text();new=Path('src/workbench_analysis/r43_market_replay.py').read_text()
    driver_scope(old,new,'materialize_market')
    with pytest.raises(ValueError,match='EXACT_APPROVED_DRIVER_AST'):
        driver_scope(old,new.replace('int(a>0)-int(b>0)','int(a>1)-int(b>0)'),'materialize_market')
