"""Bind verified formal snapshot and series without changing accepted Heads."""
import hashlib,json,sys
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(SOURCE),str(SOURCE/'src')]
ROOT=Path('G:/codex work/v4-production-20261012')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/formal_snapshot_binding_r1')
def main():
    from workbench_service.v4_daily_refresh import atomic_bytes
    from workbench_service.current_v4_context import canonical
    OUT.mkdir(parents=True,exist_ok=False)
    def ref(path):
        raw=path.read_bytes();return dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    protected={n:(ROOT/'data/v4'/n).read_bytes() for n in ('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')}
    results={}
    for label in ('MAINR1','SERIESR1'):
        result=json.loads((OUT.parent/'formal_snapshot_transfer'/label/'RESULT.json').read_bytes())
        if result['status']!='FORMAL_PG_FULL_TABLE_TRANSFER_DIGEST_PASS' or result['whole_content_manifest_difference']!=0:raise ValueError('FORMAL_COMPLETE_TRANSFER_REQUIRED')
        if result['target']!=ref(ROOT/result['target']['path']):raise ValueError('FORMAL_DESCRIPTOR_CHANGED')
        results[label]=result
    joint_path=ROOT/'config/v4_joint_release_authority_v1.json';joint=json.loads(joint_path.read_bytes())
    manifest_path=ROOT/joint['snapshot']['manifest']['path'];manifest=json.loads(manifest_path.read_bytes())
    manifest['database']=results['MAINR1']['target']
    target=manifest_path.with_name('FORMAL_MANIFEST_R1.json');atomic_bytes(target,canonical(manifest))
    joint['snapshot']['manifest']=ref(target)
    joint['daily_owner_authorities']['stocks']['series']=results['SERIESR1']['target']
    atomic_bytes(joint_path,canonical(joint))
    research=ROOT/'config/v4_research_snapshot_authority_v1.json'
    prior=json.loads(research.read_bytes())
    atomic_bytes(research,canonical(dict(contract_id=prior['contract_id'],manifest=ref(target),previous=prior)))
    stocks=ROOT/'config/v4_stock_operational_authority_v1.json';stock=json.loads(stocks.read_bytes());stock['series']=results['SERIESR1']['target'];atomic_bytes(stocks,canonical(stock))
    for name,raw in protected.items():
        if (ROOT/'data/v4'/name).read_bytes()!=raw:raise ValueError('ACCEPTED_HEAD_CHANGED')
    (OUT/'RESULT.json').write_bytes(canonical(dict(status='FORMAL_SNAPSHOT_AND_SERIES_BINDING_STAGED',snapshot=ref(target),series=results['SERIESR1']['target'],head_unchanged=True,production_activated=False,consumer_acceptance='REQUIRED')))
    print('FORMAL_SNAPSHOT_AND_SERIES_BINDING_STAGED')
if __name__=='__main__':main()
