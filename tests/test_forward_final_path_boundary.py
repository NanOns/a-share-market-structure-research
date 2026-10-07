"""R3 pre-I/O boundary matrix including real Windows junctions and children."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from common.disposable_paths import resolve_destination_inside_root


@pytest.mark.parametrize('name', [
    'D:/new_tdx/vipdoc/sz/lday/x.day',
    r'D:\new_tdx\vipdoc\sz\lday\x.day',
    r'\\server\share\x.day', '../escape.json',
    'D://new_tdx///vipdoc/x.day', 'D:new_tdx/x.day',
    '/new_tdx/x.day', 'safe/../../escape', 'safe/file:stream',
])
def test_reject_before_any_output(name, tmp_path):
    before = list(tmp_path.rglob('*'))
    with pytest.raises(ValueError):
        resolve_destination_inside_root(tmp_path, name)
    assert list(tmp_path.rglob('*')) == before


def test_normal_relative_destination_only(tmp_path):
    path = resolve_destination_inside_root(tmp_path, 'safe/result.json')
    path.parent.mkdir()
    path.write_bytes(b'disposable')
    assert path.read_bytes() == b'disposable'
    assert path.is_relative_to(tmp_path.resolve())


def test_real_windows_junction_escape_and_child(tmp_path):
    root = tmp_path / 'output'
    outside = tmp_path / 'outside'
    root.mkdir(); outside.mkdir()
    link = root / 'escape'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)],
                            capture_output=True, text=True)
    if result.returncode:
        # No platform skip: prove the resolver's actual resolved-path
        # counterexample in a fresh child if reparse creation is unavailable.
        code = "from pathlib import Path;from unittest.mock import patch;from common.disposable_paths import resolve_destination_inside_root;import sys;root=Path(sys.argv[1]);old=Path.resolve\ndef resolve(p,*a,**k):\n return Path(sys.argv[2]) if p.name=='escape' else old(p,*a,**k)\nwith patch.object(Path,'resolve',resolve):\n try:resolve_destination_inside_root(root,'escape')\n except ValueError:print('REJECT')\n else:raise AssertionError('ESCAPE_ACCEPTED')"
    else:
        with pytest.raises(ValueError, match='ESCAPE'):
            resolve_destination_inside_root(root, 'escape/forbidden.json')
        code = "from common.disposable_paths import resolve_destination_inside_root;import sys\ntry:resolve_destination_inside_root(sys.argv[1],'escape/forbidden.json')\nexcept ValueError:print('REJECT')\nelse:raise AssertionError('ESCAPE_ACCEPTED')"
    child = subprocess.run([sys.executable, '-c', code, str(root), str(outside)],
                           capture_output=True, text=True, check=True)
    assert child.stdout.strip() == 'REJECT'
    assert not (outside / 'forbidden.json').exists()


def test_child_guard_rejects_source_mutation_before_os_call():
    code = "from pathlib import Path\ntry:Path('D:/new_tdx/FINAL_GUARD_MUST_NOT_EXIST').write_bytes(b'forbidden')\nexcept ValueError as e:assert 'SOURCE_WRITE_FORBIDDEN' in str(e);print('REJECT')\nelse:raise AssertionError('SOURCE_WRITE_EXECUTED')"
    child = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True)
    assert child.stdout.strip() == 'REJECT'
    assert not Path('D:/new_tdx/FINAL_GUARD_MUST_NOT_EXIST').exists()
