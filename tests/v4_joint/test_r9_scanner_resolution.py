"""V4 scanner must distinguish literal stdlib imports from unresolved loading."""
from scripts import check_v4_business_literals as scanner


def test_literal_stdlib_imports_resolve_without_waiving_unknown_dynamic_imports(tmp_path, monkeypatch):
    path = 'src/workbench_analysis/probe.py'
    body = """import importlib
__import__('json')
__import__('importlib.metadata')
importlib.import_module('json.tool')
importlib.import_module('pytest')
__import__('not_a_real_stdlib_module')
target = choose_module()
importlib.import_module(target)
"""
    file = tmp_path / path
    file.parent.mkdir(parents=True)
    file.write_text(body, encoding='utf-8')
    monkeypatch.setattr(scanner, 'ROOT', tmp_path)
    monkeypatch.setattr(scanner, 'active_entrypoint_inventory',
                        lambda files: ([path], {'status': 'SOURCE_VERIFIED'}))

    _, summary = scanner.scan([path])
    rows = summary['dynamic_edges']
    resolved = {(row['function'], row['target']) for row in rows
                if row['status'] == 'LITERAL_STDLIB_IMPORT_RESOLVED'}
    unresolved = {(row['function'], row['target']) for row in rows
                   if row['status'] == 'UNRESOLVED'}

    assert ('__import__', 'json') in resolved
    assert ('__import__', 'importlib.metadata') in resolved
    assert ('importlib.import_module', 'json.tool') in resolved
    assert ('importlib.import_module', 'pytest') in unresolved
    assert ('__import__', 'not_a_real_stdlib_module') in unresolved
    assert ('importlib.import_module', None) in unresolved


def test_finite_literal_import_allowlist_adds_all_dependency_edges(tmp_path, monkeypatch):
    entry = 'src/workbench_analysis/entry.py'
    left = 'src/workbench_analysis/validator_left.py'
    right = 'src/workbench_analysis/validator_right.py'
    bodies = {
        entry: """import importlib
def load_validators():
    names = ('workbench_analysis.validator_left', 'workbench_analysis.validator_right')
    return {name: importlib.import_module(name) for name in names}
""",
        left: 'VALUE = 1\n',
        right: 'VALUE = 2\n',
    }
    for rel, body in bodies.items():
        file = tmp_path / rel
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(body, encoding='utf-8')
    monkeypatch.setattr(scanner, 'ROOT', tmp_path)
    monkeypatch.setattr(scanner, 'active_entrypoint_inventory',
                        lambda files: ([entry], {'status': 'SOURCE_VERIFIED'}))

    reachable, _, _, _ = scanner.runtime_graph(list(bodies))
    _, summary = scanner.scan(list(bodies))
    edge = next(row for row in summary['dynamic_edges'] if row['file'] == entry)

    assert {entry, left, right} <= reachable
    assert edge['targets'] == ['workbench_analysis.validator_left', 'workbench_analysis.validator_right']
    assert edge['status'] == 'FINITE_ALLOWLIST_IMPORTS_RESOLVED'
