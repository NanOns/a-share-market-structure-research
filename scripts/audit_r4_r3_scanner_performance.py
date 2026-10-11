"""Independent frozen scanner comparison; capacity observations, no self admission."""
import hashlib,json,os,subprocess,sys,time,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'docs/audits/r4_r3_integration_20261011'
def main():
    from scripts import scan_no_symbol_specific_runtime_logic as current
    source=subprocess.check_output(['git','show','fbd23a6b:scripts/scan_no_symbol_specific_runtime_logic.py'],cwd=ROOT)
    old=types.ModuleType('frozen_scanner');exec(compile(source,'frozen_scanner','exec'),old.__dict__)
    temporary=Path('G:/codex_tmp/r4_r3_scanner');temporary.mkdir(parents=True,exist_ok=True)
    cases=[('.md','中文\r\nSH.600000\nSEC-0123456789ABCDEF\nSZ.000001'),('.sql',"CASE security_id WHEN '600000' THEN 1 END\r\nstock_code IN ('000001')\nSH.600000"),('.json','{"security_codes":[600000,"000001"],"a":"SH.600000"}'),('.yaml','\n'.join(['中文 SH.600000 SEC-0123456789ABCDEF']*20000)),('.md','SH.600000'),('.md','\nSH.600000\r\nSZ.000001\n')]
    rows=[]
    for i,(suffix,text) in enumerate(cases):
        p=temporary/(str(i)+suffix);p.write_bytes(text.encode());outputs=[];seconds=[]
        for scanner in (old,current):
            begin=time.perf_counter();outputs.append(scanner.scan_file(p,root=temporary,category='EVIDENCE'));seconds.append(time.perf_counter()-begin)
        if outputs[0]!=outputs[1]:raise ValueError('SCANNER_SEMANTIC_DIFF')
        rows.append(dict(case=i,suffix=suffix,bytes=p.stat().st_size,hits=len(outputs[1]['hits']),old_seconds=seconds[0],new_seconds=seconds[1],all_fields_equal=True))
    data=dict(contract_id='V4_R3_SCANNER_COMPLETE_RECORD_ORACLE_R1',source_sha256=hashlib.sha256((ROOT/'scripts/scan_no_symbol_specific_runtime_logic.py').read_bytes()).hexdigest(),frozen_sha256=hashlib.sha256(source).hexdigest(),results=rows,limits=['Synthetic adverse inputs; not a full repository policy admission or approved performance budget'])
    p=OUT/'SCANNER_PERFORMANCE_ORACLE.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');os.replace(tmp,p)
    print(json.dumps(rows))
if __name__=='__main__':main()
