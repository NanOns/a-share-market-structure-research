"""Read-only Owner lookup accepts PG bytes after the source archive is absent."""
from contextlib import contextmanager
import pytest

import workbench_db.v4_operational_owner_pg_closeout as owner_pg


def test_owner_read_uses_inline_pg_descriptor_and_never_opens_source(tmp_path,monkeypatch):
    day='2026-10-09';domain='core';head='h'*64
    source={'path':'missing/source.json','sha256':'a'*64,'bytes':99}
    rows=[{'security_id':'FIXTURE','trade_date':day,'value':17}]
    payload=dict(contract_id=owner_pg.OWNER,head_token=head,T0=day,domain=domain,
        source_binding=source,rows=rows,PIT_ELIGIBLE=False,AS_RECORDED=False)
    payload_raw=owner_pg.canonical(payload).decode()
    payload_sha=owner_pg.digest(payload_raw.encode())
    schema='v4_forward_0123456789abcdef'
    fact_key=head+'_'+day+'_'+domain
    descriptor=dict(contract_id=owner_pg.CONTRACT,engine='postgresql',schema=schema,
        kind=domain,fact_key=fact_key,payload_sha256=payload_sha,
        database_identity={'system_identifier':'fixture'})
    descriptor_raw=owner_pg.canonical(descriptor)
    binding=dict(path=f'{owner_pg.FOLDER}/{domain}/{owner_pg.digest(fact_key.encode())}.pg.json',
        sha256=owner_pg.digest(descriptor_raw),bytes=len(descriptor_raw),pg_descriptor=descriptor)

    class Cursor:
        def fetchone(self):
            return (payload_raw,payload_sha)

    class PG:
        def execute(self,*_args):return Cursor()

    @contextmanager
    def readonly_connection(selected_schema,*,read_only=False):
        assert selected_schema==schema and read_only is True
        yield PG()

    monkeypatch.setattr(owner_pg,'connection',readonly_connection)
    monkeypatch.setattr(owner_pg,'read_schema',lambda *_args,**_kwargs:schema)
    monkeypatch.setattr(owner_pg.ForwardFactStore,'_database_identity',lambda _pg:{'system_identifier':'fixture'})
    assert not (tmp_path/'missing/source.json').exists()
    assert owner_pg.read(tmp_path,binding,head,day,domain,source)==rows


def test_owner_read_rejects_source_binding_drift_from_pg_fact(tmp_path,monkeypatch):
    source={'path':'missing/source.json','sha256':'a'*64,'bytes':99}
    day='2026-10-09';head='h'*64
    stored_source={'path':'other/source.json','sha256':'b'*64,'bytes':99}
    payload=dict(contract_id=owner_pg.OWNER,head_token=head,T0=day,domain='core',
        source_binding=stored_source,rows=[],PIT_ELIGIBLE=False,AS_RECORDED=False)
    payload_raw=owner_pg.canonical(payload).decode()
    payload_sha=owner_pg.digest(payload_raw.encode())
    descriptor={'contract_id':owner_pg.CONTRACT,'engine':'postgresql','schema':'v4_forward_0123456789abcdef',
        'kind':'core','fact_key':head+'_'+day+'_core','payload_sha256':payload_sha,
        'database_identity':{'system_identifier':'fixture'}}
    from workbench_db.v4_forward_pg_r1 import canonical,digest
    raw=canonical(descriptor)
    binding={'path':f"{owner_pg.FOLDER}/core/{digest(descriptor['fact_key'].encode())}.pg.json",
        'sha256':digest(raw),'bytes':len(raw),'pg_descriptor':descriptor}

    class Cursor:
        def fetchone(self):return (payload_raw,payload_sha)
    class PG:
        def execute(self,*_args):return Cursor()
    from contextlib import contextmanager
    @contextmanager
    def readonly_connection(*_args,**_kwargs):yield PG()
    monkeypatch.setattr(owner_pg,'connection',readonly_connection)
    monkeypatch.setattr(owner_pg,'read_schema',lambda *_args,**_kwargs:descriptor['schema'])
    monkeypatch.setattr(owner_pg.ForwardFactStore,'_database_identity',lambda _pg:descriptor['database_identity'])
    with pytest.raises(ValueError,match='CONTEXT_MISMATCH'):
        owner_pg.read(tmp_path,binding,head,day,'core',source)
