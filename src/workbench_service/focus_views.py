"""FP08 typed read projections. Absence of an outcome is never an Episode."""

KINDS=('episodes','timeline','anchors','observations','outcomes')
SCHEMAS={
    'episodes':['episode_id','entity_id','T0','observations','anchors'],
    'timeline':['episode_id','entity_id','trade_date','event','idempotency_key'],
    'anchors':['episode_id','entity_id','anchor_id','trade_date','kind'],
    'observations':['episode_id','entity_id','trade_date','event','source_publication'],
    'outcomes':['episode_id','entity_id','trade_date','outcome_status'],
}

def focus_view(reader,entity,kind,query):
    publication=reader.manifest.get('domain_features',{}).get('focus') or {}
    episodes=[x for x in publication.get('episodes',[]) if x['entity_id']==entity]
    if kind=='episodes': rows=episodes
    elif kind=='timeline': rows=[x for x in publication.get('events',[]) if x['entity_id']==entity]
    else:
        rows=[dict(x,episode_id=ep['episode_id'],entity_id=entity)
              for ep in episodes for x in ep.get(kind,[])]
    missing=not publication or kind=='outcomes' and not rows
    offset=int(query.get('offset',0));limit=int(query.get('limit',30))
    return reader.envelope(status='SOURCE_INCOMPLETE' if missing else 'READY' if rows else 'EMPTY_VALID',
        items=rows[offset:offset+limit],total=len(rows),offset=offset,limit=limit,has_next=offset+limit<len(rows),
        resource_type=kind,item_schema=SCHEMAS[kind],contract_id='R2_FOCUS_TYPED_READ_V2',
        reason='FOCUS_OWNER_OUTCOMES_NOT_PUBLISHED' if missing and kind=='outcomes' else 'FOCUS_OWNER_NOT_BOUND' if missing else None,
        source=reader.manifest.get('sources',{}).get('focus_operational'),
        permissions=publication.get('permissions'),write_block_reason=publication.get('write_block_reason'),legacy_history=publication.get('legacy_history'))
