from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import pytest
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.fep_e1.datasets import assemble
from workbench_analysis.fep_e2.input import bind
from workbench_analysis.fep_e2.conditional import baseline, statistics, quantile, LEVELS
from workbench_analysis.fep_e2.support import inventory, gate, discover
from workbench_analysis.fep_e2.registry import register

CONTRACT = dict(contract_id='CONDITIONAL_EXPECTANCY_V1',levels=[[n,list(k)] for n,k in LEVELS],
                weighting='BUCKET_EQUAL_DATE_RATIONAL_V1',quantile='INVERSE_EMPIRICAL_CDF_V1')
POLICY = dict(policy_id='TEST_ONLY_NOT_ADMITTED',freeze_before_statistics_at='2026-10-05T00:00:00Z',
              values=dict(rows=2,dates=2,blocks=2,entities=2,episodes=2,class_min=1,
                          max_missing_fraction=0.5,max_total_variation=0.5),required_classes=['POS','NEG'])
POLICY['applicability']=dict(entity_type='STOCK',observation_scope='FEP_STOCK_ENTRY_CORE',signal_type='ENTRY',
    target='target',horizon=1,feature_variant='CORE',evidence_origin='RECONSTRUCTED_ASOF',
    label_quality_policy='ENGINEERING',contract_versions={'feature':'V1','target':'V1'},target_kind='CONTINUOUS')
NOW='2026-10-05T10:00:00Z'


def fixture(values=(-.1,.2), kind='CONTINUOUS', classes=(), revision=1):
    observations=[]; labels={}; snapshots={}; envelopes={}
    for i,value in enumerate(values):
        key='o'+str(i); date='2026-09-'+str(10+i).zfill(2)
        observations.append(dict(observation_id=key,scope_id='FEP_STOCK_ENTRY_CORE',
                                 entity_id='entity'+str(i),trade_date=date,episode_key=key))
        snapshots[key]=dict(snapshot_id='snapshot'+str(i))
        revisions=[] if value is None else [dict(revision=revision,target_digest=digest(value),
                    training_allowed=True,source_fact_available_at='2026-10-01T00:00:00Z',
                    label_revision_available_at='2026-10-01T00:00:00Z',label_training_mature_at='2026-10-01T00:00:00Z')]
        labels[key,'target']=revisions
        row=dict(observation_id=key,entity_type='STOCK',observation_scope='FEP_STOCK_ENTRY_CORE',
                 signal_type='ENTRY',target='target',horizon=1,feature_variant='CORE',evidence_origin='RECONSTRUCTED_ASOF',
                 label_quality_policy='ENGINEERING',contract_versions={'feature':'V1','target':'V1'},
                 entity_id='entity'+str(i),trade_date=date,date_ordinal=i*2,label_end_ordinal=i*2+1,
                 episode_start=i*2,episode_end=i*2+1,regime='R',trend='T',position='P',risk='K',
                 feature_support='KNOWN',sector='UNAVAILABLE',support_class=('POS' if value and isinstance(value,(int,float)) and value>0 else 'NEG'))
        if value is not None:row.update(outcome=value,selected_label_revision=revision,selected_label_digest=digest(value))
        envelopes[key]=row
    folds=[dict(fold_id='f1',partition_name='FIT',observation_ids=list(envelopes),
                fold_dataset_cutoff='2026-10-02T00:00:00Z',phase_started_at='2026-10-03T00:00:00Z')]
    e1=assemble(observations,[dict(target_id='target',scope_id='FEP_STOCK_ENTRY_CORE',horizon=1)],
                folds,labels,snapshots,'2026-10-03T00:00:00Z')
    return bind(e1,dict(dataset_id='ENGINEERING_VECTOR',feature_contract_id='FEATURE_V1',target_contract_id='TARGET_V1',
                fold_id='f1',partition_name='FIT',target='target',target_kind=kind,classes=list(classes)),envelopes)


def run(d=None,p=None,now=NOW):
    d=d or fixture();return baseline(d,d['denominator'][0],p or POLICY,CONTRACT,now)


def rebind(d):
    d['rows']=[r for r in d['denominator'] if r['status']=='ELIGIBLE']
    d['digest']=digest({k:v for k,v in d.items() if k!='digest'})
    return d


def test_e2_01_bucket_weight():
    s,w=statistics([dict(observation_id='a',trade_date='d',outcome=.1,weight=.5)],'CONTINUOUS',[])
    assert s['weighted_mean']==.1 and s['positive_empirical_frequency']==1


def test_e2_02_quantile():
    assert quantile([1,2,3],[Fraction(1,4),Fraction(1,2),Fraction(1,4)],Fraction(1,2))==2
    assert quantile([1,2],[Fraction(1,2)]*2,Fraction(1,2))==1


def test_e2_03_negative_supported():
    d=fixture((-.4,.1,.8));d['denominator'][2]['position']='OTHER';rebind(d)
    a=run(d);assert a['selected_level']=='L4' and a['statistics']['weighted_mean']<0


