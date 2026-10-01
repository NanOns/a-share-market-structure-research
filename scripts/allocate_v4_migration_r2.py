"""Single serialized allocator for the authorized next-round migrations."""
from datetime import datetime,timezone
from pathlib import Path
import argparse,json,os,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.next_round_bundle_r1 import read,bind,write,verify_protected
REGISTRY='config/v4_migration_allocation_registry_r2.json'
def allocate(requestor):
    verify_protected()
    lock=ROOT/'config/.v4_migration_allocator_r2.lock';deadline=time.monotonic()+10
    while True:
        try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);break
        except FileExistsError:
            if time.monotonic()>deadline:raise ValueError('MIGRATION_ALLOCATOR_BUSY')
            time.sleep(.1)
    try:
        paths=sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('[0-9][0-9][0-9]_*.sql'))
        numbers=[int(p.name[:3]) for p in paths]
        if numbers!=list(range(1,max(numbers)+1)):raise ValueError('MIGRATION_NUMBER_GAP')
        registry=read(REGISTRY) if (ROOT/REGISTRY).exists() else dict(contract_id='V4_MIGRATION_ALLOCATION_REGISTRY_R2',
            supersedes=bind('config/v4_migration_allocation_registry_r1.json'),baseline_commit='bc3e398efb4f4a05c20973ff3cb335a6b101ac87',
            historical_bindings=[bind(p.relative_to(ROOT).as_posix()) for p in paths],allocations=[],authority='NEXT_ROUND_MASTER_R1_IMPLEMENTATION_SCOPE')
        for a in registry['allocations']:
            if a['requestor']==requestor:return a
        used=numbers+[a['number'] for a in registry['allocations']];number=max(used)+1
        allocation=dict(number=number,requestor=requestor,allocated_at=datetime.now(timezone.utc).isoformat(),status='RESERVED_FOR_CANDIDATE_SCHEMA')
        registry['allocations'].append(allocation);registry['next_free_number']=number+1
        write(REGISTRY,registry,immutable=False);return allocation
    finally:os.close(fd);lock.unlink(missing_ok=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--requestor',required=True);args=p.parse_args();print(json.dumps(allocate(args.requestor)))
