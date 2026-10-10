"""Exact representation-path proof only; never a tolerance or source grant."""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import struct,json,sys

def main():
    data=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'));rows=[];counts={}
    f32=lambda x:struct.unpack('<f',struct.pack('<f',float(x)))[0]
    for row in data['rows']:
        a=row['baostock_amount'];native=row['native_amount']
        d=Decimal(a) if a is not None else None;whole=d.quantize(Decimal('1'),rounding=ROUND_HALF_UP) if d is not None else None
        direct=f32(d) if d is not None else None;rounded=f32(whole) if whole is not None else None
        proof='SOURCE_NOT_PRESENT' if d is None else 'EXACT_DECIMAL_EQUAL' if Decimal(str(native))==d else 'DIRECT_BINARY32_EXACT' if direct==native else 'WHOLE_YUAN_HALF_UP_THEN_BINARY32_EXACT' if rounded==native else 'UNEXPLAINED_REPRESENTATION'
        counts[proof]=counts.get(proof,0)+1
        rows.append(dict(code=row['code'],trade_date=row['trade_date'],native_amount=native,baostock_amount=a,whole_yuan_decimal=str(whole) if whole is not None else None,direct_binary32=direct,whole_yuan_binary32=rounded,proof=proof,native_unchanged=True))
    out=dict(contract='AMOUNT_EXACT_REPRESENTATION_PATH_V1',counts=counts,rows=rows,changes_to_native=False,new_tolerance=False,provider_algorithm_proven=False,economic_equivalence_proven=False,formal_sector_amount_authority_changed=False,acceptance='REPRESENTATION_PASS_SCOPED' if not counts.get('UNEXPLAINED_REPRESENTATION') else 'FAIL',limitation='An exactly reproducible arithmetic path is evidence of representation compatibility; it does not assert undocumented provider implementation or economic feed identity')
    dest=Path(sys.argv[2]);tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(dest);print(json.dumps(counts));return bool(counts.get('UNEXPLAINED_REPRESENTATION'))
if __name__=='__main__':sys.exit(main())
