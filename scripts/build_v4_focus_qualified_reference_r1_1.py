"""Single-day independent qualified oracle; accepted prior chain is read-only."""
import argparse,hashlib,json,os,sys,time
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from workbench_analysis.r43_owner_replay import load,checked,ref,gzrows,gzwrite
from workbench_analysis import r43_focus_replay as focus
from workbench_analysis.operational_owner_adapter_v1 import private_scope
from workbench_analysis.operational_increment_plan_v1 import focus_predecessor

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--generation',required=True);p.add_argument('--correction-dir',required=True);args=p.parse_args()
    root=Path(args.root).resolve();generation=root/args.generation;old=root/'data/v4/dynamic_daily_owners/2026-10-13/35e5a7c80925e59b640bcc694df1184e8bb850634b10085473cd26f6b9b89b57'
    out=generation/'qualified_focus_reference_r1_1';out.mkdir(exist_ok=True)
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    from workbench_db import v4_series_pg_r1 as series
    from workbench_db.v4_snapshot_pg_r2 import grant_verifier
    from psycopg import connect
    credentials=load_credentials(root/'config/native_pg_roles.dpapi')
    os.environ.update(V4_NATIVE_PG_DSN=credentials[ROLES[1]],V4_NATIVE_PG_READER_DSN=credentials[ROLES[0]])
    original=series.build
    def build(root,path,rows,**kw):
        d=original(root,path,rows,**kw)
        with connect(credentials[ROLES[1]],connect_timeout=5) as pg:grant_verifier(pg,d['schema'],ROLES[0],tables=('objects','aliases','members','metadata','bars','snapshot_identity'))
        return d
    series.build=build
    parent=load(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');prior=focus_predecessor(root,parent['owners'])
    profiles=load(old/'owner_v3/PROFILE_STRUCTURE_REPLAY.json');target=profiles['owners'][-1]
    sectors=load(old/'sector_v3/SECTOR_REPLAY.json');sector=sectors['owners'][-1]
    corrections=Path(args.correction_dir);pb=load(corrections/'PROFILE_AFFECTED6.json')['rows'];sb=load(corrections/'SEED_AFFECTED6.json')['rows']
    corrected_profiles={r['security_id']:r for r in pb};corrected_seeds={r['security_id']:r for r in sb}
    profile_rows=gzrows(checked(root,target['owner']['profiles']));seed_rows=gzrows(checked(root,sector['seed']))
    qualified_profile=gzwrite(root,out/'QUALIFIED_PROFILE.jsonl.gz',[corrected_profiles.get(r['security_id'],r) for r in profile_rows])
    qualified_seed=gzwrite(root,out/'QUALIFIED_SEED.jsonl.gz',[corrected_seeds.get(r['security_id'],r) for r in seed_rows])
    target=dict(target,owner=dict(target['owner'],profiles=qualified_profile));sector=dict(sector,seed=qualified_seed)
    (out/'PROFILE_STRUCTURE_REPLAY.json').write_text(json.dumps(dict(profiles,owners=[target]),ensure_ascii=False),encoding='utf8')
    (out/'SOURCE_BINDINGS.json').write_bytes((old/'owner_v3/SOURCE_BINDINGS.json').read_bytes())
    cutoff=load(generation/'owner_v3/owners/2026-10-13/structure/runtime_manifest.json')['available_at']
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls,tz=None):
            d=datetime.fromisoformat(cutoff);return d.astimezone(tz) if tz else d.replace(tzinfo=None)
    def mapped_load(path):
        if Path(path).resolve()==(root/'docs/evidence/r4_3_four_session_closeout_20261009/sector_v3/SECTOR_REPLAY.json').resolve():return dict(sectors,owners=[sector])
        if Path(path).resolve()==(root/'docs/evidence/source_acquisition_r4_20261009/capture/acquisition.json').resolve():return load(old/'sources/acquisition.json')
        return load(path)
    def version_ref(base,path):
        path=Path(path).resolve()
        if not path.is_relative_to(root):
            raw=path.read_bytes();archive=out/'executed_sources'/hashlib.sha256(raw).hexdigest()/path.name;archive.parent.mkdir(parents=True,exist_ok=True)
            if not archive.exists():archive.write_bytes(raw)
            path=archive
        return ref(base,path)
    scope=private_scope(focus,dict(OUT=out.relative_to(root).as_posix(),load=mapped_load,ref=version_ref,datetime=FrozenDatetime))
    started=time.monotonic();print('Qualified full 5225 Focus reference: compute_sessions=[2026-10-13]',flush=True)
    result=scope['materialize_focus'](root,predecessor_state=prior)
    receipt=dict(contract_id='V4_R1_1_QUALIFIED_SINGLE_DAY_FOCUS_REFERENCE',acceptance='REFERENCE_GENERATED_NOT_PRODUCTION',
        compute_sessions=['2026-10-13'],securities=result['owners'][-1]['rows'],elapsed_seconds=round(time.monotonic()-started,3),focus=result['focus'],
        qualified_profile=qualified_profile,qualified_seed=qualified_seed,parent_focus=parent['owners'][parent['accepted_trade_date']]['focus'])
    (out/'REFERENCE_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
