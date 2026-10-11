from copy import deepcopy
import pytest
from workbench_db.v4_shadow_pg_r2 import build_readback, read, digest
from workbench_db.v4_native import connection


def vector(root):
    payload=dict(namespace='SHADOW_V4',execution_mode='SHADOW',evidence_origin='PIT_OBSERVED',value=None)
    return build_readback(root,[dict(kind='vector',id='one',payload=payload)],environment='REAL',evidence_origin='PIT_OBSERVED')


@pytest.mark.parametrize('mutation', ['payload','delete','origin'])
def test_shadow_admin_content_corruption_rejected(tmp_path,mutation):
    descriptor=vector(tmp_path)
    with connection(descriptor['schema']) as pg:
        pg.execute('ALTER TABLE facts DISABLE TRIGGER immutable_shadow')
        pg.execute('ALTER TABLE storage_identity DISABLE TRIGGER immutable_shadow')
        if mutation=='payload':pg.execute("UPDATE facts SET payload='{}'")
        elif mutation=='delete':pg.execute('DELETE FROM facts')
        else:pg.execute("UPDATE storage_identity SET environment='ACTIVATION_SIMULATION'")
    with pytest.raises(ValueError,match='MISMATCH'):
        with read(descriptor):pass
    with pytest.raises(ValueError,match='MISMATCH'):
        vector(tmp_path)  # idempotent path also verifies full content


def test_shadow_resigned_database_mismatch(tmp_path):
    descriptor=deepcopy(vector(tmp_path))
    descriptor['database_identity']['system_identifier']='0'
    descriptor['logical_digest']=digest({k:v for k,v in descriptor.items() if k!='logical_digest'})
    with pytest.raises(ValueError,match='DATABASE_IDENTITY_MISMATCH'):
        with read(descriptor):pass
