"""Bounded standalone review archive and fresh offline reruns on G only."""
from immediate_r3_common import *
from datetime import datetime
import zipfile,sys
def main():
    out=OUT/'09_CONTINUATION'
    commands=[('UPSTREAM_INDEPENDENT_ORACLE.py','UPSTREAM_ORACLE_INPUT.json'),('FULL_LOO_INDEPENDENT_ORACLE.py','FULL_LOO_ORACLE_INPUT.json.gz'),('PULSE_SOURCE_INDEPENDENT_ORACLE.py','PULSE_SOURCE_ORACLE_INPUT.json'),('AMOUNT_REPRESENTATION_ORACLE.py','P0_AMOUNT_SOURCE_COMPARISON.json')]
    source=OUT/'04_P0_AMOUNT/P0_AMOUNT_SOURCE_COMPARISON.json';items=[binding(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ('REVIEW_MANIFEST.json','OFFLINE_RECEIPT.json','DRIVE_RECEIPT.json')];write(out/'REVIEW_MANIFEST.json',dict(items=items,amount_source=binding(source),result_sha_before_receipt=git('rev-parse','HEAD')))
    markdown(out/'README_OFFLINE.md','# Offline review\n\nPython standard library only. Run each script with input and output arguments:\n\n'+''.join(f'    python {a} {b} {a}.result.json\n' for a,b in commands)+'\nOriginal production source hashes remain in the inputs. Current public-web BSE investigation is deferred by the user and not used in these algorithms. The package is a numerical/input proof, not a production capability grant.\n')
    archive=Path('G:/codex_tmp/V4_R3_CONTINUATION_REVIEW_20261010.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file() and p.name not in ('OFFLINE_RECEIPT.json','DRIVE_RECEIPT.json'):z.write(p,p.relative_to(out))
        z.write(source,source.name)
    assert archive.stat().st_size<10*1024*1024
    root=Path('G:/codex_tmp/test_temp/r3_continuation_'+datetime.now().strftime('%H%M%S'));root.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:z.extractall(root)
    runs=[]
    for script,inp in commands:
        result=subprocess.run([sys.executable,str(root/script),str(root/inp),str(root/(script+'.result.json'))],text=True,capture_output=True)
        assert result.returncode==0,result.stdout+result.stderr
        runs.append(dict(script=script,input_sha256=sha(root/inp),exit_code=result.returncode,stdout=result.stdout.strip()))
    write(out/'OFFLINE_RECEIPT.json',dict(archive=binding(archive),runs=runs,report=binding(out/'CONTINUATION_RESULT.md')))
    print(json.dumps(dict(archive=binding(archive),runs=runs)))
if __name__=='__main__':main()
