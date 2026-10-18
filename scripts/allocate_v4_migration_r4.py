"""Current-baseline allocator successor; R3 historical protection is not bypassed."""
import json
import os
from datetime import datetime,timezone
from scripts.full_chain_repair_io import ROOT,write,binding,PREFIX

def _next_number(physical_numbers, allocated_numbers):
    physical=list(physical_numbers)
    if not physical or any(type(number) is not int or number<1 for number in physical):
        raise ValueError('MIGRATION_ALLOCATION_INVENTORY_INVALID')
    allocated=set(allocated_numbers)
    if any(type(number) is not int or number<1 for number in allocated):
        raise ValueError('MIGRATION_ALLOCATION_REGISTRY_INVALID')
    physical_set=set(physical);high=max(physical_set)
    reserved_missing=allocated & (set(range(1,high+1))-physical_set)
    if reserved_missing:
        raise ValueError('MIGRATION_ALLOCATION_RESERVED_FILE_MISSING:'+','.join(map(str,sorted(reserved_missing))))
    used=physical_set|allocated
    return next(number for number in range(1,max(used)+2) if number not in used)

def allocate(requestor):
    entry=json.loads((ROOT/(PREFIX+'ENTRY_BASELINE.json')).read_bytes())
    for ref in entry['protected']:
        if ref['path'].startswith('src/workbench_db/migrations/') and binding(ref['path'])!=ref:
            raise ValueError('HISTORICAL_MIGRATION_CHANGED')
    lock=ROOT/'config/.v4_unified_migration_allocator.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        path='config/v4_migration_allocation_registry_r4.json'
        registry=json.loads((ROOT/path).read_bytes()) if (ROOT/path).exists() else dict(contract_id='V4_MIGRATION_ALLOCATION_REGISTRY_R4',
            predecessor=binding('config/v4_migration_allocation_registry_r3.json'),entry=binding(PREFIX+'ENTRY_BASELINE.json'),allocations=[])
        for item in registry['allocations']:
            if item['requestor']==requestor:return item
        numbers=[int(p.name[:3]) for p in (ROOT/'src/workbench_db/migrations/v4_postgres').glob('[0-9][0-9][0-9]_*.sql')]
        for name in ('config/v4_migration_allocation_registry_r3.json','config/v4_migration_allocation_registry_fep_e1_v1.json'):
            previous=json.loads((ROOT/name).read_bytes())
            numbers += [a['number'] for a in previous.get('allocations',[]) if 'number' in a]
        numbers += [a['number'] for a in registry['allocations']]
        physical=[int(p.name[:3]) for p in (ROOT/'src/workbench_db/migrations/v4_postgres').glob('[0-9][0-9][0-9]_*.sql')]
        allocated=numbers[len(physical):]
        item=dict(number=_next_number(physical,allocated),requestor=requestor,allocated_at=datetime.now(timezone.utc).isoformat(),status='RESERVED_CANDIDATE_ONLY')
        registry['allocations'].append(item);write(path,registry);return item
    finally:os.close(fd);lock.unlink()

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--requestor',default='FULL_CHAIN_R1_FEP_SIGNAL_INTEGRITY')
    args=parser.parse_args()
    print(json.dumps(allocate(args.requestor)))
