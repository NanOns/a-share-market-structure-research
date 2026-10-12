"""Local-only aggregate ZIP; preserve the previous delivery and verify all bytes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('G:/codex_tmp/V4_R4_R3_FINAL_DELIVERY')
DEST = BASE / 'S1B_20261012'
AUDIT = ROOT / 'docs/audits/s1b_20261012'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    result = json.loads((AUDIT / 'RESULT.json').read_bytes())
    assert result['status'] == 'SCOPED_PASS' and result['S1B'] == 'NOT_FULL_PASS'
    assert result['S2'] == 'NOT_ENTERED' and result['source_bytes_stable']
    for name, expected in result['source_sha256'].items():
        assert sha((ROOT / name).read_bytes()) == expected
    assert json.loads((AUDIT / 'EXECUTION_s1b_http_20261012_R4.json').read_bytes())['source_sha256'] == sha((ROOT / 'scripts/run_s1b_identity_http.py').read_bytes())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    old = BASE / 'V4_R4_R3_FINAL_DELIVERY.zip'
    DEST.mkdir(parents=True, exist_ok=False)
    target = DEST / 'V4_R4_R3_S1B_DELIVERY.zip'
    temp = target.with_suffix('.zip.tmp')
    files = []
    names = set()
    with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        def put(name, raw, origin):
            assert name not in names
            names.add(name)
            out.writestr(name, raw)
            files.append(dict(path=name, bytes=len(raw), sha256=sha(raw), origin=origin))
        with zipfile.ZipFile(old) as previous:
            for info in previous.infolist():
                if info.filename == '05_SOURCE_MANIFEST_SHA256.json':
                    continue
                put(info.filename, previous.read(info), 'PREVIOUS_SCOPED_DELIVERY_UNCHANGED')
        for path in sorted(AUDIT.iterdir()):
            if path.is_file():
                put('s1b/evidence/' + path.name, path.read_bytes(), 'S1B_LOCAL_EVIDENCE')
        for name in ('src/focus_tracker/v4_exact_identity_adapter_r4.py',
                     'src/workbench_analysis/r43_focus_replay.py',
                     'src/workbench_analysis/corrected_focus_replay.py',
                     'tests/test_v4_focus_source_identity_r4.py',
                     'scripts/run_s1b_identity_http.py', 'scripts/package_s1b_delivery.py'):
            put('s1b/source/' + name, (ROOT / name).read_bytes(), 'S1B_FINAL_SOURCE')
        put('07_S1B_EXIT_REPORT.md', (AUDIT / 'EXIT_REPORT.md').read_bytes(), 'CURRENT_EXIT_REPORT')
        put('08_S1B_DELIVERY_HEAD.json', json.dumps(dict(git_head=head, branch='codex/s1-b-20261012',
            status='S1B_NOT_FULL_PASS_S2_NOT_ENTERED', previous_zip_sha256=sha(old.read_bytes()),
            current_report='07_S1B_EXIT_REPORT.md', previous_reports='HISTORICAL_SCOPED_EVIDENCE_ONLY',
            manual_upload_folder='https://drive.google.com/drive/folders/1ijwJxkUpl7Vr-PlucOMf59xhxUXKEbbD',
            drive_operations=0, production_changed=False), ensure_ascii=False, indent=2).encode(), 'FINAL_DELIVERY_IDENTITY')
        manifest = dict(contract='S1B_AGGREGATE_DELIVERY_SHA256_V1', git_head=head,
            status='S1B_NOT_FULL_PASS_S2_NOT_ENTERED', exclusions=['05_SOURCE_MANIFEST_SHA256.json'], files=files)
        out.writestr('05_SOURCE_MANIFEST_SHA256.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode())
    with zipfile.ZipFile(temp) as verify:
        assert verify.testzip() is None
        assert len(verify.namelist()) == len(set(verify.namelist())) == len(files) + 1
        for row in files:
            raw = verify.read(row['path'])
            assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    os.replace(temp, target)
    receipt = dict(git_head=head, zip_path=str(target), bytes=target.stat().st_size,
        sha256=sha(target.read_bytes()), verified_files=len(files), manifest_self_exempt_only=True,
        status='S1B_NOT_FULL_PASS_S2_NOT_ENTERED', manual_upload_folder='https://drive.google.com/drive/folders/1ijwJxkUpl7Vr-PlucOMf59xhxUXKEbbD')
    receipt_path = DEST / 'DELIVERY_RECEIPT.json'
    receipt_temp = receipt_path.with_suffix('.json.tmp')
    receipt_temp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
    os.replace(receipt_temp, receipt_path)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
