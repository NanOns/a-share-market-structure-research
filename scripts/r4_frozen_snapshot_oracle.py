"""Separate frozen pre-R4 SQLite producer oracle, never a V4 runtime fallback."""
import json,os,subprocess,sys,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
BASE='fbd23a6ba08d0948fe7ad421d1765fe363648522'

def main():
    import workbench_service.production_v4
    source=subprocess.check_output(['git','show',BASE+':src/workbench_service/production_v4.py'],cwd=ROOT)
    module=types.ModuleType('workbench_service.production_v4');module.__package__='workbench_service';module.__file__='FROZEN_'+BASE+'_production_v4.py'
    sys.modules[module.__name__]=module
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    pointer=ROOT/'config/v4_research_snapshot_authority_v1.json';before=pointer.read_bytes()
    staged=module.build_snapshot(ROOT,publish=False)
    if pointer.read_bytes()!=before:raise ValueError('FROZEN_ORACLE_POINTER_CHANGED')
    manifest=json.loads((ROOT/staged['pointer']['manifest']['path']).read_bytes())
    target=Path('G:/codex_tmp/full_system_r4_fbd23a6b/snapshot_candidate/frozen_producer_oracle.json')
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/r4_sqlite_readonly_oracle.py'),'--source',str(ROOT/manifest['database']['path']),'--output',str(target),'--kind','snapshot'],check=True)
    result=dict(contract_id='R4_FROZEN_PRODUCER_MIGRATION_ORACLE_R1',source_SHA=BASE,staged=staged,oracle=str(target),scope='Separate source comparison process, SQLite production runtime remains prohibited',protected_pointer_unchanged=True)
    temp=target.with_name('frozen_producer_receipt.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(temp,target.with_name('frozen_producer_receipt.json'))
    print(json.dumps(dict(status='FROZEN_PRODUCER_STAGED',counts=staged['counts'])))
if __name__=='__main__':main()
