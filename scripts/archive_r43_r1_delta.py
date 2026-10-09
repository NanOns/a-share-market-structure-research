"""Create and independently read back the scoped repair delta archive."""
import hashlib,json,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/r4_3_r1_targeted_repair_20261009'
def main():
    files=set(p for p in OUT.rglob('*') if p.is_file())
    changes=subprocess.check_output(['git','diff','--name-only','52f097f82cb1dfee58b20b1a93e3339b1dc37eac','HEAD'],cwd=ROOT,text=True).splitlines()
    files.update(ROOT/p for p in changes if (ROOT/p).is_file())
    archive=Path('E:/codex_tmp/R43_R1_TARGETED_REPAIR_DELTA_20261009.zip')
    manifest=[]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):
            raw=p.read_bytes();name=p.relative_to(ROOT).as_posix();z.writestr(name,raw)
            manifest.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        z.writestr('DELTA_MANIFEST.json',json.dumps(dict(previous_full_archive_index_drive_id='17myJDYtkmimQKF2UgQEhPmPoltt2cf4A',base_head='52f097f82cb1dfee58b20b1a93e3339b1dc37eac',files=manifest),ensure_ascii=False,indent=2))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for b in manifest:assert hashlib.sha256(z.read(b['path'])).hexdigest()==b['sha256']
    result=dict(path=str(archive),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=len(manifest),restore_readback='PASS',previous_full_archive_index_drive_id='17myJDYtkmimQKF2UgQEhPmPoltt2cf4A')
    print(json.dumps(result))
if __name__=='__main__':main()
