import numpy as np
import pytest

from common.identity import source_identity
from common.input_snapshot import build_input_snapshot_manifest
from normalize.phase1 import DAY_DTYPE


@pytest.fixture
def gap_rows():
    rows=np.zeros(2,dtype=DAY_DTYPE);rows['date']=[20260901,20260903]
    for field in ('open','high','low','close'):rows[field]=[1000,1100]
    rows['volume']=[100,120];rows['amount']=[1000,1320]
    return rows


@pytest.fixture
def manifest_factory():
    def make(run_id='run-1',revision=1,source_sha='source-a'):
        fingerprint={
            'source_fingerprint_version':'production-source-fingerprint-v1.0',
            'source_fingerprint':source_sha,
            'source_fingerprint_components':{
                'day':'day','gbbq':'gbbq','gbbq_map':'map','tdxhy':'hy','tdxzs':'zs',
                'infoharbor_block':'block','sh_tnf':'sh','sz_tnf':'sz','bj_tnf':'bj',
                'master_calendar':'calendar','resolved_cutoff_date':'20260903'},
            'day_fingerprint_summary':{'file_count':2},'calendar_sha256':'calendar'}
        identity=source_identity(fingerprint);identity['sha256']=source_sha
        return build_input_snapshot_manifest(run_id=run_id,cutoff_date='20260903',
            source_revision_id=revision,source_identity=identity,source_fingerprint=fingerprint,
            computation_identity={'version':'computation-identity-v1.0','sha256':'computation'},
            render_identity={'version':'render-identity-v1.0','sha256':'render'},
            run_universe={'generation':'universe-generation','sha256':'universe','count':2},
            observed_at='2026-09-06T00:00:00+00:00')
    return make
