"""Stage owner unit metadata and preserve actual accepted field values."""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader,build_snapshot
from workbench_service.joint_release import AUTHORITY,checked_path,validate
from workbench_service.current_v4_context import canonical,digest
OUT=ROOT/'docs/evidence/r2_available_fields_continuation_20261008'

def prepare():
    if (OUT/'CANDIDATE.json').exists():raise RuntimeError('AVAILABLE_FIELD_CANDIDATE_FROZEN')
    before=(ROOT/AUTHORITY).read_bytes();candidate=json.loads(before);old=ProductionV4ResearchReader(ROOT)
    authority=old.manifest['domain_features']['stocks']
    snapshot=build_snapshot(ROOT,publish=False,authority_overrides=candidate['daily_owner_authorities'],
        focus_override=dict(trade_date=candidate['trade_date'],input_data_head=authority['input_data_head'],
            publication=old.manifest['sources']['focus_operational'],journal=old.manifest['sources']['focus_journal']))
    candidate['snapshot']=snapshot['pointer'];source=ROOT/'src/workbench_service/static/research'
    build=digest(canonical({p.name:digest(p.read_bytes()) for p in sorted(source.iterdir()) if p.is_file()}));assets={}
    for p in sorted(source.iterdir()):
        if p.is_file():
            target=ROOT/'data/v4/ui_releases'/build/p.name
            if not target.exists():write(target,p.read_bytes())
            assert target.read_bytes()==p.read_bytes();assets[p.name]=ref(target)
    candidate.update(ui_build_id=build,ui_assets=assets);validate(ROOT,candidate)
    assert (ROOT/AUTHORITY).read_bytes()==before
    write(OUT/'CANDIDATE.json',candidate);write(OUT/'PREDECESSOR.json',dict(sha256=digest(before),authority=json.loads(before)))
    actual=ProductionV4ResearchReader(ROOT,snapshot_authority=candidate['snapshot']);registries=[json.loads(checked_path(ROOT,b).read_bytes()) for b in json.loads((ROOT/'config/v4_stock_unit_projection_v1.json').read_bytes())['registries']]
    units={(x['field_id'],x['parameter_set_id']):x['unit'] for registry in registries for x in registry['fields']};comparisons=0;declared=0;fixed=0
    with sqlite3.connect(old.path.as_uri()+'?mode=ro',uri=True) as prev,sqlite3.connect(actual.path.as_uri()+'?mode=ro',uri=True) as db:
        for domain,sid,payload in db.execute('SELECT domain,id,payload FROM objects'):
            item=json.loads(payload);prior=json.loads(prev.execute('SELECT payload FROM objects WHERE domain=? AND id=?',(domain,sid)).fetchone()[0])
            assert set(item['fields'])==set(prior['fields'])
            for field,cell in item['fields'].items():
                old_cell=prior['fields'][field]
                assert cell['value']==old_cell['value'] and cell['quality']==old_cell['quality'] and cell['source_digest']==old_cell['source_digest'],(domain,sid,field)
                comparisons+=1
                key=(field,cell.get('parameter_set_id'))
                if domain=='stocks' and key in units:
                    assert cell['unit']==units[key],(sid,field,cell['unit'],units[key]);declared+=1;fixed+=cell['unit']!=old_cell['unit']
    write(OUT/'UNIT_SOURCE_ORACLE.json',dict(result='PASS',unchanged_value_quality_source_comparisons=comparisons,
        registry_unit_comparisons=declared,unit_metadata_corrected_cells=fixed,registries=json.loads((ROOT/'config/v4_stock_unit_projection_v1.json').read_bytes())['registries'],
        strict_pit=False,raw_source_unchanged=True,snapshot=candidate['snapshot']))
    print(json.dumps(dict(result='STAGED',unit_comparisons=declared,metadata_fixed=fixed,ui_build_id=build,context_token=actual.token)))

def serve():
    import os,shutil
    from workbench_service.v4_server import serve_v4
    sandbox=Path('E:/codex_tmp/r2_available_fields_preview');previous=Path('E:/codex_tmp/r2_raw_turnover_preview')
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
    write(sandbox/AUTHORITY,candidate);validate(sandbox,candidate);serve_v4(sandbox,'127.0.0.1',28770)

if __name__=='__main__':serve() if '--serve' in sys.argv else prepare()
