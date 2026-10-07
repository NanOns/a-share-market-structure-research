"""One pre-I/O destination boundary for engineering copies and materializers."""
import json
import re
from functools import lru_cache
from pathlib import Path, PureWindowsPath

REPOSITORY = Path(__file__).resolve().parents[2]
DISPOSABLE_BASES = (Path('E:/codex_tmp/test_temp'), Path('G:/codex_tmp/test_temp'))


@lru_cache(maxsize=1)
def configured_source_roots():
    text = (REPOSITORY / 'config/paths.yaml').read_text(encoding='utf8')
    roots = [Path(json.loads(v)) for v in re.findall(r'^  root: ("[^"\n]+")\s*$', text, re.M)]
    for file in (REPOSITORY / 'config').glob('dm01_go_forward_runtime_contract_r4*.json'):
        roots.extend(Path(v) for v in json.loads(file.read_bytes())['read_only_tdx_roots'])
    if not roots:
        raise ValueError('CONFIGURED_SOURCE_ROOT_UNAVAILABLE')
    return tuple(sorted(set(p.resolve() for p in roots)))


def resolve_destination_inside_root(root, relative):
    """Reject ambiguous/escaping names before callers create or open anything.

    Resolution follows existing junctions/reparse points. Callers must invoke
    this again immediately before publication if another actor can alter paths.
    """
    name = str(relative)
    win = PureWindowsPath(name)
    if not name or '\x00' in name or win.drive or win.root or '..' in win.parts:
        raise ValueError('DISPOSABLE_DESTINATION_PATH_REJECTED')
    if any(':' in p for p in win.parts):
        raise ValueError('DISPOSABLE_DESTINATION_STREAM_REJECTED')
    base = Path(root).resolve()
    if not any(base.is_relative_to(p.resolve()) for p in DISPOSABLE_BASES):
        raise ValueError('DISPOSABLE_OUTPUT_ROOT_REQUIRED')
    target = base.joinpath(*win.parts).resolve()
    if target == base or not target.is_relative_to(base):
        raise ValueError('DISPOSABLE_DESTINATION_ESCAPE')
    for source in configured_source_roots():
        if base == source or base.is_relative_to(source) or target == source or target.is_relative_to(source):
            raise ValueError('CONFIGURED_SOURCE_DESTINATION_REJECTED')
    return target
