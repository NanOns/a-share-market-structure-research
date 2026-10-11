import ast,json,os,subprocess,sys
from pathlib import Path

def test_rank_function_formula_ast_matches_frozen_helper():
    root=Path(__file__).resolve().parents[1]
    def function(path):
        return next(x for x in ast.parse(path.read_text(encoding='utf8')).body if isinstance(x,ast.FunctionDef) and x.name=='_exact_cycle_delta')
    assert ast.dump(function(root/'src/sector/rank_comparison_r1.py'),include_attributes=False)==ast.dump(function(root/'src/workbench_service/research_builder.py'),include_attributes=False)

def test_pure_rank_import_and_execution_need_no_legacy_builder_or_database():
    root=Path(__file__).resolve().parents[1]
    program='''
import importlib.abc,sys,json,sqlite3
class Forbidden(BaseException):pass
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='workbench_service.research_builder' or fullname.startswith('workbench_db'):raise Forbidden(fullname)
sys.meta_path.insert(0,Block())
def reject(*args,**kwargs):raise Forbidden('sqlite3.connect')
sqlite3.connect=reject
from sector.rank_comparison_r1 import _exact_cycle_delta,SECTOR_CYCLE_CONTRACT
import pandas as pd
rows=[dict(trade_date=pd.Timestamp(day).date(),sector_id=sid,sector_type='INDUSTRY',q5=value,contract_id=SECTOR_CYCLE_CONTRACT) for day,values in [('2026-10-08',[('A',.25),('B',.75)]),('2026-10-09',[('A',.75),('B',.25)])] for sid,value in values]
result=_exact_cycle_delta(pd.DataFrame(rows),'2026-10-09','2026-10-08',dict(thresholds=dict(coverage=dict(max_rank_universe_change=0,min_rank_intersection_union=1)))).set_index('sector_id')
assert result.loc['A','dq5_3']==.5 and result.loc['B','dq5_3']==-.5
assert 'workbench_service.research_builder' not in sys.modules
assert not any(k.startswith('workbench_db') for k in sys.modules)
print(json.dumps(dict(A=float(result.loc['A','dq5_3']),B=float(result.loc['B','dq5_3']),legacy_builder_loaded=False,database_package_loaded=False)))
'''
    env=dict(os.environ,PYTHONPATH=str(root/'src'),TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([sys.executable,'-B','-c',program],cwd=root,env=env,text=True,capture_output=True,check=True)
    assert json.loads(result.stdout)==dict(A=.5,B=-.5,legacy_builder_loaded=False,database_package_loaded=False)
