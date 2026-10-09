import json,sys,subprocess,zipfile,os,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
OUT=ROOT/'docs/evidence/r43_r2_fp_entry_20261009'

if __name__=='__main__':
    paths=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0')
    paths=[p for p in paths if p and not p.endswith(('DELIVERY_RECEIPT.json','ARCHIVE_PAYLOAD_MANIFEST.json'))]
    manifest=dict(contract_id='R43_FP_ENTRY_ARCHIVE_MANIFEST_V1',entries=[dict(path=p,bytes=(ROOT/p).stat().st_size,sha256=sha(ROOT/p)) for p in paths],
                  protected_heads_changed=False,prior_data_reused='Existing Drive R43 R2 package and frozen owner archive; not re-uploaded or recomputed',
                  receipt_delivery='Separate DELIVERY_RECEIPT.json after actual upload/readback/commit/push')
    atomic(OUT/'ARCHIVE_PAYLOAD_MANIFEST.json',canonical(manifest))
    destination=Path('E:/codex_tmp/R43_R2_FP_ENTRY_CONTROL_REPAIR_20261009.zip');temporary=destination.with_suffix('.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in paths:archive.write(ROOT/path,path)
        archive.write(OUT/'ARCHIVE_PAYLOAD_MANIFEST.json','ARCHIVE_PAYLOAD_MANIFEST.json')
    os.replace(temporary,destination)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for binding in manifest['entries']:assert hashlib.sha256(archive.read(binding['path'])).hexdigest()==binding['sha256']
    print(json.dumps(dict(path=str(destination),bytes=destination.stat().st_size,sha256=sha(destination),entries=len(paths),roundtrip='ALL_PAYLOAD_BYTE_SHA_PASS')))
