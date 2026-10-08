"""R2 executable scoped/full cutover; no historical permission mutations."""
import argparse,json,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from workbench_service.production_v4 import POINTER,ProductionV4ResearchReader
from workbench_service.joint_release import AUTHORITY,activate,validate,checked_path
OUT=ROOT/'docs/evidence/r2_repair_20261008'
SCOPES=['stocks_daily','sectors_current_facts','market_current','focus_read_corrected','forward_read','diagnostics','compare_corrected']

def prepare():
    r=ProductionV4ResearchReader(ROOT);assets={}
    source=ROOT/'src/workbench_service/static/research'
    build=digest(canonical({p.name:digest(p.read_bytes()) for p in sorted(source.iterdir()) if p.is_file()}))
    for p in sorted(source.iterdir()):
        if not p.is_file():continue
        target=ROOT/'data/v4/ui_releases'/build/p.name
        if target.exists() and target.read_bytes()!=p.read_bytes():raise SourceInvalid('UI_IMMUTABILITY_CONFLICT')
        if not target.exists():write(target,p.read_bytes())
        assets[p.name]=ref(target)
    value=dict(contract_id='V4_JOINT_RELEASE_V1',ui_build_id=build,ui_assets=assets,snapshot=json.loads((ROOT/POINTER).read_bytes()),trade_date=r.context['trade_date'],operational_release_scope=SCOPES,full_product_release=False,trading=False,focus_automatic_write=False,read_only=True,owner_admission=ref(OUT/'R2_OWNER_DATE_MATRIX.json'),qa_contract=ref('config/v4_full_product_qa_contract_v2.json'),field_debt=ref(OUT/'R2_PRODUCT_FIELD_COVERAGE.json'))
    validate(ROOT,value);write(OUT/'R2_RELEASE_CANDIDATE.json',value);return value

def gate(candidate):
    qa_path=OUT/'FP13_QA_V2_FINAL.json'
    qa=json.loads(qa_path.read_bytes())
    if qa.get('contract_id')!='FP13_FULL_PRODUCT_QA_V2':raise SourceInvalid('QA_V2_REQUIRED')
    for key in ('iab_browser_pass','service_disconnect_recovery_pass','field_scope_coverage_pass'):
        if qa.get(key) is not True:raise SourceInvalid('QA_GATE_FAILED:'+key)
    if qa.get('ui_build_id')!=candidate['ui_build_id']:raise SourceInvalid('QA_UI_BUILD_MISMATCH')
    if qa.get('context_token')!='research-v4-'+candidate['snapshot']['manifest']['sha256']:raise SourceInvalid('QA_SNAPSHOT_MISMATCH')
    if qa.get('operational_release_scope')!=candidate['operational_release_scope']:raise SourceInvalid('QA_SCOPE_MISMATCH')
    for b in qa['evidence']:checked_path(ROOT,b)
    checked_path(ROOT,candidate['owner_admission']);checked_path(ROOT,candidate['field_debt']);checked_path(ROOT,candidate['qa_contract'])
    matrix=json.loads(checked_path(ROOT,candidate['owner_admission']).read_bytes())
    if matrix['trade_date']!=candidate['trade_date']:raise SourceInvalid('OWNER_ADMISSION_DATE_MISMATCH')
    manifest=json.loads(checked_path(ROOT,candidate['snapshot']['manifest']).read_bytes())
    if ref('data/v4/V4_DATA_ACCEPTED_HEAD.json')['sha256']!=manifest['context']['data_head_digest']:raise SourceInvalid('LATEST_ACCEPTED_INPUT_MISMATCH')
    if candidate.get('full_product_release') and qa.get('product_complete') is not True:raise SourceInvalid('FULL_PRODUCT_NOT_ACCEPTED')

def health(candidate):
    results={};base='http://127.0.0.1:28765'
    for route in ['/','/v4']+['/v4/research/'+x for x in ('home','sectors','stocks','focus','market','diagnostics')]:
        with urllib.request.urlopen(base+route,timeout=20) as response:raw=response.read();results[route]=dict(http=response.status,sha256=digest(raw))
        if digest(raw)!=candidate['ui_assets']['index.html']['sha256']:raise SourceInvalid('LIVE_UI_READBACK_MISMATCH')
    with urllib.request.urlopen(base+'/api/v4/context',timeout=20) as response:context=json.load(response)
    if context['context_token']!='research-v4-'+candidate['snapshot']['manifest']['sha256']:raise SourceInvalid('LIVE_READER_READBACK_MISMATCH')
    if context['context']['operational_release_scope']!=candidate['operational_release_scope']:raise SourceInvalid('LIVE_SCOPE_READBACK_MISMATCH')
    for route in ('home','stocks?limit=1','sectors?limit=1','focus?limit=1','market','diagnostics'):
        with urllib.request.urlopen(base+'/api/v4/'+route,timeout=20) as response:data=json.load(response)
        if data.get('context_token')!=context['context_token']:raise SourceInvalid('LIVE_DOMAIN_CONTEXT_MISMATCH')
        if data.get('status')!='READY':raise SourceInvalid('LIVE_DOMAIN_NOT_READY:'+route)
        results['/api/v4/'+route]=dict(status=data['status'],context_token=data['context_token'])
    return dict(pass_=True,**{'pass':True},routes=results,context_token=context['context_token'],app_read_pair_digest=digest(canonical([candidate['ui_build_id'],context['context_token'],candidate['operational_release_scope']])))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--activate',action='store_true');parser.add_argument('--expected-authority-digest');args=parser.parse_args()
    if args.activate:
        candidate=json.loads((OUT/'R2_RELEASE_CANDIDATE.json').read_bytes());gate(candidate)
        result=activate(ROOT,candidate,args.expected_authority_digest,health);write(OUT/'FP14_RELEASE_V2_FINAL.json',result);print(json.dumps(result))
    else:print(json.dumps(dict(candidate=prepare()['ui_build_id'],activation_performed=False)))
