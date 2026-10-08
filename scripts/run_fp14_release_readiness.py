"""Prepare a truthful candidate; an unmet product gate never switches authority."""
import argparse,json,os,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.fp_domain_evidence import check_protected
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from workbench_service.production_v4 import ProductionV4ResearchReader,rollback_snapshot,POINTER
from workbench_service.v4_daily_refresh import atomic_bytes
OUT=ROOT/'docs/evidence/fp14_20261008'

def readiness(qa):
    reasons=[]
    for field,expected in [('acceptance','PASS'),('product_complete',True),('required_field_coverage_pass',True),('edge_pass',True),('offline_pass',True)]:
        if qa.get(field)!=expected:reasons.append('FP13_GATE_NOT_PASSED:'+field)
    return reasons

def prepare():
    r=ProductionV4ResearchReader(ROOT);qa_path=ROOT/'docs/evidence/fp13_20261008/FINAL_ACCEPTANCE.json';qa=json.loads(qa_path.read_bytes());reasons=readiness(qa)
    before={p:ref(p) for p in (POINTER,'config/v4_research_ui_authority_v1.json','config/v4_production_runtime_authority_v1.json')}
    assets=[ref(p) for p in sorted((ROOT/'src/workbench_service/static/research').glob('*')) if p.is_file()]
    verified=[]
    for name,binding in r.manifest['sources'].items():
        actual=ref(binding['path'])
        if actual['sha256']!=binding['sha256']:raise SourceInvalid('CANDIDATE_SOURCE_DIGEST_MISMATCH:'+name)
        verified.append(dict(name=name,binding=actual))
    metadata=r.manifest['metadata'];versions={}
    for name,source in r.manifest['sources'].items():
        if source.get('contract_id'):versions[name]=source['contract_id']
    candidate=dict(contract_id='FP14_RELEASE_CANDIDATE_V1',app_version=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),operational_capabilities=dict(scoped_read_only=r.manifest['counts'],full_product=False,focus_write=False),accepted_model_versions=versions,last_processed_trade_date=r.context['trade_date'],source_head_digests=dict(data=r.context['data_head_digest'],stage=r.context['stage_head_digest']),runtime_read_contract=r.manifest['sources']['read_contract'],research_authority=ref(POINTER),source_owner_matrix=r.manifest['sources'],release_metadata=metadata,ui_build_id=digest(canonical(assets)),ui_assets=assets,ui_authority=ref('config/v4_research_ui_authority_v1.json'),rollback_target=r.authority.get('previous'),qa_receipt=ref(qa_path),release_contract=ref('config/v4_full_product_release_contract_v1.json'),default_route_check={},result='BLOCKED',reasons=reasons or ['FULL_RELEASE_EXECUTOR_NOT_ADMITTED_NO_IMPLICIT_ACTIVATION'],activation_performed=False,statistical_advantage_claim=False)
    for route in ('/','/v4','/v4/research/home','/v4/shadow','/v3'):
        with urllib.request.urlopen('http://127.0.0.1:28765'+route,timeout=30) as response:
            raw=response.read();candidate['default_route_check'][route]=dict(http=response.status,sha256=digest(raw),bytes=len(raw))
    assert candidate['default_route_check']['/']['sha256']==candidate['default_route_check']['/v4']['sha256']==candidate['default_route_check']['/v4/research/home']['sha256']
    candidate['source_digest_verification']=verified
    candidate['full_owner_semantic_admission']=False
    assert before=={p:ref(p) for p in before}
    candidate['authorities_preserved']=True
    write(OUT/'RELEASE_CANDIDATE_MANIFEST.json',candidate)
    write(OUT/'RELEASE_RESULT.json',dict(result='BLOCKED',reasons=candidate['reasons'],activation_performed=False,authorities_preserved=True,candidate=ref(OUT/'RELEASE_CANDIDATE_MANIFEST.json'),protected=check_protected(OUT),next_stage='Resolve independent FP13 product/browser gates; then request stage re-evaluation'))
    print(json.dumps(dict(result='BLOCKED',activation_performed=False,reasons=candidate['reasons'])))
    return 2

def rehearse():
    """Byte-for-byte real releases copied under a separate root, no live swap."""
    real=ProductionV4ResearchReader(ROOT);before=ref(POINTER);sandbox=ROOT/'runtime/fp14_rehearsal';current=(ROOT/POINTER).read_bytes();authority=json.loads(current);previous=authority.get('previous')
    if not previous:raise SourceInvalid('NO_REAL_PREVIOUS_SNAPSHOT')
    ui=ref('config/v4_research_ui_authority_v1.json')
    references=[ui]
    for target in (authority,previous):
        manifest_ref=target['manifest'];manifest=json.loads((ROOT/manifest_ref['path']).read_bytes());references += [manifest_ref,manifest['database']]
        stocks=manifest.get('domain_features',{}).get('stocks')
        if stocks:references.append(stocks['series'])
    for binding in {x['path']:x for x in references}.values():
        raw=(ROOT/binding['path']).read_bytes()
        if digest(raw)!=binding['sha256']:raise SourceInvalid('REAL_REHEARSAL_SOURCE_DIGEST_MISMATCH')
        target=sandbox/binding['path'];atomic_bytes(target,raw)
    atomic_bytes(sandbox/POINTER,current)
    before_reader=ProductionV4ResearchReader(sandbox);counts=before_reader.manifest['counts'];sample=before_reader.query('stocks',{'limit':1})['items'][0]
    rollback=rollback_snapshot(sandbox,digest(current));old_reader=ProductionV4ResearchReader(sandbox)
    assert old_reader.token!=before_reader.token
    try:rollback_snapshot(sandbox,'0'*64)
    except SourceInvalid:cas_conflict=True
    else:raise AssertionError('STALE_CAS_ACCEPTED')
    # Restore the exact retained pointer under the same serialization convention.
    path=sandbox/POINTER;old_raw=path.read_bytes();expected=digest(old_raw);lock=path.with_suffix('.lock');fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        os.close(fd)
        if digest(path.read_bytes())!=expected:raise SourceInvalid('SNAPSHOT_CAS_CONFLICT')
        atomic_bytes(path,current)
        try:restored=ProductionV4ResearchReader(sandbox)
        except Exception:atomic_bytes(path,old_raw);raise
    finally:lock.unlink()
    assert restored.token==before_reader.token and restored.manifest['counts']==counts
    assert restored.query('stocks',{'limit':1})['items'][0]==sample
    assert before==ref(POINTER)
    write(OUT/'REAL_ISOLATED_ROLLBACK.json',dict(scope='ISOLATED_REAL_RESEARCH_SNAPSHOTS_NOT_LIVE_PRODUCT_RELEASE',before=before_reader.token,rollback=rollback,restored=restored.token,cas_conflict_rejected=cas_conflict,counts=counts,sample_restored=True,ui_authority_digest=ui['sha256'],ui_changed=False,live_authority_preserved=True,focus_forward_writes=0,live_browser_rollback='NOT_EXECUTED_FP13_GATE_BLOCKED'))
    print('Real isolated predecessor rollback / exact restore / stale CAS rejection PASS')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rehearse-rollback',action='store_true');a=p.parse_args()
    if a.rehearse_rollback:rehearse()
    else:raise SystemExit(prepare())
