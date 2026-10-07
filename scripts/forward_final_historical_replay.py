"""Execute exact archived assertions separately; unavailable history is no pass."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from scripts.full_chain_repair_io import ROOT, binding, write
from scripts.forward_final_bootstrap import P
from tests.final_disposable_paths import resolve_destination_inside_root


def run():
    if (ROOT / (P + 'V4_SCOPE_CORRECTION_RECEIPT.json')).exists():
        raise ValueError('PRE_V4_HISTORICAL_EXECUTION_OUTSIDE_USER_V4_SCOPE')
    registry = json.loads((ROOT / (P + 'IA05_60_NODE_DEPENDENCY_CLASSIFICATION.json')).read_bytes())
    base = resolve_destination_inside_root(Path('G:/codex_tmp/test_temp'), 'final_historical_' + uuid.uuid4().hex)
    base.mkdir()
    modules = {}; selectors = []; identities = {}
    for row in registry['nodes']:
        path = row['old_test_path']
        if path not in modules:
            archive = ROOT / row['original_archive']['path']; raw = archive.read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row['original_module']['sha256']
            name = 'test_historical_' + str(len(modules)).zfill(3)
            output = resolve_destination_inside_root(base, name + '.py')
            package = path.removesuffix('.py').replace('/', '.').rpartition('.')[0]
            code = ('import base64,pytest\n_historical_wrapper_file=__file__\n__package__=' + repr(package) + '\n_historical_declared_file=' + repr(str(ROOT / path)) + '\n__file__=_historical_declared_file\n'
                    'exec(compile(base64.b64decode(' + repr(base64.b64encode(raw).decode()) + '),' + repr(str(archive)) + ',"exec"),globals())\n'
                    '__file__=_historical_wrapper_file\n'
                    '@pytest.fixture(autouse=True)\ndef _historical_original_file_context(monkeypatch):\n monkeypatch.setitem(globals(),"__file__",_historical_declared_file)\n'
                    '@pytest.fixture(name="tmp_path")\ndef _historical_private_tmp(tmp_path_factory):\n return tmp_path_factory.mktemp("historical_assertion")\n')
            output.write_text(code, encoding='utf8')
            modules[path] = (output, name)
        output, name = modules[path]
        function = row['old_node'].split('::', 1)[1]
        selectors.append(str(output) + '::' + function)
        identities[name + '::' + function] = row
    environment = dict(os.environ, PYTHONPATH=str(ROOT / 'src') + os.pathsep + str(ROOT),
                       REMAINDER_TEST_TEMP_BASE='G:/codex_tmp/test_temp', TEMP=str(base), TMP=str(base))
    xml = resolve_destination_inside_root(base, 'historical.xml')
    command = [sys.executable, '-m', 'pytest', '-p', 'tests.runtime_isolation_plugin', '-p', 'tests.final_historical_plugin',
               '-p', 'tests.final_blocker_plugin', *selectors, '-q', '--confcutdir=' + str(base),
               '--basetemp=' + str(base / 'run'), '--junitxml=' + str(xml)]
    process = subprocess.run(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    write(P + 'historical_profile/execution.log', process.stdout, raw=True)
    if not xml.exists():
        raise ValueError('HISTORICAL_PROFILE_DID_NOT_COMPLETE')
    raw = xml.read_bytes(); write(P + 'historical_profile/execution.xml', raw, raw=True)
    results = []
    cases = ET.fromstring(raw).findall('.//testcase')
    if len(cases) != len(registry['nodes']):
        raise ValueError('HISTORICAL_PROFILE_INCOMPLETE_COLLECTION')
    for index, case in enumerate(cases):
        key = case.attrib['classname'].rsplit('.', 1)[-1] + '::' + case.attrib['name']
        row = identities.get(key, registry['nodes'][index])
        if case.attrib['name'] != row['old_node'].split('::', 1)[1]:
            raise ValueError('HISTORICAL_PROFILE_IDENTITY_ORDER_ERROR:' + key)
        error = case.find('error'); failure = case.find('failure')
        problem = error if error is not None else failure
        if problem is None:
            status = 'ORIGINAL_HISTORICAL_ASSERTION_PASS' if case.find('skipped') is None else 'HISTORICAL_EXECUTION_SKIPPED_NOT_ACCEPTED'
        elif row['classification'] == 'HISTORICAL_ONLY_SUPERSEDED':
            status = 'HISTORICAL_ARTIFACT_UNAVAILABLE_FORMALLY_SUPERSEDED'
        else:
            status = 'ACTIVE_APPROVAL_CHAIN_UNAVAILABLE_BLOCKED'
        results.append(dict(old_node=row['old_node'], classification=row['classification'], status=status,
                            raw_pytest_failed=problem is not None, original_module=row['original_module'],
                            original_archive=row['original_archive'], trace=None if problem is None else problem.text))
    assert len(results) == 60
    write(P + 'HISTORICAL_PROFILE_RECEIPT.json', dict(contract=binding('config/v4_forward_r3_historical_profile_v1.json'),
        command=command, exit_code=process.returncode, original_assertions_executed=60, results=results,
        raw_xml=binding(P+'historical_profile/execution.xml'), raw_log=binding(P+'historical_profile/execution.log'),
        mechanism='Exact archived module bytes compiled in memory; original declared file context, separate disposable fixture outputs',
        original_artifacts_reconstructed=False, missing_history_is_current_pass=False,
        current_approval_permissions=False, ignored=[], deselected=[]))


if __name__ == '__main__':
    run()
