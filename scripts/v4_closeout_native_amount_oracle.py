"""Independent native DAY byte conservation and separate provider differences."""
import hashlib,json,struct,zipfile,argparse,os
from decimal import Decimal
from pathlib import Path

ROOT=Path('G:/codex work/v4-production-20261012')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def bound(root,b):
    p=Path(b['path']);p=p if p.is_absolute() else root/p
    raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=b['sha256']:raise ValueError('SOURCE_DIGEST_MISMATCH')
    return p,raw

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label.isalnum():raise ValueError('VERSIONED_LABEL_REQUIRED')
    out=OUT/('NATIVE_AMOUNT_ORACLE_'+args.label+'.json')
    if out.exists():raise ValueError('PRESERVE_PRIOR_ORACLE')
    diagnosis=json.loads((OUT/'formal_capture_diagnosis_20261013.json').read_bytes())
    freeze_path,raw=bound(ROOT,diagnosis['execution']['source_freeze']);freeze=json.loads(raw)
    _,raw=bound(ROOT,freeze['tdx']);tdx=json.loads(raw)
    package,_=bound(ROOT,freeze['effective_package']['download'])
    target=int(freeze['target_session'].replace('-',''));errors=[];comparisons=0
    native={}
    with zipfile.ZipFile(package) as z:
        for row in tdx['target_bars']:
            blob=z.read(row['source_entry'])
            if hashlib.sha256(blob).hexdigest()!=row['entry_sha256']:raise ValueError('DAY_ENTRY_DIGEST_MISMATCH')
            if len(blob)%32:raise ValueError('DAY_RECORD_LENGTH_INVALID')
            records=[(offset,struct.unpack_from('<IIIIIfII',blob,offset)) for offset in range(0,len(blob),32) if struct.unpack_from('<I',blob,offset)[0]==target]
            if len(records)!=1:raise ValueError('TARGET_DAY_RECORD_NOT_UNIQUE')
            offset,record=records[0]
            expected={**{k:Decimal(record[i])/100 for i,k in enumerate(('open','high','low','close'),1)},'amount':Decimal.from_float(record[5]),'volume':Decimal(record[6])}
            for key,value in expected.items():
                actual=Decimal.from_float(row[key]) if key=='amount' else Decimal(str(row[key]))
                comparisons+=1
                if actual!=value:errors.append(dict(security=row['source_security_key'],field=key,expected=str(value),actual=str(actual)))
            native[row['source_security_key']]=dict(amount=expected['amount'],amount_bytes=blob[offset+20:offset+24].hex())
    # Provider parity is a separate audit; no epsilon merges distinct amounts.
    daily=freeze['sources']['baostock']['daily']['rows'] if 'sources' in freeze else None
    if daily is None:
        def find(x):
            if isinstance(x,dict):
                if isinstance(x.get('rows'),list) and x['rows'] and 'amount' in x['rows'][0] and 'code' in x['rows'][0]:return x['rows']
                for v in x.values():
                    r=find(v)
                    if r is not None:return r
            return None
        daily=find(freeze)
    if daily is None:raise ValueError('REAL_BAOSTOCK_ROWS_REQUIRED')
    counts=dict(exact_decimal_equal=0,same_float32_quantization=0,different_float32=0,no_native_target_bar=0);differences=[]
    for row in daily:
        key=row['code'].upper();n=native.get(key)
        if n is None:counts['no_native_target_bar']+=1;continue
        amount=Decimal(row['amount'])
        if amount==n['amount']:counts['exact_decimal_equal']+=1
        elif struct.pack('<f',float(amount)).hex()==n['amount_bytes']:counts['same_float32_quantization']+=1
        else:
            counts['different_float32']+=1;differences.append(dict(security=key,native_amount=str(n['amount']),native_float32_bytes=n['amount_bytes'],baostock_amount=str(amount)))
    result=dict(contract_id='V4_INDEPENDENT_NATIVE_AMOUNT_BYTE_ORACLE_R1',acceptance='PASS' if not errors else 'FAIL',scope='NATIVE_SOURCE_BYTE_CONSERVATION_ONLY',target=freeze['target_session'],freeze=diagnosis['execution']['source_freeze'],package_sha256=freeze['effective_package']['download']['sha256'],native_rows=len(native),scalar_comparisons=comparisons,errors=errors,provider_parity=dict(acceptance='FAIL' if differences else 'PASS',counts=counts,differences=differences,independent_audit='M10_AMOUNT_A',tolerance_used=False),AS_RECORDED=freeze['AS_RECORDED'],PIT_ELIGIBLE=freeze['PIT_ELIGIBLE'],publication=False)
    temp=out.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2),encoding='utf8');os.replace(temp,out)
    print(json.dumps({k:result[k] for k in ('acceptance','native_rows','scalar_comparisons')}));print(json.dumps(counts))

if __name__=='__main__':main()
