import hashlib
import json

import pytest

from workbench_analysis import operational_successor_v1 as successor
from workbench_db import v4_operational_daily_evidence_pg_v1 as evidence


def _document(path, value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    return {'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)},raw


def test_prepare_and_reader_use_pg_for_daily_receipts_and_oracles(tmp_path,monkeypatch):
    day='2026-10-12'
    core={'oracle':[{'trade_date':day,'result':'PASS','errors':[]}],'owners':[]}
    sector={'oracle':[{'trade_date':day,'passed':True}]}
    freeze={'target_session':day}
    period={'target_session':day,'acceptance':'PASS','errors':[],'checks':1}
    sources={}
    for name,value in (('core.json',core),('sector.json',sector),('freeze.json',freeze),('period.json',period)):
        sources[name]=_document(name,value)
    receipt={'target_session':day,'acceptance':'DERIVED_READY','owners':{},
        'numeric_core_oracle':sources['core.json'][0],
        'sector_oracle':sources['sector.json'][0],
        'source_freeze':sources['freeze.json'][0]}
    receipt_binding,receipt_raw=_document('receipt.json',receipt)
    sources['receipt.json']=(receipt_binding,receipt_raw)
    candidate={'accepted_trade_date':day,'owners':{},'day_receipt':receipt_binding,
        'period_numeric_oracle':sources['period.json'][0]}
    persisted={};descriptors={}

    def local_file(root,binding):
        return type('Payload',(),{'read_bytes':lambda self:sources[binding['path']][1]})()
    def append(root,token,target_day,domain,source_binding,rows):
        descriptor={'path':domain+'/'+token+'.pg.json','sha256':token,'bytes':64,
            'pg_descriptor':{'kind':domain,'fact_key':token}}
        descriptors[token]=descriptor;persisted[token]=rows
        return descriptor
    def read_owner(root,descriptor,token,target_day,domain,source_binding,**kwargs):
        assert descriptor==descriptors[token]
        assert domain==evidence.DOMAIN and target_day==day
        return persisted[token]

    monkeypatch.setattr(evidence,'checked',local_file)
    monkeypatch.setattr(evidence,'append_owner_fact',append)
    monkeypatch.setattr(evidence,'read_owner_fact',read_owner)

    evidence.prepare(tmp_path,candidate)
    monkeypatch.setattr(evidence,'checked',lambda *args,**kwargs:pytest.fail('DAILY_EVIDENCE_FILE_OPENED'))

    assert candidate['day_receipt']==candidate[evidence.KEY]['entries']['day_receipt']['descriptor']
    assert candidate['period_numeric_oracle']==candidate[evidence.KEY]['entries']['period_numeric_oracle']['descriptor']
    assert successor._daily_evidence(tmp_path,candidate,'day_receipt')==receipt
    assert successor._daily_evidence(tmp_path,candidate,'numeric_core_oracle',receipt['numeric_core_oracle'])==core
    assert successor._daily_evidence(tmp_path,candidate,'sector_oracle',receipt['sector_oracle'])==sector
    assert successor._daily_evidence(tmp_path,candidate,'source_freeze',receipt['source_freeze'])==freeze
    assert successor._daily_evidence(tmp_path,candidate,'period_numeric_oracle')==period
    assert evidence.prepare(tmp_path,candidate)['reused'] is True
    assert len(persisted)==len(evidence.DOCUMENTS)


def test_daily_evidence_reader_rejects_source_binding_substitution(tmp_path,monkeypatch):
    day='2026-10-12'
    source={'path':'source.json','sha256':'a'*64,'bytes':4}
    descriptor={'path':'daily_evidence/fact.pg.json','sha256':'b'*64,'bytes':4,
        'pg_descriptor':{'kind':'daily_evidence','fact_key':'c'*64}}
    candidate={'accepted_trade_date':day,evidence.KEY:dict(contract_id=evidence.CONTRACT,T0=day,
        entries={'numeric_core_oracle':dict(source_binding=source,descriptor=descriptor,fact_token='c'*64)})}
    monkeypatch.setattr(evidence,'read_owner_fact',lambda *args,**kwargs:pytest.fail('SUBSTITUTED_SOURCE_READ'))

    with pytest.raises(ValueError,match='SOURCE_BINDING_MISMATCH'):
        evidence.read(tmp_path,candidate,'numeric_core_oracle',source_binding={'path':'other.json','sha256':'d'*64,'bytes':4})
