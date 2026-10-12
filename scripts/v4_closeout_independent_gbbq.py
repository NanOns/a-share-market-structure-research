"""Independent bulk Feistel decoder over the declared expanded key data.

The primary decoder is never imported by decode(). The expanded key is shared
format data, not an independent key discovery or external audit claim.
"""
import hashlib,json,struct
from pathlib import Path
from typing import NamedTuple
import numpy as np
from tdx._gbbq_key import GBBQ_KEY_BYTES

CONTRACT='V4_INDEPENDENT_GBBQ_BULK_FEISTEL_ORACLE_R1'

class Event(NamedTuple):
    security_id:str
    raw_code:str
    event_date:int
    category:int
    c1:float
    c2:float
    c3:float
    c4:float
    source_record_index:int
    market_byte:int

def decode(raw):
    if len(raw)<4:raise ValueError('INDEPENDENT_GBBQ_HEADER_REQUIRED')
    count=int.from_bytes(raw[:4],'little')
    if len(raw)!=4+29*count:raise ValueError('INDEPENDENT_GBBQ_EXACT_DENOMINATOR_REQUIRED')
    if not count:return []
    schedule=np.frombuffer(GBBQ_KEY_BYTES,dtype='<u4')
    p=schedule[:18];s=schedule[18:1042].reshape(4,256)
    blocks=np.ndarray((count,3,2),dtype='<u4',buffer=raw,offset=4,strides=(29,8,4))
    left=blocks[:,:,0].copy();right=blocks[:,:,1].copy()
    # Conventional sixteen-round reversed-P Blowfish Feistel formulation.
    # Array uint32 arithmetic wraps modulo 2**32 at each addition.
    for index in range(17,1,-1):
        left=np.bitwise_xor(left,p[index])
        mixed=np.add(s[0,left>>24],s[1,(left>>16)&255],dtype=np.uint32)
        mixed=np.bitwise_xor(mixed,s[2,(left>>8)&255])
        mixed=np.add(mixed,s[3,left&255],dtype=np.uint32)
        right=np.bitwise_xor(right,mixed)
        left,right=right,left
    left,right=right,left
    right=np.bitwise_xor(right,p[1]);left=np.bitwise_xor(left,p[0])
    output=np.stack((left,right),axis=-1).astype('<u4').view('u1').reshape(count,24)
    records=np.ndarray((count,29),dtype='u1',buffer=raw,offset=4,strides=(29,1)).copy()
    records[:,:24]=output
    results=[]
    for index,row in enumerate(records):
        payload=row.tobytes();market=payload[0];code=payload[1:8].rstrip(b'\0').decode('ascii',errors='replace')
        symbol={0:'SZ',1:'SH',2:'BJ'}.get(market,'UNKNOWN_'+str(market))+'.'+code
        results.append(Event(symbol,code,int.from_bytes(payload[8:12],'little'),payload[12],
            *struct.unpack('<ffff',payload[13:29]),index,market))
    return results

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True,type=Path);parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    if not args.out.resolve().is_relative_to(Path('G:/codex_tmp').resolve()) or args.out.exists():raise ValueError('NEW_G_LOCAL_ORACLE_OUTPUT_REQUIRED')
    raw=args.source.read_bytes();actual=decode(raw)
    from tdx.gbbq_reader import decode_gbbq_bytes
    reference=decode_gbbq_bytes(raw);failures=[];comparisons=0
    for left,right in zip(actual,reference,strict=True):
        for field in Event._fields:
            a,b=getattr(left,field),getattr(right,field)
            if field in ('c1','c2','c3','c4'):a,b=struct.pack('<f',a),struct.pack('<f',b)
            comparisons+=1
            if a!=b:failures.append(dict(record=left.source_record_index,field=field))
    receipt=dict(contract_id=CONTRACT,acceptance='PASS' if not failures else 'FAIL',source=str(args.source),
        source_sha256=hashlib.sha256(raw).hexdigest(),source_bytes=len(raw),record_denominator=len(actual),
        scalar_comparisons=comparisons,key_schedule_sha256=hashlib.sha256(GBBQ_KEY_BYTES).hexdigest(),
        shared_key_schedule_data=True,independent_implementation=True,external_acceptance=False,
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),failures=failures)
    args.out.parent.mkdir(parents=True,exist_ok=True);temp=args.out.with_suffix('.tmp');temp.write_text(json.dumps(receipt,indent=2),encoding='utf8');temp.replace(args.out)
    print(json.dumps({k:receipt[k] for k in ('acceptance','record_denominator','scalar_comparisons')}))
    return int(bool(failures))

if __name__=='__main__':raise SystemExit(main())