def test_e2_04_fallback():
    d=fixture();d['denominator'][1]['position']='OTHER';rebind(d)
    assert run(d)['selected_level']=='L3'


def test_e2_05_thin():
    p=deepcopy(POLICY);p['values']['rows']=100
    assert run(p=p)['support_state']=='THIN_ROWS' and run(p=p)['diagnostic_only']


def test_e2_06_one_date():
    rows=fixture()['rows']*50
    rows=deepcopy(rows)
    for r in rows:r['trade_date']='same'
    assert gate(rows,rows,POLICY)[0]=='THIN_DATES'


def test_e2_07_overlap():
    rows=deepcopy(fixture()['rows'])
    for r in rows:r.update(entity_id='one',episode_start=0,episode_end=100)
    p=deepcopy(POLICY);p['values']['entities']=1
    assert gate(rows,rows,p)[0]=='THIN_EPISODES'


@pytest.mark.parametrize('field,value',[('observation_scope','DAILY'),('target','other'),('horizon',3),
                                       ('evidence_origin','PIT_OBSERVED'),('feature_variant','SECTOR'),
                                       ('contract_versions',{'feature':'V2'})])
def test_e2_08_09_10_cross_base(field,value):
    d=fixture();d['denominator'][1][field]=value;rebind(d)
    with pytest.raises(ValueError):run(d)


def test_e2_11_categorical():
    d=fixture(('NONE','EXIT'),kind='CATEGORICAL',classes=['NONE','EXIT'])
    s,_=statistics(d['rows'],'CATEGORICAL',d['classes'])
    assert sum(s['observed_weighted_frequency'].values())==1 and s['observed_weighted_frequency']['NONE']==.5


def test_e2_12_any_overlap():
    rows=[dict(observation_id='a',trade_date='d',outcome=dict(ANY_CONFIRM=True,ANY_INVALIDATE=True,ANY_EXPIRE=False))]
    s,_=statistics(rows,'ANY_EVENTS',list(rows[0]['outcome']))
    assert sum(s['observed_weighted_frequency'].values())==2


def test_e2_13_missing_denominator():
    d=fixture((-.1,.2,None));a=run(d)
    assert a['denominator_summary']['expected']==3 and a['denominator_summary']['statuses']['MISSING_LABEL']==1


def test_e2_14_representativeness():
    p=deepcopy(POLICY);p['values']['max_total_variation']=0
    a=run(fixture((-.1,.2,None)),p);assert a['support_state']=='REPRESENTATIVENESS_FAIL' and not a['full_population_claim']


def test_e2_15_revision():
    early=fixture(revision=1);before=run(early)
    late=fixture(revision=2);latest=fixture(revision=3)
    assert run(early)==before and before['label_revision_selections'][0]['selected_label_revision']==1
    assert len({run(d)['logical_digest'] for d in (early,late,latest)})==3
    broken=deepcopy(early);broken['rows'][0]['selected_label_revision']=3;rebind(broken)
    with pytest.raises(ValueError):run(broken)


def test_e2_16_timestamp():
    assert run()['logical_digest']==run(now='2026-10-06T00:00:00Z')['logical_digest']


def test_e2_17_policy():
    p=deepcopy(POLICY);p['values']['rows']=3
    assert run()['logical_digest']!=run(p=p)['logical_digest']


def test_e2_18_no_grants():
    a=run();assert a['artifact_type']=='CONDITIONAL_STATISTICS_BASELINE'
    assert a['MODEL_DISPLAY']==a['PRIORITY_USE']=='UNGRANTED' and not a['production']


def test_e2_19_20_isolation_and_registry(tmp_path):
    root=Path(__file__).resolve().parents[2]
    protected=list((root/'src/workbench_analysis/fep_e1').glob('*.py'))
    protected+=list((root/'config').glob('*priority*'))
    before={str(p):digest(p.read_text(encoding='utf-8')) for p in protected}
    a=run();path=register(tmp_path/'registry',a);original=path.read_bytes()
    register(tmp_path/'registry',run(now='2026-10-06T00:00:00Z'))
    assert path.read_bytes()==original
    a['statistics']['weighted_mean']=999
    with pytest.raises(ValueError):register(tmp_path/'registry',a)
    assert before=={str(p):digest(p.read_text(encoding='utf-8')) for p in protected}


def test_discovery_no_outcome_performance():
    d=fixture();a=discover(d['denominator'],d['rows'])
    for r in d['rows']:r['outcome']*=1000
    assert discover(d['denominator'],d['rows'])==a


def test_unset_and_freeze():
    p=deepcopy(POLICY);p['values']['rows']='UNSET'
    assert run(p=p)['support_state']=='NOT_EVALUABLE'
    with pytest.raises(ValueError):run(now=p['freeze_before_statistics_at'])
