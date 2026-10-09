"""Bounded slice archive, not a complete successor release or source ZIP."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
OUT=ROOT/'docs/evidence/dynamic_daily_20261009'
if __name__=='__main__':
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    changed=subprocess.check_output(['git','diff','--name-only','6f0cf3c5a983eab481283d0436e050d70b77fe29',head],cwd=ROOT,text=True,encoding='utf8').splitlines()
    files=[ROOT/p for p in changed if (ROOT/p).is_file()]
    tdx=json.loads((OUT/'DD02_REAL_TDX_EXTRACTION.json').read_bytes())['extraction']['artifact']
    files.append(Path(tdx['path']))
    payload=[]
    for p in sorted(set(files)):
        p.resolve().relative_to(ROOT.resolve())
        if p.stat().st_size>30_000_000:raise ValueError('SLICE_ARTIFACT_SIZE_BOUND')
        payload.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size))
    manifest=dict(contract_id='DYNAMIC_DAILY_ENGINEERING_SLICE_ARCHIVE_V1',git_sha=head,
        baseline='6f0cf3c5a983eab481283d0436e050d70b77fe29',payload=payload,
        scope='Engineering delta plus actual target bars and dated runtime receipts; complete official 551MB ZIP remains local SHA-bound',
        full_successor_release=False,external_acceptance='NOT_GRANTED')
    archive=Path('E:/codex_tmp/DYNAMIC_DAILY_ENGINEERING_SLICE_20261009.zip');archive.parent.mkdir(parents=True,exist_ok=True)
    temporary=archive.with_suffix('.tmp.zip')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
        for item in payload:z.write(ROOT/item['path'],item['path'])
        z.writestr('SLICE_MANIFEST.json',canonical(manifest))
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
        for item in payload:
            data=z.read(item['path']);assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
    os.replace(temporary,archive)
    atomic(OUT/'SLICE_ARCHIVE_RECEIPT.json',canonical(dict(archive_path=str(archive),bytes=archive.stat().st_size,
        sha256=sha(archive),git_sha=head,payload_count=len(payload),zip_crc='PASS',every_payload_digest='PASS',
        external_acceptance='NOT_GRANTED')))
    print(json.dumps(dict(path=str(archive),bytes=archive.stat().st_size,payload_count=len(payload))))
