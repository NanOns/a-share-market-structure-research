"""Atomic candidate-only Focus reader authority; accepted operational Head unchanged."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
TARGET=Path('G:/codex_tmp/v4_ui_default_r1')

def main():
    from workbench_service.current_v4_context import canonical
    from workbench_service.v4_daily_refresh import atomic_bytes
    from workbench_analysis.operational_successor_v1 import accepted_api
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    result=json.loads((ROOT/'docs/audits/v4_full_closeout_20261012/focus_pg_read/RESULT.json').read_bytes())
    authority=TARGET/'config/core_product_focus_read_authority_r2.json'
    prior=authority.read_bytes()
    out=ROOT/'docs/audits/v4_full_closeout_20261012/focus_pg_read'
    (out/'AUTHORITY_BEFORE.bin').write_bytes(prior)
    def ref(path):
        raw=path.read_bytes();return dict(path=path.relative_to(TARGET).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    head=TARGET/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';head_before=head.read_bytes()
    old=json.loads((TARGET/json.loads(prior)['manifest']['path']).read_bytes())
    assert old['head']['sha256']==result['head_token']==hashlib.sha256(head_before).hexdigest()
    manifest=dict(old,contract_id='CORE_PRODUCT_FOCUS_READ_MANIFEST_R3_NATIVE_PG',projection=result['binding'],
                  candidate_source_revision=result['source_sha256'],external_acceptance='NOT_GRANTED')
    path=TARGET/'data/v4/focus_pg_projection_closeout'/result['binding']['sha256']/'READ_MANIFEST.json'
    atomic_bytes(path,canonical(manifest))
    try:
        atomic_bytes(authority,canonical(dict(contract_id='CORE_PRODUCT_FOCUS_READ_AUTHORITY_R3_NATIVE_PG',manifest=ref(path))))
        api=accepted_api(TARGET);bff=CoreProductBFFR1(api,None)
        pack=bff.focus_projection('2026-10-09')
        assert pack and len(pack[1]['episodes'])==2805
        code,payload=bff.get('/api/v4/focus',dict(trade_date='2026-10-09',limit='30',context_token=api.token))
        assert code==200 and payload['total']==2805
        assert head.read_bytes()==head_before
    except BaseException:
        atomic_bytes(authority,prior);raise
    (out/'DEFAULT_CONSUMER_RESULT.json').write_text(json.dumps(dict(status='CANDIDATE_NATIVE_PG_FOCUS_CONSUMER_PASS',
        authority=ref(authority),manifest=ref(path),episodes=len(pack[1]['episodes']),HTTP_equivalent_code=code,
        token=api.token,production_changed=False,head_unchanged=True),ensure_ascii=False,indent=2),encoding='utf8')
    print('CANDIDATE_NATIVE_PG_FOCUS_CONSUMER_PASS')
if __name__=='__main__':main()
