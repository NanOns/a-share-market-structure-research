"""Verify authenticated Drive raw bytes and pinned remote Git source bytes."""
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.record_next_stage_contract_r1 import OUT
from workbench_analysis.v4_14_replay_io import publish, exact, ref


def main():
    for name in ('TMP','TEMP','TMPDIR'):
        os.environ[name]='G:/codex_tmp'
    source_commit='6bd8c50d66c2c0847bca4addc3f646dedde4f7be'
    subprocess.run(['git','fetch','origin'],cwd=ROOT,check=True)
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/v4-fp14-r2-repair'],cwd=ROOT).decode().split()[0]
    assert remote==source_commit
    receipt=json.loads(Path('G:/codex_tmp/next_stage_drive_verified.json').read_bytes())
    with zipfile.ZipFile('G:/codex_tmp/next_stage_drive_readback.zip') as archive:
        manifest=json.loads(archive.read('DELIVERY_MANIFEST.json'))
        assert manifest['source_commit']==source_commit
        for binding in manifest['files']:
            raw=archive.read(binding['path'])
            assert len(raw)==binding['bytes'] and hashlib.sha256(raw).hexdigest()==binding['sha256']
            blob=subprocess.check_output(['git','cat-file','blob',source_commit+':'+binding['path']],cwd=ROOT)
            assert raw==blob, binding['path']
        archive_count=len(manifest['files'])
    index=json.loads((ROOT/OUT/'FINAL_EVIDENCE_INDEX.json').read_bytes())
    for binding in index['evidence']+index['code']:
        exact(ROOT,binding)
    for binding in receipt:
        raw=Path(binding['readback_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==binding['local_sha256']==binding['download_sha256']
        binding['url']='https://drive.google.com/file/d/'+binding['id']+'/view'
    heads=['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']
    current={p:ref(ROOT,p) for p in heads}
    expected=json.loads((ROOT/OUT/'PROTECTED_HEAD_READBACK.json').read_bytes())['before']
    assert current==expected
    publish(ROOT,OUT+'/DELIVERY_READBACK.json',dict(contract_id='NEXT_STAGE_GIT_DRIVE_EXACT_READBACK_R1',
        remote_exact_source_head=remote,source_commit=source_commit,
        archive_files_verified=archive_count,git_blob_bytes_verified=True,
        indexed_evidence_files_verified=len(index['evidence']),indexed_code_verified=len(index['code']),
        drive=receipt,protected_heads=current,protected_heads_unchanged=True,
        formal_acceptance=False,production_restart=False,
        current_source_review='PENDING_REAL_CAPTURE_AND_INDEPENDENT_SOURCE_REVIEW',
        browser_1366_1920='PENDING_BROWSER_SURFACE',
        receipt_commit_note='This receipt is committed after pinned source_commit; source archive intentionally excludes this post-upload receipt.'))
    print(json.dumps(dict(remote_exact_source_head=remote,archive_files_verified=archive_count,
        Drive_raw_byte_SHA_match=True,protected_heads_unchanged=True)))


if __name__=='__main__':
    main()
