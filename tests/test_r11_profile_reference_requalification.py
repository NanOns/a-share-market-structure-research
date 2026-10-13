import json
from pathlib import Path
from scripts.v4_04_machine_executor_r4 import execute_rule
from v4.profile_core import extension_risk,severe_extension
from workbench_analysis.tdx_official_daily_source import sha256_file


def test_six_fixed_real_branch_inputs_match_independent_contract_oracle():
    root=Path(__file__).resolve().parents[1]
    fixture=json.loads((root/'tests/fixtures/r11_profile_branch_6.json').read_text('utf-8'))
    assert fixture['scan_rows']==5225 and len(fixture['cases'])==6
    assert sha256_file(root/'src/v4/profile_core.py')==fixture['accepted_kernel_sha256']
    contracts=json.loads((root/'config/v4_04_algorithm_contracts_v3.json').read_text('utf-8'))
    params={x['parameter_id']:x['value'] for x in json.loads((root/'config/v4_04_parameter_set_v1.json').read_text('utf-8'))['parameters']}
    for case in fixture['cases']:
        risk=extension_risk(case['evidence'])
        oracle=execute_rule(contracts['rules'],'EXTENSION_RISK_V1',case['evidence'],params)
        assert oracle==risk.value==case['new_risk']
        assert case['old_risk']=='UNKNOWN' and risk.unknown_reason is None
        severe=severe_extension(risk)
        assert severe.value is False and severe.unknown_reason is None


def test_unresolved_high_conjunction_still_unknown():
    risk=extension_risk(dict(bias20_atr=0,ret5=None,atr20=1,close=10,amount_ratio20=10,ret1=-0.01))
    assert risk.value=='UNKNOWN' and risk.unknown_reason=='REQUIRED_INPUT_UNKNOWN'
    assert severe_extension(risk).value is None


def test_qualified_overlay_preserves_all_unaffected_rows_and_rejects_unknown_entity():
    import pytest
    from scripts.verify_v4_append_full_values_r1_1 import apply_qualified
    old={'A':dict(value=1),'B':dict(value=2)}
    fresh=apply_qualified(old,{'A':dict(value=3)})
    assert fresh=={'A':dict(value=3),'B':dict(value=2)} and old['A']['value']==1
    with pytest.raises(ValueError,match='ENTITY_NOT_IN_OLD_REFERENCE'):apply_qualified(old,{'C':dict(value=4)})


def test_qualified_reference_requires_real_oracle_pass_and_exact_scope(tmp_path):
    import pytest
    from scripts.verify_v4_append_full_values_r1_1 import qualified_rows
    (tmp_path/'RESULT.json').write_text(json.dumps(dict(acceptance='FAIL')))
    with pytest.raises(ValueError,match='SCOPE_OR_ORACLE_REQUIRED'):qualified_rows(tmp_path,{})
