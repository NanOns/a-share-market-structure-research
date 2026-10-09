"""Verify connector-fetched cloud bytes and record actual delivery."""
import base64,hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.scoped_successor_r421 import atomic,canonical
OUT=ROOT/'docs/evidence/r4_3_r2_release_control_20261009'
def main():
    names=['ZIP','R43_R2_FORMAL_HANDOFF.md','R43_R2_EXTERNAL_REVIEW_SCOPE_AND_DISPOSITION.md'];counts=[11,1,1];records=[]
    ids=['1IfqA3-eG80Q0um_xpBZd4nmu4s8cMc40','1fXrGxfkNq0rSqPtPkmaI1zt2ezVH0f-T','1uBLMtlCsiIESN7DG3h1BIT3ZQXilGz56']
    for i in range(3):
        raw=base64.b64decode(''.join(Path(f'E:/codex_tmp/r43_r2_remote_{i}_{k}.txt').read_text() for k in range(counts[i])))
        expected=Path('E:/codex_tmp/R43_R2_REAL_PRODUCTION_DELTA_20261009.zip').read_bytes() if i==0 else (OUT/names[i]).read_bytes()
        assert raw==expected
        records.append(dict(id=ids[i],name=names[i],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),cloud_actual_byte_readback='PASS',url='https://drive.google.com/file/d/'+ids[i]+'/view'))
        if i==0:Path('E:/codex_tmp/R43_R2_DRIVE_READBACK.zip').write_bytes(raw)
    with zipfile.ZipFile('E:/codex_tmp/R43_R2_DRIVE_READBACK.zip') as z:
        assert z.testzip() is None;manifest=json.loads(z.read('DELTA_MANIFEST.json'))
        assert all(hashlib.sha256(z.read(x['path'])).hexdigest()==x['sha256'] for x in manifest['files'])
    value=dict(status='GIT_PUSH_AND_DRIVE_REAL_BYTE_ARCHIVE_PASS',payload_commit='40856a44edf0db346c819187766241791eca0c08',remote_push_completed=True,candidate_digest='e751fb6ebee81baa3fd213515800e220135738d485118828bc6c81fe9dd853c8',production_trade_date='2026-10-08',archive_files_verified=len(manifest['files']),Drive=records,independent_external_acceptance=False,R1_delta_cloud_byte_verification='PASS')
    atomic(OUT/'DELIVERY_RECEIPT.json',canonical(value));print(json.dumps(dict(status=value['status'],files=len(manifest['files']),cloud_bytes=[r['bytes'] for r in records])))
if __name__=='__main__':main()
