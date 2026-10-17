import hashlib
import json


def _binding(path, payload):
    return {'path':path,'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)}


def test_successor_bff_reads_validation_cohort_owner_through_embedded_pg_authority(tmp_path,monkeypatch):
    from workbench_service import operational_successor_bff_v1 as bff_module
    from workbench_db import v4_cohort_pg_r1 as cohort_pg
    from workbench_analysis.r43_operational_publication import digest

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
    monkeypatch.setattr(cohort_pg,'load_owner',lambda *args,**kwargs:(_ for _ in ()).throw(
        AssertionError('LEGACY_COHORT_OWNER_FILE_READ')))

    status,payload=bff_module.OperationalSuccessorBFFV1(api,None).get(
        '/api/v4/forward/statistics',{'context_token':api.token})

    assert status==200
    assert api.calls==[('validation_cohort',day,api.token)]
    assert payload['data']['status']=='READY'
    assert payload['data']['observed_count']==0
