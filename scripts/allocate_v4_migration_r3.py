"""Unified serialized R3 allocator; prior registries and migrations are immutable."""
import argparse,os,time,json
from datetime import datetime,timezone
from scripts.next_round_bundle_r2 import ROOT,BASELINE,MASTER,read,write,bind,verify_protected
REGISTRY='config/v4_migration_allocation_registry_r3.json'

def allocate(requestor):
    verify_protected();lock=ROOT/'config/.v4_unified_migration_allocator.lock';deadline=time.monotonic()+10
    while True:
        try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);break
        except FileExistsError:
            if time.monotonic()>deadline:raise ValueError('UNIFIED_MIGRATION_ALLOCATOR_BUSY')
            time.sleep(.1)
    try:
        paths=sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('[0-9][0-9][0-9]_*.sql'))
        nums=[int(p.name[:3]) for p in paths]
        if nums!=list(range(1,max(nums)+1)):raise ValueError('MIGRATION_ALLOCATION_GAP')
        registry=read(REGISTRY) if (ROOT/REGISTRY).exists() else dict(contract_id='V4_MIGRATION_ALLOCATION_REGISTRY_R3',baseline_commit=BASELINE,
            supersedes=bind('config/v4_migration_allocation_registry_r2.json'),authority=bind(MASTER),historical_bindings=[bind(p.relative_to(ROOT).as_posix()) for p in paths],allocations=[])
        for a in registry['allocations']:
            if a['requestor']==requestor:return a
        used=nums+[a['number'] for a in registry['allocations']];number=max(used)+1
        allocation=dict(number=number,requestor=requestor,allocated_at=datetime.now(timezone.utc).isoformat(),status='RESERVED_FOR_R2_CANDIDATE_SEMANTIC_CONSTRAINT')
        registry['allocations'].append(allocation);registry['next_free_number']=number+1;write(REGISTRY,registry,immutable=False);return allocation
    finally:os.close(fd);lock.unlink(missing_ok=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--requestor',required=True);args=p.parse_args();print(json.dumps(allocate(args.requestor)))
