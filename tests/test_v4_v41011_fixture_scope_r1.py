"""An attested SQL test fixture never becomes a general database grant."""
import pytest,psycopg
from scripts.v4_closeout_v41011_sql_fixture import DATABASE,connection
from scripts.v4_closeout_phase0_clean_fixture import DATABASE as PHASE0_DATABASE,connection as phase0_connection
from tests.v4_native_isolation_plugin_r4 import V4DatabaseGuardViolation

@pytest.mark.parametrize('params',[connection(DATABASE),phase0_connection(PHASE0_DATABASE)])
def test_verified_sql_fixture_rejects_unrelated_test_scope(params):
    with pytest.raises(V4DatabaseGuardViolation,match='R4_UNATTESTED_PG_FORBIDDEN'):
        psycopg.connect(**params)
