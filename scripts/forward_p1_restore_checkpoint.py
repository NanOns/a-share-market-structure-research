"""Undo the detected storage-only drift, retaining both byte versions and proof.

Requires exact original/changed hashes and exhaustive logical/catalog equality.
This is an incident correction, never evidence that the failed run made no write.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from scripts.full_chain_repair_io import ROOT,write,binding
from scripts.forward_p1_fingerprint import PREFIX

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while block:=stream.read(8*1024*1024):h.update(block)
    return h.hexdigest()

def restore():
    load=lambda name:json.loads((ROOT/(PREFIX+name)).read_bytes())
    comparison=load('PROTECTED_DB_DRIFT_LOGICAL_COMPARISON.json')
    catalogs=load('PROTECTED_DB_DRIFT_CATALOG_COMPARISON.json')
    assert comparison['logical_rows_equal'] and comparison['all_base_tables_compared']==103
    assert all(c['equal'] for c in catalogs)
    before=next(f for f in load('IA09_PROTECTED_ROOT_FINGERPRINT_BEFORE.json')['files'] if f['path']=='data/database/market_research.duckdb')
    changed=next(f for f in load('IA09_PROTECTED_ROOT_FINGERPRINT_AFTER.json')['files'] if f['path']==before['path'])
    source=Path(load('INITIAL_DB_SNAPSHOT_BINDING.json')['path'])
    target=(ROOT/before['path']).resolve()
    assert target.is_relative_to(ROOT) and not target.is_symlink() and sha(source)==before['sha256']
    for name in ('IA09_PROTECTED_ROOT_FINGERPRINT_AFTER.json','IA09_ALL_RUNTIME_ROOTS_AFTER_FINAL_REGRESSION.json',
                 'AFFECTED_TEST_RECEIPT.json','AFFECTED_PYTEST.log'):
        write(PREFIX+'FAILED_PRE_GLOBAL_GUARD_'+name,(ROOT/(PREFIX+name)).read_bytes(),raw=True)
    directory=Path('E:/codex_tmp/test_temp')/('forward_p1_storage_incident_'+str(time.time_ns()))
    directory.mkdir()
    backup=directory/'changed_database.duckdb'
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    # Deny writers while preserving read/delete sharing for atomic replacement.
    handle=kernel.CreateFileW(str(target),0x80000000,5,None,3,0x80,None)
    if handle==ctypes.c_void_p(-1).value:raise OSError(ctypes.get_last_error(),'Cannot lock protected DB against writers')
    temporary=target.with_name('.forward_p1_verified_restore.tmp')
    try:
        assert sha(target)==changed['sha256'],'LIVE_DATABASE_CHANGED_SINCE_LOGICAL_COMPARISON'
        shutil.copyfile(target,backup)
        assert sha(backup)==changed['sha256']
        with source.open('rb') as src,temporary.open('wb') as dst:
            shutil.copyfileobj(src,dst,8*1024*1024);dst.flush();os.fsync(dst.fileno())
        assert sha(temporary)==before['sha256']
        os.utime(temporary,ns=(target.stat().st_atime_ns,before['mtime_ns']))
        # Windows MoveFileEx can deny replacing a destination with an open
        # reader even with delete sharing. Revalidate after releasing it.
        kernel.CloseHandle(handle);handle=None
        assert sha(target)==changed['sha256'],'LIVE_DATABASE_CHANGED_BEFORE_ATOMIC_RENAME'
        os.replace(temporary,target)
        assert sha(target)==before['sha256'] and target.stat().st_mtime_ns==before['mtime_ns']
    finally:
        if handle is not None:kernel.CloseHandle(handle)
    write(PREFIX+'PROTECTED_DB_STORAGE_INCIDENT_AND_RESTORATION.json',dict(
        status='STORAGE_BYTE_DRIFT_DETECTED_AND_CORRECTED; FAILED_RUN_RETAINED',
        failed_run_zero_write_claim=False,original=before,changed=changed,
        original_snapshot=dict(path=str(source),sha256=sha(source)),
        changed_snapshot=dict(path=str(backup),sha256=sha(backup)),
        logical_comparison=binding(PREFIX+'PROTECTED_DB_DRIFT_LOGICAL_COMPARISON.json'),
        catalog_comparison=binding(PREFIX+'PROTECTED_DB_DRIFT_CATALOG_COMPARISON.json'),
        logical_data_loss=False,all_base_table_rows_and_catalog_definitions_equal=True,
        writer_lock='WIN32_DENY_WRITE_DURING_SNAPSHOT_AND_COPY; RELEASE_AND_REVALIDATE_FOR_ATOMIC_RENAME',atomic_restore=True,
        restored_sha256=sha(target),restored_mtime_ns=target.stat().st_mtime_ns,
        next='GLOBAL_TEST_CONNECTION_GUARD_AND_FRESH_ACCEPTANCE_REGRESSION_REQUIRED'))

if __name__=='__main__':
    import sys
    if sys.argv[1:]!=['--restore-verified-checkpoint-drift']:raise ValueError('EXPLICIT_INCIDENT_RESTORE_MODE_REQUIRED')
    restore()
