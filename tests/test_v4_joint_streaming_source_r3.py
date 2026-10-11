"""Independent whole-byte oracle and distant tamper/escape negatives."""
import hashlib
from pathlib import Path
import pytest
from workbench_service.joint_release import checked_path
from workbench_service.current_v4_context import SourceInvalid

def test_full_multichunk_binding_and_distant_tamper(tmp_path,monkeypatch):
    raw=bytes(range(256))*12289+bytes(range(255,-1,-1))
    path=tmp_path/'source.bin';path.write_bytes(raw)
    binding={'path':'source.bin','sha256':hashlib.sha256(raw).hexdigest()}
    original=Path.read_bytes
    def bounded(p):
        if p==path:raise AssertionError('LARGE_INPUT_MUST_STREAM')
        return original(p)
    monkeypatch.setattr(Path,'read_bytes',bounded)
    assert checked_path(tmp_path,binding)==path
    with path.open('r+b') as stream:stream.seek(2*1024*1024+11);stream.write(b'X')
    with pytest.raises(SourceInvalid,match='DIGEST_MISMATCH'):checked_path(tmp_path,binding)

def test_source_escape_rejected_before_read(tmp_path):
    with pytest.raises(SourceInvalid,match='OUTSIDE_PROJECT'):
        checked_path(tmp_path,{'path':'../outside.bin','sha256':'0'*64})
