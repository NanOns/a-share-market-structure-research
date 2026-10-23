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


def test_v4_ui_graph_uses_route_allowlists_and_excludes_legacy_static_files(tmp_path, monkeypatch):
    import hashlib
    import json

    service = 'src/workbench_service/v4_server.py'
    control = 'src/workbench_service/v4_control_server_v2.py'
    desktop = 'src/workbench_desktop/engine.py'
    v4_html = 'src/workbench_service/static/research/index.html'
    v4_app = 'src/workbench_service/static/research/app.js'
    v4_style = 'src/workbench_service/static/research/style.css'
    v4_workbench = 'src/workbench_service/static/v4-workbench.html'
    desktop_asset = 'src/workbench_service/static/core-product-r1/desktop_status.js'
    control_asset = 'src/workbench_service/static/r43-control-v2/app.js'
    adapter = 'config/v4_control_adapter_v2.json'
    legacy_page = 'src/workbench_service/static/online-events-v3.html'
    legacy_api = 'src/workbench_service/static/v2/api.js'
    bodies = {
        service: "UI_AUTHORITY = 'config/v4_research_ui_authority_v1.json'\n",
        control: "ADAPTER = 'config/v4_control_adapter_v2.json'\n",
        desktop: 'V4_ASSET_PREFIX = "/v4/assets/"\n',
        v4_html: '<link rel="stylesheet" href="/v4/assets/style.css"><script type="module" src="/v4/assets/app.js"></script>',
        v4_app: "fetch('/api/v4/current/context');\n",
        v4_style: 'body { color: black; }\n',
        v4_workbench: '<script src="/v4/workbench.js"></script>',
        desktop_asset: "fetch('/api/v4/desktop/status');\n",
        control_asset: "fetch('/api/v4/control/context');\n",
        legacy_page: '<script src="online-events-v3.js"></script>',
        legacy_api: "fetch('/api/v2/legacy');\n",
    }
    for rel, body in bodies.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8')
    adapter_path = tmp_path / adapter
    adapter_path.parent.mkdir(parents=True, exist_ok=True)
    adapter_path.write_text(json.dumps({'ui_assets': {'app.js': {
        'path': control_asset,
        'sha256': hashlib.sha256((tmp_path / control_asset).read_bytes()).hexdigest(),
    }}}), encoding='utf-8')
    monkeypatch.setattr(scanner, 'ROOT', tmp_path)
    monkeypatch.setattr(scanner, 'active_entrypoint_inventory',
                        lambda files: ([service, control, desktop], {'status': 'SOURCE_VERIFIED'}))

    reachable, _, _, _ = scanner.runtime_graph([*bodies, adapter])

    assert {v4_html, v4_app, v4_style, v4_workbench, desktop_asset, control_asset} <= reachable
    assert legacy_page not in reachable
    assert legacy_api not in reachable


def test_sha_bound_joint_ui_assets_are_scanned_as_dynamic_v4_dependencies(tmp_path, monkeypatch):
    import hashlib
    import json

    service = 'src/workbench_service/v4_server.py'
    contract = 'config/v4_joint_release_authority_v1.json'
    release = 'data/v4/ui_releases/sha-bound/index.html'
    app = 'data/v4/ui_releases/sha-bound/app.js'
    style = 'data/v4/ui_releases/sha-bound/style.css'
    legacy = 'src/workbench_service/static/research-v3.html'
    bodies = {
        service: "from workbench_service.joint_release import load\n",
        release: '<script type="module" src="/v4/assets/app.js"></script>',
        app: "import './module.js';\nfetch('/api/v4/current/context');\n",
        style: 'body { color: black; }\n',
        'data/v4/ui_releases/sha-bound/module.js': 'export const state = "ready";\n',
        legacy: '<script>fetch("/api/v3/legacy")</script>',
    }
    for rel, body in bodies.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8')
    bindings = {}
    for name, rel in [('index.html', release), ('app.js', app), ('style.css', style)]:
        bindings[name] = {'path': rel, 'sha256': hashlib.sha256((tmp_path / rel).read_bytes()).hexdigest()}
    contract_path = tmp_path / contract
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(json.dumps({'contract_id': 'V4_JOINT_RELEASE_V1', 'ui_assets': bindings}),
                             encoding='utf-8')
    monkeypatch.setattr(scanner, 'ROOT', tmp_path)
    monkeypatch.setattr(scanner, 'active_entrypoint_inventory',
                        lambda files: ([service], {'status': 'SOURCE_VERIFIED'}))

    candidates = [*bodies, contract]
    bound_assets = scanner.configured_ui_asset_targets(
        candidates, contract, scanner.V4_JOINT_UI_NAMES)
    reachable, _, _, _ = scanner.runtime_graph(candidates)

    assert {release, app, style} <= bound_assets
    assert {release, app, style, 'data/v4/ui_releases/sha-bound/module.js'} <= reachable
    assert legacy not in reachable


def test_css_hex_colors_do_not_create_security_identity_findings():
    assert scanner.verified_false_positive(
        'data/v4/ui_releases/current/style.css', 'CONSTANT_SECURITY_ID', '226556',
        ':root{--accent:#226556;color:#718591}') == 'CSS_HEX_COLOR'
    assert scanner.verified_false_positive(
        'data/v4/ui_releases/current/style.css', 'CONSTANT_SECURITY_ID', '226556',
        '.row{content:226556}') is None
