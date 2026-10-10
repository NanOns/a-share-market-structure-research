"""Independent reference: no production imports; expected extraction gates."""
import json
import sys
from datetime import datetime, timezone, timedelta

FIELDS=('CONFIRMED','WARM','frozen_invalidation','episode_invalidation_contract_id','followup_complete','scenario')

def reference(row):
    # Current real source contains Native facts only, none of six D2 owners.
    return dict(entity_id=row['sector_id'],entity_type='SECTOR',
        unique_member_count=len(set(row['member_ids'])),missing_fields=list(FIELDS),
        readiness='SOURCE_INCOMPLETE',maturity=None,health=None,
        formal_consumer_enabled=False,accepted=False)

if __name__=='__main__':
    data=json.load(open(sys.argv[1],encoding='utf8'))
    output=dict(input_source=data['source_binding'],rows=[reference(r) for r in data['rows']],
        verdict='SOURCE_NOT_PRESENT_FOR_SIX_D2_FIELDS',production_authorized=False)
    with open(sys.argv[2],'w',encoding='utf8',newline='\n') as f:json.dump(output,f,ensure_ascii=False,indent=2)
