"""New preparation contract negatives; no existing numerical suite repeated."""
import ast
import pytest
from workbench_analysis.operational_sealed_preparation_v1 import source_conservation
from workbench_analysis.r43_owner_replay import ref

def bindings(root,text,name='src/workbench_analysis/exact_operational_core_candidate_r3.py'):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf8')
    return dict(ref(root,path),module_path=name)

def test_changed_numerical_producer_rejected(tmp_path):
    old=bindings(tmp_path/'old','value = 1\n');new=bindings(tmp_path/'new','value = 2\n')
    # References resolve from a common root while retaining logical module identity.
    old['path']='old/'+old['path'];new['path']='new/'+new['path']
    with pytest.raises(ValueError,match='NUMERIC_PRODUCER_SOURCE_CHANGED'):source_conservation(tmp_path,[old],[new])

def test_post_generation_io_preserves_original_ast(tmp_path):
    name='src/workbench_analysis/operational_daily_executor_v1.py'
    before='def execute(context):\n    value = 1\n    return value\n'
    addition="    if context.get('exact_daily_policy'):\n        from .operational_product_pack_v3 import prepare\n        prepare(context)\n"
    after=before.replace('    return value\n',addition+'    return value\n')
    old=bindings(tmp_path/'old',before,name);new=bindings(tmp_path/'new',after,name)
    old['path']='old/'+old['path'];new['path']='new/'+new['path']
    result=source_conservation(tmp_path,[old],[new]);assert result['changed_source_proof'][0]['scope']=='POST_GENERATION_IO_ONLY'

def test_io_addition_cannot_hide_changed_numeric_statement(tmp_path):
    name='src/workbench_analysis/operational_daily_executor_v1.py'
    old=bindings(tmp_path/'old','def execute(context):\n    value = 1\n    return value\n',name)
    new=bindings(tmp_path/'new',"def execute(context):\n    value = 2\n    if context.get('exact_daily_policy'):\n        from .operational_product_pack_v3 import prepare\n        prepare(context)\n    return value\n",name)
    old['path']='old/'+old['path'];new['path']='new/'+new['path']
    with pytest.raises(ValueError,match='AST_CONSERVATION_FAILED'):source_conservation(tmp_path,[old],[new])
