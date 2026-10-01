"""Real notice semantics and accepted-sidecar fail-closed guards."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
import pytest
from workbench_analysis.official_event_semantics_v1 import (
    CONTRACT,parse_document_semantics,parse_dated_trading_statements,require_trading_event)
ROOT=Path(__file__).resolve().parents[2]
SIDECAR='data/v4/source_evidence/a13/OFFICIAL_NOTICE_EVENT_SEMANTICS_AMENDMENT_R1.json'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def write(root,p,v):
    path=root/p;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True),encoding='utf8')
    return dict(path=p,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def copy_binding(root,b):
    target=root/b['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/b['path']).read_bytes())
def real_event(kind):
    for entry in read(SIDECAR)['entries']:
        if entry['security_key'] is None:continue
        for event in entry['dated_trading_statements']:
            if event['actual_event_type']==kind:return entry,event
    raise AssertionError('REAL_DATED_NOTICE_EVENT_REQUIRED')
@pytest.mark.parametrize('kind',['IPO_ISSUANCE_POSTPONEMENT','IPO_LISTING_POSTPONEMENT'])
def test_misnamed_real_ipo_notices_are_never_trading_suspension(kind):
    entries=[e for e in read(SIDECAR)['entries'] if e['actual_event_type']==kind and 'suspension' in e['raw_artifact']['path']]
    assert entries
    for e in entries:
        text=(ROOT/e['semantic_text_binding']['path']).read_text(encoding='utf8')
        parsed=parse_document_semantics(text)
        assert parsed['actual_event_type']==kind and parsed['dated_trading_statements']==[]
        assert not e['consumer_permissions']['TRADING_STATUS_TRUTH']
        assert e['event_effective_date'] and e['event_date_adjudication']
@pytest.mark.parametrize('kind',['LISTED_STOCK_TRADING_SUSPENSION','LISTED_STOCK_RESUMPTION'])
def test_real_dated_trading_statements_are_explicit(kind):
    parent,event=real_event(kind)
    text=(ROOT/parent['semantic_text_binding']['path']).read_text(encoding='utf8')
    assert event in parse_dated_trading_statements(text)
    # Isolated statement still states listed-company stock behavior explicitly.
    assert parse_document_semantics(event['semantic_evidence'])['actual_event_type']==kind
def test_ambiguous_wording_stays_unknown():
    parsed=parse_document_semantics('关于暂停及暂缓有关事项的说明')
    assert parsed['actual_event_type']=='UNKNOWN_EVENT_SEMANTICS'
    assert parsed['formal_consumer_authorization'] is False
@pytest.mark.parametrize('text',[None,'','  '])
def test_filename_only_inference_rejected(text):
    with pytest.raises(ValueError,match='FILENAME_ONLY_EVENT_INFERENCE_REJECTED'):parse_document_semantics(text)
def install(root,kind='LISTED_STOCK_RESUMPTION'):
    parent,event=real_event(kind)
    for b in (parent['raw_artifact'],parent['semantic_text_binding']):copy_binding(root,b)
    item=dict(parent,**event)
    item['identity_evidence']=parent['semantic_text_binding']
    item['consumer_permissions']={'TRADING_STATUS_TRUTH':True}
    sidecar=dict(contract_id=CONTRACT,external_acceptance='EXTERNALLY_ACCEPTED',entries=[item],fixture_only=True)
    b=write(root,'fixtures/accepted_notice.json',sidecar)
    write(root,'data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_R1.json',dict(
        contract_id='OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_V1',external_acceptance='EXTERNALLY_ACCEPTED',sidecar=b,fixture_only=True))
    return sidecar,b,item
@pytest.mark.parametrize('kind',['LISTED_STOCK_TRADING_SUSPENSION','LISTED_STOCK_RESUMPTION'])
def test_accepted_fixture_requires_real_raw_and_dated_document_statement(tmp_path,kind):
    _,b,event=install(tmp_path,kind)
    assert require_trading_event(tmp_path,b,event['raw_artifact'],security_key=event['security_key'],
        effective_date=event['event_effective_date'])['actual_event_type']==kind
@pytest.mark.parametrize('mutation',['head_missing','unknown','unaccepted','raw_hash','wrong_date',
    'wrong_key','permission','text_sha','semantic_phrase','caller_accepted_sidecar_only'])
def test_formal_notice_negative_vectors(tmp_path,mutation):
    sidecar,b,event=install(tmp_path);raw=deepcopy(event['raw_artifact']);key=event['security_key'];date=event['event_effective_date']
    if mutation=='head_missing':(tmp_path/'data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_R1.json').unlink()
    elif mutation=='unknown':event['actual_event_type']='UNKNOWN_EVENT_SEMANTICS'
    elif mutation=='unaccepted':sidecar['external_acceptance']=None
    elif mutation=='raw_hash':raw['sha256']='0'*64
    elif mutation=='wrong_date':date='2026-09-29'
    elif mutation=='wrong_key':key='OTHER_IDENTITY'
    elif mutation=='permission':event['consumer_permissions']['TRADING_STATUS_TRUTH']=False
    elif mutation=='text_sha':event['semantic_text_binding']=dict(event['semantic_text_binding'],sha256='0'*64)
    elif mutation=='semantic_phrase':event['semantic_evidence']='公司股票暂缓事项'
    elif mutation=='caller_accepted_sidecar_only':b=write(tmp_path,'fixtures/other_accepted_sidecar.json',sidecar)
    if mutation not in ('head_missing','caller_accepted_sidecar_only'):
        b=write(tmp_path,'fixtures/accepted_notice.json',sidecar)
        write(tmp_path,'data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_R1.json',dict(
            contract_id='OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_V1',external_acceptance='EXTERNALLY_ACCEPTED',sidecar=b))
    with pytest.raises(ValueError):require_trading_event(tmp_path,b,raw,security_key=key,effective_date=date)
def test_actual_candidate_sidecar_cannot_authorize_any_trading_truth():
    sidecar=read(SIDECAR);assert sidecar['external_acceptance'] is None
    assert not (ROOT/'data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_R1.json').exists()
    b=dict(path=SIDECAR,sha256=hashlib.sha256((ROOT/SIDECAR).read_bytes()).hexdigest())
    for kind in ('LISTED_STOCK_TRADING_SUSPENSION','LISTED_STOCK_RESUMPTION'):
        parent,event=real_event(kind)
        with pytest.raises(ValueError,match='ACCEPTED_EVENT_SEMANTICS_REQUIRED'):
            require_trading_event(ROOT,b,parent['raw_artifact'],security_key=parent['security_key'],effective_date=event['event_effective_date'])
def test_inventory_and_full_counterfactual_proofs():
    inventory=read('reports/audits/A13_FULL_NOTICE_AND_CAPTURE_MANIFEST_INVENTORY_R1.json')
    assert inventory['named_or_capture_id_object_count']==len(read(SIDECAR)['entries'])
    assert inventory['capture_manifest_count']>=197 and not inventory['parse_errors']
    result=read('reports/audits/A13_NOTICE_REMOVAL_ADMISSION_COUNTERFACTUAL_R1.json')
    assert result['full_PIT_fact_count']==50162 and result['full_PIT_equal_to_accepted']
    assert len(set(result['full_admission_business_digests'].values()))==1
    assert all(v['security_rows_changed']==0 and v['old_business_digest']==v['new_business_digest'] for v in result['full_downstream_business_diff'].values())
    assert result['V4_08_ACCEPTED_HEAD']=='KEEP' and result['BUSINESS_REBUILD_REQUIRED'] is False
    ledger=read('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R7.json')
    assert next(e for e in ledger['entries'] if e.get('audit_id')=='OFFICIAL_NOTICE_FILENAME_VS_EVENT_SEMANTICS')['status']=='OPEN'
