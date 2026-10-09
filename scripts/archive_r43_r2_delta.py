"""Archive actual R2 production closure, referencing existing owner backups."""
import hashlib,json,subprocess,zipfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.scoped_successor_r421 import atomic,canonical
OUT=ROOT/'docs/evidence/r4_3_r2_release_control_20261009'
def main():
    paths={p for p in OUT.rglob('*') if p.is_file()}
    changed=subprocess.check_output(['git','diff','--name-only','4e344156564338cda185fd44505c1273cf8bfdca','HEAD'],cwd=ROOT,text=True).splitlines()
    paths.update(ROOT/p for p in changed if (ROOT/p).is_file());paths.add(Path(__file__).resolve())
    dest=Path('E:/codex_tmp/R43_R2_REAL_PRODUCTION_DELTA_20261009.zip');manifest=[]
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):
            raw=p.read_bytes();name=p.relative_to(ROOT).as_posix();manifest.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()));z.writestr(name,raw)
        z.writestr('DELTA_MANIFEST.json',canonical(dict(files=manifest,previous_full_archive_index_drive_id='17myJDYtkmimQKF2UgQEhPmPoltt2cf4A',R1_delta_drive_id='1WQeOcdute9TMYLkhUhQX1r0wg_dT2Tm5',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())))
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None
        for b in manifest:assert hashlib.sha256(z.read(b['path'])).hexdigest()==b['sha256']
    receipt=dict(path=str(dest),bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),files=len(manifest),restore_readback='PASS')
    atomic(OUT/'LOCAL_DELTA_ARCHIVE_RECEIPT.json',canonical(receipt));print(json.dumps(receipt))
if __name__=='__main__':main()
