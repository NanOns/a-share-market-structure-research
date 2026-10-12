import pytest
from workbench_service.exact_candidate_chart_r3 import candidate

def test_explicit_engineering_gate_precedes_every_io():
    with pytest.raises(ValueError,match='CAPABILITY_DISABLED'):
        candidate('G:/codex work/r4-pg-only-20261011',{},engineering_enable=False)

def test_production_workspace_rejected_before_source_or_pg_io():
    with pytest.raises(ValueError,match='ISOLATION_REQUIRED'):
        candidate('G:/codex work/r4-pg-only-20261011',{},engineering_enable=True)

@pytest.mark.parametrize('query',[{'period':'X'},{'limit':0},{'limit':201},{'offset':-1}])
def test_bad_queries_refused_before_source_pg_access(query):
    with pytest.raises(ValueError,match='CHART_QUERY_INVALID'):
        candidate('G:/codex_tmp/no-source-is-required',query,engineering_enable=True)
