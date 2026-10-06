"""Read-only audit inventory. Output is atomic and confined to this evidence directory."""
from pathlib import Path
import ast
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def put(name, value):
    path = OUT / name
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8', errors='replace').strip()

def walk(value, pointer=''):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
            yield pointer, value
        for k, v in value.items():
            yield from walk(v, pointer + '/' + k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk(v, pointer + '/' + str(i))

files = []
parse_errors = []
for directory in ('src', 'scripts', 'config', 'migrations', 'tests'):
    for path in sorted((ROOT / directory).rglob('*')):
        if not path.is_file() or path.suffix not in ('.py', '.sql', '.json', '.yaml', '.js', '.html'):
            continue
        if '__pycache__' in path.parts:
            continue
        row = dict(path=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size, sha256=digest(path))
        text = path.read_text(encoding='utf-8-sig')
        row['lines'] = len(text.splitlines())
        if path.suffix == '.py':
            try:
                tree = ast.parse(text)
                row['symbols'] = [dict(name=n.name, line=n.lineno, end=n.end_lineno, kind=type(n).__name__)
                                  for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
            except SyntaxError as e:
                parse_errors.append(dict(path=row['path'], error=str(e)))
        elif path.suffix == '.json':
            try:
                v = json.loads(text)
                row['contract_id'] = v.get('contract_id') if isinstance(v, dict) else None
            except ValueError as e:
                parse_errors.append(dict(path=row['path'], error=str(e)))
        files.append(row)
put('source_inventory.json', dict(head=git('rev-parse', 'HEAD'), branch=git('branch', '--show-current'),
    initial_status=git('status', '--porcelain'), files=files, parse_errors=parse_errors,
    scope_note='Inventory and parse only; listed files are not all individually semantically verified.'))

heads = []
for path in sorted((ROOT / 'data/v4').glob('*HEAD*.json')):
    v = json.loads(path.read_bytes())
    heads.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=digest(path), data=v))
put('heads_snapshot.json', heads)

checks = []
roots = [ROOT / 'config/v4_16_runtime_dependencies_v6.json',
         ROOT / 'config/v4_16_runtime_capability_resolution_v2.json',
         ROOT / 'config/v4_16_runtime_activation_authority_v5.json',
         ROOT / 'data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4.json']
roots += list((ROOT / 'data/v4').glob('V4_*ACCEPTED_HEAD*.json'))
for owner in roots:
    if not owner.exists():
        continue
    for pointer, ref in walk(json.loads(owner.read_bytes())):
        target = (ROOT / ref['path']).resolve()
        row = dict(owner=owner.relative_to(ROOT).as_posix(), pointer=pointer, binding=ref)
        if not target.is_relative_to(ROOT):
            row['result'] = 'OUTSIDE_WORKSPACE_NOT_READ'
        elif not target.is_file():
            row['result'] = 'MISSING'
        else:
            row['actual_sha256'] = digest(target)
            row['actual_bytes'] = target.stat().st_size
            expected_bytes = ref.get('bytes', ref.get('byte_count', row['actual_bytes']))
            row['result'] = 'PASS' if ref['sha256'] == row['actual_sha256'] and expected_bytes == row['actual_bytes'] else 'MISMATCH'
        checks.append(row)
put('exact_binding_checks.json', checks)
baseline = ROOT / 'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
put('audit_baseline.json', dict(head=git('rev-parse','HEAD'), design=dict(path=baseline.relative_to(ROOT).as_posix(),
    sha256=digest(baseline), bytes=baseline.stat().st_size), files=len(files), parse_errors=len(parse_errors),
    binding_counts={state:sum(x['result']==state for x in checks) for state in sorted({x['result'] for x in checks})}))
print(json.dumps(json.loads((OUT/'audit_baseline.json').read_text(encoding='utf8')), ensure_ascii=False))
