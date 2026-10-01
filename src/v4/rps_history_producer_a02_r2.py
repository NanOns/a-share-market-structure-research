"""Compatible V1 publication producer with explicit small-universe UNKNOWN."""
from .rps_pit_history_a02_v1 import publish as publish_v1,digest

def publish(input_payload,previous=None):
    for horizon in ('5','20'):
        values=input_payload['returns'][horizon]
        if any(isinstance(v,bool) for v in values.values()): raise ValueError('A02_RETURN_BOOLEAN_NOT_NUMBER')
    publication=publish_v1(input_payload,previous)
    # Rank formula and real published scores remain exactly unchanged. The
    # missing-rank reason has precedence over valid individual endpoint metadata.
    for row in publication['rows']:
        for field in ('rps5','rps20'):
            value=row[field]
            if value['value'] is None and value['unknown_reason'] is None:
                value['unknown_reason']='INSUFFICIENT_EVALUABLE_UNIVERSE'
    publication['logical_digest']=digest({k:v for k,v in publication.items() if k!='logical_digest'})
    return publication
