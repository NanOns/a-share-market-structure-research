import json

import pytest

from workbench_db import v4_operational_registry_pg_v1 as registry


def test_registry_reader_uses_head_bound_pg_fact_without_opening_source_file(tmp_path,monkeypatch):
    day='2026-10-12'
    source={'path':'archive/BUILDER_REGISTRY.json','sha256':'a'*64,'bytes':17}
    descriptor={'path':'data/v4/operational_owner_pg_closeout_r1/builder_registry/fact.pg.json',
        'sha256':'b'*64,'bytes':23,'pg_descriptor':{'kind':'builder_registry','fact_key':'c'*64}}
    value={'owner_bindings':{'2026-10-12':{'raw':{'path':'raw.pg','sha256':'d'*64}}},'bindings':[]}
    candidate={'accepted_trade_date':day,'owners':value['owner_bindings'],'registry':descriptor,
        registry.KEY:dict(contract_id=registry.CONTRACT,T0=day,source_binding=source,
            descriptor=descriptor,fact_token=registry._fact_token(day,source))}
    calls=[]
    monkeypatch.setattr(registry,'read_owner_fact',lambda *args,**kwargs:calls.append(args) or [value])
    monkeypatch.setattr(registry,'checked',lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('REGISTRY_FILE_OPENED')))

    assert registry.read_registry(tmp_path,candidate)==value
    assert calls and calls[0][3:6]==(day,registry.DOMAIN,source)


def test_registry_reader_rejects_descriptor_not_bound_to_candidate(tmp_path,monkeypatch):
    source={'path':'archive/BUILDER_REGISTRY.json','sha256':'a'*64,'bytes':17}
    descriptor={'path':'registry.pg.json','sha256':'b'*64,'bytes':23,'pg_descriptor':{'kind':'builder_registry'}}
    candidate={'accepted_trade_date':'2026-10-12','owners':{},'registry':{'path':'other.pg.json','sha256':'e'*64},
        registry.KEY:dict(contract_id=registry.CONTRACT,T0='2026-10-12',source_binding=source,
            descriptor=descriptor,fact_token=registry._fact_token('2026-10-12',source))}
    monkeypatch.setattr(registry,'read_owner_fact',lambda *args,**kwargs:pytest.fail('unbound registry read'))

    with pytest.raises(ValueError,match='AUTHORITY_SCOPE_MISMATCH'):
        registry.read(tmp_path,candidate)


def test_registry_prepare_appends_exact_payload_and_embeds_pg_descriptor(tmp_path,monkeypatch):
    source={'path':'archive/BUILDER_REGISTRY.json','sha256':'a'*64,'bytes':17}
    value={'owner_bindings':{'2026-10-12':{'raw':{'path':'raw.json','sha256':'d'*64}}},'bindings':[]}
    candidate={'accepted_trade_date':'2026-10-12','owners':value['owner_bindings'],'registry':source}
    calls=[]
    monkeypatch.setattr(registry,'checked',lambda root,binding:type('File',(),{'read_bytes':lambda self:json.dumps(value).encode()})())
    descriptor={'path':'data/v4/operational_owner_pg_closeout_r1/builder_registry/fact.pg.json',
        'sha256':'b'*64,'bytes':23,'pg_descriptor':{'kind':'builder_registry','fact_key':'c'*64}}
    monkeypatch.setattr(registry,'append_owner_fact',lambda *args,**kwargs:calls.append(args) or descriptor)
    monkeypatch.setattr(registry,'read_owner_fact',lambda *args,**kwargs:[value])

    receipt=registry.prepare(tmp_path,candidate)

    assert receipt['rows']==1 and candidate['registry']==descriptor
    assert candidate[registry.KEY]['source_binding']==source
    assert candidate[registry.KEY]['descriptor']==descriptor
    assert calls[0][1:5]==(registry._fact_token('2026-10-12',source),'2026-10-12',registry.DOMAIN,source)
