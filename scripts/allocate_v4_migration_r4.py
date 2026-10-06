"""Current-baseline allocator successor; R3 historical protection is not bypassed."""
import json
import os
from datetime import datetime,timezone
from scripts.full_chain_repair_io import ROOT,write,binding,PREFIX

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
        if sorted(numbers)!=list(range(1,max(numbers)+1)):raise ValueError('MIGRATION_ALLOCATION_GAP')
        for name in ('config/v4_migration_allocation_registry_r3.json','config/v4_migration_allocation_registry_fep_e1_v1.json'):
            previous=json.loads((ROOT/name).read_bytes())
            numbers += [a['number'] for a in previous.get('allocations',[]) if 'number' in a]
        numbers += [a['number'] for a in registry['allocations']]
        item=dict(number=max(numbers)+1,requestor=requestor,allocated_at=datetime.now(timezone.utc).isoformat(),status='RESERVED_CANDIDATE_ONLY')
        registry['allocations'].append(item);write(path,registry);return item
    finally:os.close(fd);lock.unlink()

if __name__=='__main__':print(json.dumps(allocate('FULL_CHAIN_R1_FEP_SIGNAL_INTEGRITY')))
