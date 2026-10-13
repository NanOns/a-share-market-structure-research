"""Script sibling import closure must be frozen, without source-path fallback."""
import scripts.build_windows_package_v1 as build

def test_script_alias_closes_transitive_source_import(tmp_path,monkeypatch):
    (tmp_path/'scripts').mkdir();(tmp_path/'src').mkdir()
    (tmp_path/'src/security').mkdir()
    (tmp_path/'src/security/__init__.py').write_text('')
    (tmp_path/'src/security/identity.py').write_text('VALUE=1\n')
    (tmp_path/'run_desktop.py').write_text('from scripts.capture import run\n')
    (tmp_path/'scripts/capture.py').write_text('from helper import board_for\ndef run(): return board_for()\n')
    (tmp_path/'scripts/helper.py').write_text('from security.identity import VALUE\ndef board_for(): return VALUE\n')
    monkeypatch.setattr(build,'ROOT',tmp_path)
    result=build.inventory();modules={r['module']:r['path'] for r in result['modules']}
    assert modules['helper']=='scripts/helper.py'
    assert modules['security.identity']=='src/security/identity.py'
    assert any(e['caller']=='scripts.capture' and e['callee']=='helper' for e in result['edges'])

def test_namespaced_script_import_still_retains_original_name(tmp_path,monkeypatch):
    (tmp_path/'scripts').mkdir();(tmp_path/'src').mkdir()
    (tmp_path/'run_desktop.py').write_text('from scripts.helper import value\n')
    (tmp_path/'scripts/helper.py').write_text('value=1\n')
    monkeypatch.setattr(build,'ROOT',tmp_path)
    result=build.inventory()
    assert any(r['module']=='scripts.helper' and r['path']=='scripts/helper.py' for r in result['modules'])
