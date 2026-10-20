import hashlib
import json


def _binding(path, payload):
    return {'path':path,'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)}


def test_successor_bff_reads_cohort_owner_and_grant_from_pg(tmp_path,monkeypatch):
    from workbench_service import operational_successor_bff_v1 as bff_module
    from workbench_db import v4_cohort_pg_r1 as cohort_pg
    from workbench_analysis.r43_operational_publication import digest
    from workbench_analysis import contract_registry_pg_v1 as registry
    from contextlib import nullcontext
    from types import SimpleNamespace

    day='2026-10-12'
    owner_binding={'path':'cohort/owner.json','sha256':'a'*64,'bytes':13}
    grant={
        'contract_id':'VALIDATION_COHORT_READ_GRANT_R4_V1','capability':'READ_STATISTICS',
        'authorized':True,'owner':owner_binding,'trade_date':day,
        'read_cutoff':'2026-10-12T23:59:59+08:00',
    }
    grant_raw=json.dumps(grant).encode()
    grant_path=tmp_path/'grant.json';grant_path.write_bytes(grant_raw)
    grant_binding=_binding('grant.json',grant_raw)
    owner={'contract_id':'VALIDATION_COHORT_READ_R3_V2','trade_date':day,'enrollments':[]}
    candidate={'accepted_trade_date':day,'data_cutoff_date':day,'published_sessions':[day],
        'observed_at':'2026-10-12T19:00:00+08:00',
        'owners':{day:{'validation_cohort':owner_binding}},
        'cohort_read_grants':{day:grant_binding}}

    class Api:
        root=tmp_path
        token=digest(candidate)
        embedded_pg_owner_authority=True
        def __init__(self):self.candidate=candidate;self.calls=[]
        def read(self,domain,trade_date,token):
            self.calls.append((domain,trade_date,token))
            return {'status':'READY','rows':owner}

    api=Api()
    monkeypatch.setattr(bff_module.OperationalSuccessorBFFV1,'envelope',
        lambda self,day,**payload:dict(day=day,**payload))
    monkeypatch.setattr(cohort_pg,'load_owner',lambda *args,**kwargs:owner)
    monkeypatch.setattr('workbench_db.v4_publication_reader.readonly_connection',
        lambda: nullcontext(object()))
    monkeypatch.setenv('V4_PG_MODEL_NAMESPACE_ID','cohort-test')
    identity={'database':'market_research','database_oid':646711,'host':'127.0.0.1','port':5432}
    monkeypatch.setenv('V4_PG_EXPECTED_DATABASE_IDENTITY_JSON',json.dumps(identity))
    def load_grant(cursor,contract_id,raw_sha256,namespace,*,expected_database_identity):
        assert contract_id=='VALIDATION_COHORT_READ_GRANT_R4_V1'
        assert raw_sha256==grant_binding['sha256']
        assert namespace=='cohort-test'
        assert expected_database_identity==identity
        return SimpleNamespace(contract_id=contract_id,raw_sha256=raw_sha256,
            namespace=namespace,content_format='JSON',parsed_json=grant)
    monkeypatch.setattr(registry,'load_current_approved_contract_by_digest',load_grant)

    status,payload=bff_module.OperationalSuccessorBFFV1(api,None).get(
        '/api/v4/forward/statistics',{'context_token':api.token})

    assert status==200
    assert api.calls==[]
    assert payload['data']['status']=='READY'
    assert payload['data']['observed_count']==0
