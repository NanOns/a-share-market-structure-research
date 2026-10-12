"""Recompute exact Focus validity bridge then stage complete PG read authority."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
WORK=Path('G:/codex_tmp/r4_r3_pg_publication_v2')
CANDIDATE=Path('G:/codex_tmp/v4_ui_default_r1')
OUT=ROOT/'docs/audits/v4_full_closeout_20261012/focus_pg_read'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    from scripts.r4_readonly_source_guard import install
    install(['G:/codex work/大A交易','D:/new_tdx'])
    from focus_tracker.v4_exact_identity_adapter_r4 import AcceptedPaths
    from focus_tracker.core_product_focus_r2 import enriched_project,CONTRACT as BRIDGE
    from workbench_db.v4_series_pg_r1 import verified_series_scope
    from workbench_db.v4_focus_projection_pg_closeout import build
    from workbench_service.current_v4_context import canonical
    OUT.mkdir(parents=True,exist_ok=False)
    old=json.loads((ROOT/'docs/audits/r4_r3_local_delivery_20261012/S1_IDENTITY_REPAIR_R2/RESULT.json').read_bytes())
    current=json.loads((ROOT/'docs/audits/v4_full_closeout_20261012/focus_R2/RESULT.json').read_bytes())
    bindings=current['bindings']
    # Immutable source bindings point into WORK; read projection is built there,
    # then staged with a PG descriptor in the separate default candidate.
    days={}
    for owner in old['result']['owners']:
        p=WORK/owner['D2']['path'];assert sha(p)==owner['D2']['sha256']
        days[owner['trade_date']]=json.loads(gzip.decompress(p.read_bytes()))['rows']
    source_before={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'src/focus_tracker').glob('*.py')}
    with verified_series_scope():projection=enriched_project(days,AcceptedPaths(WORK,bindings))
    projection.update(contract_id='CORE_PRODUCT_FOCUS_READ_R3_NATIVE_PG',T0=max(days),source_bindings=bindings,
                      validity_bridge_contract_id=BRIDGE,PIT_ELIGIBLE=False,AS_RECORDED=False,external_acceptance='NOT_GRANTED')
    target=CANDIDATE/'data/v4/closeout_focus_source/FOCUS.json.gz'
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise ValueError('IMMUTABLE_FOCUS_OUTPUT_ALREADY_EXISTS')
    target.write_bytes(gzip.compress(canonical(projection),mtime=0))
    source=dict(path=target.relative_to(CANDIDATE).as_posix(),bytes=target.stat().st_size,sha256=sha(target))
    head=CANDIDATE/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    token=sha(head);before=head.read_bytes()
    binding,oracle=build(CANDIDATE,source,t0=max(days),head_token=token)
    assert source_before=={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'src/focus_tracker').glob('*.py')}
    assert head.read_bytes()==before
    (OUT/'RESULT.json').write_text(json.dumps(dict(contract_id='V4_CURRENT_EXACT_FOCUS_NATIVE_PG_READ_CANDIDATE_R1',
        status='STAGED_WHOLE_PAYLOAD_READBACK_PASS',binding=binding,oracle=oracle,head_token=token,
        source_sha256=source_before,production_changed=False,default_consumer_acceptance='REQUIRED'),ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(status='STAGED_WHOLE_PAYLOAD_READBACK_PASS',episodes=len(projection['episodes']))))

if __name__=='__main__':main()
