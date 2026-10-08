"""Immutable Focus successor snapshot; never mutate live authorities."""
import copy,json,shutil,sqlite3,sys,uuid,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.run_r2_focus_continuation import OUT
from focus_tracker.v4_path_adapter import checked,CONTRACT
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from workbench_service.production_v4 import ProductionV4ResearchReader,compact_cell
from workbench_service.joint_release import AUTHORITY,validate


def main():
    before=(ROOT/AUTHORITY).read_bytes();base=json.loads(before)
    receipt=json.loads((OUT/'SHADOW_READBACK.json').read_bytes())
    if receipt['status']!='SHADOW_SOURCE_PASS' or not receipt['append_failure_exact_rollback'] or not receipt['oracle']:
        raise SourceInvalid('FOCUS_SHADOW_GATE_FAILED')
    publication=json.loads(checked(ROOT,receipt['publication']).read_bytes())
    publication['write_block_reason']='CONTINUOUS_DAILY_DRIVER_NOT_YET_ADMITTED'
    publication['shadow_acceptance']=ref(OUT/'SHADOW_READBACK.json')
    published_path=ROOT/'data/v4/r2_focus_journal'/receipt['second']['head']/('publication_'+digest(canonical(publication))+'.json')
    write(published_path,publication);published=ref(published_path)
    reader=ProductionV4ResearchReader(ROOT);day=reader.context['trade_date']
    if publication['trade_date']!=day:raise SourceInvalid('FOCUS_SNAPSHOT_DATE_MIX')
    directory=ROOT/'data/v4/research_snapshots'/uuid.uuid4().hex;directory.mkdir(parents=True)
    path=directory/'focus_research.sqlite';shutil.copyfile(reader.path,path)
    meta=copy.deepcopy(reader.manifest);meta.pop('database')
    meta['domain_features']['focus']=publication
    meta['sources']['focus_operational']=published
    meta['sources']['focus_journal']=receipt['journal']
    for name,binding in receipt['sources']['implementation'].items():meta['sources']['focus_kernel_'+name]=binding
    meta['release_id']=directory.name;meta['built_at']=datetime.now(timezone.utc).isoformat()
    meta['metadata'].update(release_id=directory.name,published_at=meta['built_at'],
        input_digest=digest(canonical(meta['sources'])))
    meta['gaps']=[g for g in meta['gaps'] if g['domain']!='focus']+[dict(domain='focus',state='SOURCE_INCOMPLETE',
        reason='PARTIAL_PATH_PREDICATE_OWNERS_AND_UNRECONCILED_LEGACY_PG',next='ADMIT_MISSING_PREDICATES_INDEPENDENTLY')]
    with sqlite3.connect(path) as db:
        oldrows={json.loads(p)['entity_id']:(identifier,json.loads(p)) for identifier,p in db.execute("SELECT id,payload FROM objects WHERE domain='focus'")}
        db.execute("DELETE FROM objects WHERE domain='focus'")
        for ep in {e['entity_id']:e for e in sorted(publication['episodes'],key=lambda e:e['T0'])}.values():
            identifier,item=oldrows[ep['entity_id']]
            last=ep['observations'][-1]
            values={**last,**{k:ep[k] for k in ('episode_id','T0','end_date','parent_episode_id')}}
            fields={k:compact_cell(dict(value=v,quality='UNKNOWN' if v is None or v=='UNKNOWN' else 'KNOWN',
                reason=last.get('path_reason') if k=='path_state' else 'OWNER_VALUE_UNAVAILABLE' if v is None or v=='UNKNOWN' else None,
                contract_id=CONTRACT),published,k,day) for k,v in values.items()}
            item['fields']=fields
            db.execute('INSERT INTO objects VALUES(?,?,?,?,?,?)',('focus',identifier,item['display_name'].casefold(),item.get('symbol',''),last.get('scenario') or '',canonical(item).decode()))
        # Correct quality in the new projection only; original source and old
        # snapshot bytes are retained as the independent anomaly evidence.
        for domain,identifier,payload in db.execute('SELECT domain,id,payload FROM objects').fetchall():
            item=json.loads(payload);changed=False
            for cell in item.get('fields',{}).values():
                if cell.get('value')=='UNKNOWN' and cell.get('quality')=='KNOWN':
                    cell.update(quality='UNKNOWN',reason='OWNER_LITERAL_UNKNOWN_NOT_A_KNOWN_VALUE');changed=True
            if changed:db.execute('UPDATE objects SET payload=? WHERE domain=? AND id=?',(canonical(item).decode(),domain,identifier))
        meta['counts']['focus']=db.execute("SELECT count(*) FROM objects WHERE domain='focus'").fetchone()[0]
        db.execute("UPDATE metadata SET value=? WHERE key='snapshot'",(canonical(meta).decode(),))
        db.commit()
    write(directory/'manifest.json',dict(meta,database=ref(path)))
    pointer=dict(contract_id='V4_RESEARCH_SNAPSHOT_AUTHORITY_V1',manifest=ref(directory/'manifest.json'),previous=base['snapshot'])
    candidate=copy.deepcopy(base);candidate['snapshot']=pointer
    assets={};static=ROOT/'src/workbench_service/static/research'
    build=digest(canonical({p.name:digest(p.read_bytes()) for p in sorted(static.iterdir()) if p.is_file()}))
    for p in sorted(static.iterdir()):
        if not p.is_file():continue
        target=ROOT/'data/v4/ui_releases'/build/p.name
        if target.exists() and target.read_bytes()!=p.read_bytes():raise SourceInvalid('UI_IMMUTABILITY_CONFLICT')
        if not target.exists():write(target,p.read_bytes())
        assets[p.name]=ref(target)
    candidate.update(ui_build_id=build,ui_assets=assets)
    candidate['app_version']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    candidate['focus_journal_admission']=ref(OUT/'SHADOW_READBACK.json')
    candidate['focus_automatic_write']=False
    validate(ROOT,candidate)
    write(OUT/'CANDIDATE.json',candidate)
    assert before==(ROOT/AUTHORITY).read_bytes()
    write(OUT/'SNAPSHOT_READBACK.json',dict(status='CANDIDATE_SOURCE_PASS',snapshot=pointer,
        counts=meta['counts'],live_authority_preserved=True,production_activated=False,
        next_stage='ISOLATED_HTTP_IAB_THEN_JOINT_CAS'))
    print(json.dumps(dict(status='CANDIDATE_SOURCE_PASS',release_id=directory.name,counts=meta['counts'])))

if __name__=='__main__':main()
