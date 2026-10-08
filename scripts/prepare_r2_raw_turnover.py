"""Stage actual RAW amount/volume facts without changing live authority."""
import copy,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader,build_snapshot
from workbench_service.joint_release import AUTHORITY,checked_path,validate
from workbench_service.current_v4_context import canonical,digest
OUT=ROOT/'docs/evidence/r2_raw_turnover_continuation_20261008'

def prepare():
    if (OUT/'CANDIDATE.json').exists():raise RuntimeError('RAW_TURNOVER_CANDIDATE_FROZEN')
    before=(ROOT/AUTHORITY).read_bytes();candidate=json.loads(before);reader=ProductionV4ResearchReader(ROOT)
    authority=reader.manifest['domain_features']['stocks']
    write(ROOT/'config/v4_raw_amount_volume_projection_v1.json',dict(contract_id='R2_RAW_AMOUNT_VOLUME_PROJECTION_V1',
        unit_contract=authority['sources']['unit_contract'],units=dict(amount='CNY',volume='SHARES'),price_basis='RAW_UNADJUSTED',
        scale=1,source='ACCEPTED_RAW_DAILY_A_SHARE_SCOPE_ONLY',strict_pit=False,
        independent_audit='AUD_R2_RAW_AMOUNT_VOLUME_PRESENTATION',does_not_close='M10_AMOUNT_A_CROSS_MODULE_AUDIT'))
    snapshot=build_snapshot(ROOT,publish=False,authority_overrides=candidate['daily_owner_authorities'],
        focus_override=dict(trade_date=candidate['trade_date'],input_data_head=authority['input_data_head'],
            publication=reader.manifest['sources']['focus_operational'],journal=reader.manifest['sources']['focus_journal']))
    candidate['snapshot']=snapshot['pointer']
    source=ROOT/'src/workbench_service/static/research';build=digest(canonical({p.name:digest(p.read_bytes()) for p in sorted(source.iterdir()) if p.is_file()}));assets={}
    for p in sorted(source.iterdir()):
        if p.is_file():
            target=ROOT/'data/v4/ui_releases'/build/p.name
            if not target.exists():write(target,p.read_bytes())
            assert target.read_bytes()==p.read_bytes();assets[p.name]=ref(target)
    candidate.update(ui_build_id=build,ui_assets=assets);validate(ROOT,candidate)
    assert (ROOT/AUTHORITY).read_bytes()==before
    write(OUT/'CANDIDATE.json',candidate);write(OUT/'PREDECESSOR.json',dict(sha256=digest(before),authority=json.loads(before)))
    actual=ProductionV4ResearchReader(ROOT,snapshot_authority=candidate['snapshot'])
    raw=json.loads(checked_path(ROOT,actual.manifest['sources']['RAW_DAILY']).read_bytes())['rows'];raw_lookup={r['security_id']:r for r in raw}
    count=0;plausible=0;positive=0
    with sqlite3.connect(actual.path.as_uri()+'?mode=ro',uri=True) as db,sqlite3.connect(checked_path(ROOT,authority['series']).as_uri()+'?mode=ro',uri=True) as series:
        for p, in db.execute('SELECT payload FROM objects WHERE domain=?',('stocks',)):
            item=json.loads(p);r=raw_lookup[item['entity_id']]
            historical=json.loads(series.execute('SELECT payload FROM bars WHERE security=? AND day=?',(item['entity_id'],candidate['trade_date'])).fetchone()[0])
            for field,unit in [('amount','CNY'),('volume','SHARES')]:
                cell=item['fields'][field];assert cell['value']==r[field]==historical[field]
                assert cell['unit']==unit and cell['source_as_of']==candidate['trade_date'] and cell['source_digest']==actual.manifest['sources']['RAW_DAILY']['sha256']
                count+=1
            if r['volume']>0:
                positive+=1;price=r['amount']/r['volume'];plausible+=r['low']*.95<=price<=r['high']*1.05
    assert count==5213*2
    write(OUT/'REAL_SOURCE_ORACLE.json',dict(result='PASS',accepted_stocks=len(raw),raw_value_comparisons=count,series_value_comparisons=count,
        amount_div_volume_crosscheck=dict(positive_volume_rows=positive,plausible_rows=plausible,tolerance=.05,ratio=plausible/positive),
        source=actual.manifest['sources']['RAW_DAILY'],series=authority['series'],unit_contract=authority['sources']['unit_contract'],snapshot=candidate['snapshot'],strict_pit=False))
    print(json.dumps(dict(result='STAGED',comparisons=count,ui_build_id=build,context_token=actual.token)))

def serve():
    import os,shutil
    from workbench_service.v4_server import serve_v4
    sandbox=Path('E:/codex_tmp/r2_raw_turnover_preview');previous=Path('E:/codex_tmp/r2_presentation_preview')
    for p in previous.rglob('*'):
        if p.is_file() and p.relative_to(previous).parts[0] in ('data','config'):
            target=sandbox/p.relative_to(previous)
            if not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(p,target) if p.relative_to(previous).parts[0]=='config' else os.link(p,target)
    candidate=json.loads((OUT/'CANDIDATE.json').read_bytes());manifest=validate(ROOT,candidate)
    for binding in [candidate['snapshot']['manifest'],manifest['database'],*manifest['sources'].values(),*candidate['ui_assets'].values()]:
        target=sandbox/binding['path'];target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copyfile(ROOT/binding['path'],target)
    write(sandbox/AUTHORITY,candidate);validate(sandbox,candidate);serve_v4(sandbox,'127.0.0.1',28769)

if __name__=='__main__':serve() if '--serve' in sys.argv else prepare()
