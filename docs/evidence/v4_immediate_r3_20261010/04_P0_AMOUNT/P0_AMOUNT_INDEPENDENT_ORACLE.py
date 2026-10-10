"""Offline IEEE754 binary32 source-representation comparison; no business imports.
Never changes the amount authority, tolerance or stored observations.
"""
from pathlib import Path
import json,struct,sys
def main():
    here=Path(__file__).parent;p=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else here/'P0_AMOUNT_SOURCE_COMPARISON.json').read_text(encoding='utf8'));counts={};rows=[]
    for r in p['rows']:
        native=r['native_amount'];bao=r['baostock_amount'];rounded=struct.unpack('<f',struct.pack('<f',float(bao)))[0] if bao is not None else None
        verdict='SOURCE_NOT_PRESENT' if bao is None else 'EXACT_EQUAL' if native==float(bao) else 'UNIT_OR_PRECISION' if native==rounded else 'INSUFFICIENT_EVIDENCE'
        counts[verdict]=counts.get(verdict,0)+1;rows.append(dict(**r,binary32_of_baostock=rounded,classification=verdict,delta=None if bao is None else native-float(bao),same_volume=None if r.get('baostock_volume') is None else r['native_volume']==int(r['baostock_volume'])))
    out=dict(contract='R3_AMOUNT_BINARY32_ORACLE_V1',counts=counts,compared=sum(r['baostock_amount'] is not None for r in rows),different=sum(r['baostock_amount'] is not None and r['native_amount']!=float(r['baostock_amount']) for r in rows),rows=rows,authority_changed=False,conclusion='Exact binary32 representation is demonstrated per row; economic-source equivalence/sector Amount A remain independently gated',exit_code=0)
    dest=Path(sys.argv[2] if len(sys.argv)>2 else here/'P0_AMOUNT_ORACLE_RESULT.json');tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8');tmp.replace(dest);print(json.dumps({k:out[k] for k in ('counts','compared','different')}));return 0
if __name__=='__main__':sys.exit(main())
