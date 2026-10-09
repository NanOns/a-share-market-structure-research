"""Bounded real HTTP verification after operational CAS."""
import json
from urllib.request import urlopen
from urllib.parse import urlencode,urlparse
from .operational_successor_v1 import digest


def readback(base,candidate):
    parsed=urlparse(base)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost'):
        raise ValueError('LOCAL_HTTP_READBACK_REQUIRED')
    token=digest(candidate);day=candidate['accepted_trade_date'];checks=[]
    for path in ('/api/v4/context','/api/operations/status','/api/v4/stocks','/api/v4/sectors','/api/v4/market','/api/v4/focus'):
        url=base+path+'?'+urlencode(dict(context_token=token,trade_date=day,limit=3))
        with urlopen(url,timeout=30) as response:
            raw=response.read(4*1024*1024+1)
            if len(raw)>4*1024*1024:raise ValueError('HTTP_READBACK_SIZE_LIMIT')
            payload=json.loads(raw)
        context=payload.get('context',{})
        if payload.get('context_token')!=token or context.get('accepted_trade_date')!=day:
            raise ValueError('HTTP_READBACK_TOKEN_OR_DATE_MISMATCH')
        if payload.get('status') in ('SOURCE_INCOMPLETE','UNKNOWN'):raise ValueError('HTTP_REQUIRED_DOMAIN_NOT_READY')
        checks.append(dict(path=path,context_token=token,accepted_trade_date=day,status='PASS'))
    return dict(status='PASS',context_token=token,accepted_trade_date=day,checks=checks)
