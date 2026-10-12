"""G-only reproducible onedir build and conservative static dependency inventory."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path('G:/codex_tmp/windows_package_v1')
DELIVERY = Path('G:/codex work/大A交易_交付/windows_package_v1')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    modules = {}
    for base, prefix in ((ROOT/'src', ''), (ROOT/'scripts', 'scripts.')):
        for path in base.rglob('*.py'):
            parts = list(path.relative_to(base).with_suffix('').parts)
            if parts[-1] == '__init__':
                parts.pop()
            name = prefix+'.'.join(parts)
            if name:
                modules[name.rstrip('.')] = path
    modules['run_desktop'] = ROOT/'run_desktop.py'
    pending = ['run_desktop']
    seen, edges, calls, dynamic = set(), [], [], []
    while pending:
        name = pending.pop()
        if name in seen or name not in modules:
            continue
        seen.add(name)
        pieces=name.split('.')
        pending.extend('.'.join(pieces[:i]) for i in range(1,len(pieces)))
        path = modules[name]
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        package = name if path.name == '__init__.py' else name.rpartition('.')[0]
        for node in ast.walk(tree):
            imported = []
            if isinstance(node, ast.Import):
                imported = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parts = package.split('.')
                    head = '.'.join(parts[:len(parts)-node.level+1])
                    base = '.'.join(p for p in (head, node.module) if p)
                else:
                    base = node.module or ''
                imported = [base]+[base+'.'+a.name for a in node.names]
            for target in imported:
                if target in modules:
                    edges.append(dict(caller=name, callee=target, line=node.lineno))
                    pending.append(target)
            if isinstance(node, ast.Call):
                text = ast.unparse(node.func)
                if 'subprocess' in text or text in ('os.system','os.popen'):
                    calls.append(dict(module=name, line=node.lineno, expression=ast.unparse(node)))
                if '__import__' in text or 'import_module' in text:
                    dynamic.append(dict(module=name, line=node.lineno, expression=ast.unparse(node)))
            if isinstance(node, ast.Attribute) and ast.unparse(node) == 'sys.executable':
                calls.append(dict(module=name, line=node.lineno, expression='sys.executable'))
    files = [dict(module=name, path=modules[name].relative_to(ROOT).as_posix(), sha256=sha(modules[name])) for name in sorted(seen)]
    return dict(contract_id='V4_PACKAGE_REACHABILITY_V1', entry='run_desktop', modules=files,
                edges=edges, subprocess_and_executable=calls, dynamic_imports=dynamic,
                caveat='Conservative AST includes conditional/historical branches; dynamic adapter aliases separately reviewed.',
                historical_daily_launcher_reachable='scripts.run_v4_current_daily' in seen)


def prepare():
    for key in ('TMP','TEMP','TMPDIR'):
        os.environ[key] = 'G:/codex_tmp'
    os.environ['PYINSTALLER_CONFIG_DIR'] = str(BUILD/'pyinstaller_cache')
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    BUILD.mkdir(parents=True, exist_ok=True)
    DELIVERY.mkdir(parents=True, exist_ok=True)
    graph = inventory()
    (BUILD/'DEPENDENCY_INVENTORY.json').write_text(json.dumps(graph, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    resources = BUILD/('resources_'+str(time.time_ns()))
    resources.mkdir(exist_ok=True)
    # Existing contracts read immutable Git objects; bundle the local reader.
    git_source = Path(shutil.which('git')).resolve().parents[1]/'mingw64/bin'
    git_target = resources/'git/bin'
    git_target.mkdir(parents=True, exist_ok=True)
    for source in [git_source/'git.exe', *git_source.glob('*.dll')]:
        shutil.copyfile(source, git_target/source.name)
    notices=resources/'third_party_notices'
    notices.mkdir(exist_ok=True)
    shutil.copyfile(git_source.parents[1]/'LICENSE.txt',notices/'Git_LICENSE.txt')
    from importlib.metadata import distribution
    for name in ['pystray','Pillow','numpy','scipy','scikit-learn','baostock','PyInstaller','psutil','pandas']:
        dist=distribution(name)
        for relative in dist.files or []:
            if any(word in relative.name.upper() for word in ('LICENSE','COPYING')) and Path(dist.locate_file(relative)).is_file():
                output=notices/name/Path(str(relative))
                output.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(dist.locate_file(relative),output)
    files = [ROOT/row['path'] for row in graph['modules']]
    module_locations=list(graph['modules'])
    known_modules={row['module'] for row in module_locations}
    policy=json.loads((ROOT/'config/read_only_operational_daily_release_policy_v1_1.json').read_bytes())
    from workbench_desktop.closeout_runtime_sources_r1 import admitted,AUTHORITY
    runtime_repairs=admitted(ROOT)
    if runtime_repairs:files.append(ROOT/AUTHORITY)
    for binding in policy['accepted_algorithm_bindings']:
        source=ROOT/binding['path']
        if sha(source)!=binding['sha256']:
            repair=runtime_repairs.get(binding['path'])
            if not repair or sha(source)!=repair['runtime']['sha256']:raise ValueError('ACCEPTED_ALGORITHM_ORIGINAL_CHANGED:'+binding['path'])
            files.extend(ROOT/repair[key]['path'] for key in ('upstream','runtime'))
        files.append(source)
        if source.suffix=='.py' and source.is_relative_to(ROOT/'src'):
            name='.'.join(source.relative_to(ROOT/'src').with_suffix('').parts)
            if name not in known_modules:
                module_locations.append(dict(module=name,path=binding['path'],sha256=binding['sha256'],
                    inclusion_reason='MANDATORY_CONTRACT_ORIGINAL_NOT_AST_ENTRY_REACHABILITY'))
                known_modules.add(name)
    files += list((ROOT/'src/workbench_service/static').rglob('*'))
    files += list((ROOT/'config').glob('*.json'))
    files += [ROOT/'requirements-windows-package.txt',ROOT/'requirements-fep-e3-r1.txt',ROOT/'requirements-v4-baostock.txt',
              ROOT/'scripts/pyinstaller_workspace_paths_v1.py',ROOT/'scripts/build_windows_package_v1.py']
    entries = []
    # Reachable accepted modules introspect BaoStock callable source for
    # provenance. Keep exact bundled SDK originals as well as frozen code.
    import baostock
    sdk_root=Path(baostock.__file__).resolve().parent
    for source in sorted(sdk_root.rglob('*.py')):
        suffix=source.relative_to(sdk_root)
        relative='third_party_sources/baostock/'+suffix.as_posix()
        target=resources/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        parts=list(suffix.with_suffix('').parts)
        if parts[-1]=='__init__':parts.pop()
        module='.'.join(['baostock']+parts)
        module_locations.append(dict(module=module,path=relative,sha256=sha(source),
            inclusion_reason='SDK_ORIGINAL_SOURCE_INTROSPECTION_NOT_DEVELOPMENT_FALLBACK'))
        entries.append(dict(path=relative,sha256=sha(source),bytes=source.stat().st_size))
    for source in sorted(set(files)):
        if not source.is_file() or '__pycache__' in source.parts:
            continue
        relative = source.relative_to(ROOT).as_posix()
        target = resources/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        entries.append(dict(path=relative, sha256=sha(source), bytes=source.stat().st_size))
    for source in sorted(git_target.iterdir()):
        entries.append(dict(path=source.relative_to(resources).as_posix(), sha256=sha(source), bytes=source.stat().st_size))
    for source in sorted(notices.rglob('*')):
        if source.is_file():entries.append(dict(path=source.relative_to(resources).as_posix(),sha256=sha(source),bytes=source.stat().st_size))
    identity = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    sys.path.insert(0,str(ROOT/'src'))
    from workbench_analysis.rotation_reconstructed_r43 import evaluator
    import inspect
    _,kernel_sha=evaluator()
    introspection=dict(rotation_kernel_sha256=kernel_sha,
        sdk_callable_source_sha256={name:hashlib.sha256(inspect.getsource(getattr(baostock,name)).encode()).hexdigest()
            for name in ('query_stock_industry','query_history_k_data_plus')},
        contract='Unchanged accepted reconstructed Rotation evaluator and exact installed BaoStock callable logical sources')
    manifest = dict(contract_id='V4_WINDOWS_FULL_PACKAGE_MANIFEST_V1', build_release_id='V4_PACKAGE_1.0.0_'+identity[:12],
        source_sha=identity, source_identity_kind='SHA256_EXACT_RESOURCE_LIST', workspace_schema_version=1,
        baseline_git_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        resources=entries,module_locations=module_locations,source_introspection_bindings=introspection,
        built_at=datetime.now(timezone.utc).isoformat(),
        workspace_policy='Existing independently verified G workspace; immutable referenced artifacts retain original bytes.',
        python=sys.version, external_python_required=False, formal_release=False)
    (resources/'package_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return graph, resources


def main():
    graph, resources = prepare()
    manifest=json.loads((resources/'package_manifest.json').read_bytes())
    release_dir=DELIVERY/'versions'/manifest['build_release_id']
    command = [sys.executable, '-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
        '--name','DaAV4','--paths',str(ROOT/'src'),'--paths',str(ROOT),
        '--workpath',str(BUILD/'work'),'--specpath',str(BUILD), '--distpath',str(release_dir),
        '--add-data',str(resources)+';resources', '--collect-all','baostock', '--collect-all','tzdata',
        '--runtime-hook',str(ROOT/'scripts/pyinstaller_workspace_paths_v1.py'),
        '--hidden-import','pystray._win32']
    for module in manifest['module_locations']:
        if module['module'] != 'run_desktop':
            command += ['--hidden-import',module['module']]
    command += [str(ROOT/'run_desktop.py')]
    with (BUILD/'BUILD.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    print(json.dumps(dict(exit_code=result.returncode, delivery=str(release_dir/'DaAV4'), log=str(BUILD/'BUILD.log'))))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
