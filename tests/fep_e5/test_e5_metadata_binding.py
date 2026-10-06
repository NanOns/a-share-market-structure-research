"""R1R1C metadata rejection matrix; accepted predicates are immutable."""
import copy
import pytest
import os
from workbench_analysis.fep_e5 import metadata_binding as m


@pytest.mark.parametrize('case', range(1, 9), ids=lambda n: f'TM{n:02}')
def test_target_negative(case):
    a=m.authority(); row=copy.deepcopy(a['target_row']); registry=copy.deepcopy(a['target_registry'])
    if case==1:row['contract_id']='FEP_E5_OBSERVATION_V1'
    if case==2:registry['contract_id']='OTHER'
    if case==3:row['enabled']=True
    if case==4:row['horizon']=3
    if case==5:row['scope_id']='OTHER'
    if case==6:registry['targets'][0]['family']='MFE_N'
    if case==7:row['formula']='FREE_TEXT_RETURN'
    if case==8:row['enabled']=registry['targets'][0]['engineering_adapter']
    with pytest.raises(ValueError):m.verify_target(row,registry)


@pytest.mark.parametrize('case', range(1, 8), ids=lambda n: f'SM{n:02}')
def test_signal_negative(case):
    a=m.authority(); body=copy.deepcopy(a['signal_body'])
    row=dict(core_signal_contract_id=m.SIGNAL_CONTRACT,scope_id='FEP_STOCK_ENTRY_CORE',signal_key='FIRST_PREWATCH:accepted')
    if case==1:row['core_signal_contract_id']='FEP_E5_HISTORICAL_RECONSTRUCTION_AUTHORITY_V1'
    if case==2:row['core_signal_contract_id']='FEP_E5_OBSERVATION_V1'
    if case==3:row['core_signal_contract_id']='UNKNOWN'
    if case==4:row['scope_id']='OTHER'
    if case==5:body['formal_signals'].remove('FIRST_PREWATCH')
    if case==6:body['first_prewatch']='ENROLLED_ONLY'
    if case==7:row['signal_key']='NEW_CONFIRMED:accepted'
    with pytest.raises(ValueError):m.verify_signal(row,body)


def test_accepted_metadata_keeps_target_disabled():
    a=m.authority()
    assert m.verify_target(a['target_row'],a['target_registry'])
    assert not a['target_row']['enabled'] and a['target_registry']['targets'][0]['engineering_adapter']
    assert m.verify_signal(dict(core_signal_contract_id=m.SIGNAL_CONTRACT,scope_id='FEP_STOCK_ENTRY_CORE',signal_key='FIRST_PREWATCH:accepted'),a['signal_body'])


@pytest.mark.parametrize('port,kind', [(55492,'fresh'),(55493,'upgrade')])
def test_real_canonical_metadata_readback(port,kind):
    if os.environ.get('FEP_E5_CANONICAL_TEST_ENABLE')!='1':
        pytest.skip('Explicit isolated canonical fixture required')
    import psycopg
    a=m.authority()
    with psycopg.connect(f'host=127.0.0.1 port={port} user=fep_e5_admin dbname=fep_e5b_{kind}') as pg:
        row=pg.execute("select to_jsonb(t) from fep.targets t where target_id='ABS_RETURN_N:T1'").fetchone()[0]
        assert m.verify_target(row,a['target_registry'])
        rows=pg.execute("select to_jsonb(t) from fep.observations t where scope_id='FEP_STOCK_ENTRY_CORE'").fetchall()
        assert len(rows)==205 and all(m.verify_signal(x[0],a['signal_body']) for x in rows)
        bodies=dict(pg.execute('select contract_id,body from fep.contracts where contract_id in (%s,%s)',(m.TARGET_CONTRACT,m.SIGNAL_CONTRACT)).fetchall())
        assert bodies[m.TARGET_CONTRACT]['accepted_registry']==a['target_registry']
        assert bodies[m.SIGNAL_CONTRACT]['accepted_contract']==a['signal_body']
        assert pg.execute('select count(*) from fep.training_runs').fetchone()[0]==0
