import sys,json,importlib.abc,importlib.util,traceback
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
exe=Path('G:/codex work/v4-production-20261012/versions/V4_PACKAGE_1.0.0_fe11c18cfdf7/DaAV4/DaAV4.exe')
resources=exe.parent/'_internal/resources'
m=json.loads((resources/'package_manifest.json').read_bytes())
roots={r['module'].split('.')[0] for r in m['module_locations']} - {'baostock','run_desktop'}
archive=CArchiveReader(str(exe)).open_embedded_archive('PYZ.pyz')
locations={r['module']:resources/r['path'] for r in m['module_locations']}
class Loader(importlib.abc.Loader):
    def create_module(self,spec):return None
    def exec_module(self,module):
        name=module.__name__;module.__file__=str(locations.get(name,resources/(name.replace('.','/')+'.py')))
        exec(archive.extract(name),module.__dict__)
class Finder(importlib.abc.MetaPathFinder):
    def find_spec(self,name,path=None,target=None):
        if name.split('.')[0] not in roots:return None
        if name not in archive.toc:raise ImportError('UNPACKAGED_LOCAL_MODULE:'+name)
        kind=archive.toc[name][0]
        if kind==3:
            s=importlib.machinery.ModuleSpec(name,None,is_package=True);s.submodule_search_locations=[];return s
        return importlib.util.spec_from_loader(name,Loader(),is_package=kind==1)
sys._MEIPASS=str(exe.parent/'_internal')
sys.path.insert(0,'E:/python/Lib/site-packages/PyInstaller/loader')
import pyimod02_importers
pyimod02_importers.pyz_archive=archive
sys.path_hooks.insert(0,pyimod02_importers.PyiFrozenFinder.path_hook)
sys.path_importer_cache.clear()
sys.path.insert(0,sys._MEIPASS)
exec((resources/'scripts/pyinstaller_workspace_paths_v1.py').read_text(),{'__name__':'frozen_original_hook'})
import os
os.environ['DAAV4_WORKSPACE_ROOT']='G:/codex work/v4-production-20261012'
root=Path('G:/codex_tmp/test_temp/frozen_daily_diagnose_r1');root.mkdir(parents=True,exist_ok=True)
(root/'data/v4').mkdir(parents=True,exist_ok=True)
(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').write_text('{"accepted_trade_date":"2026-10-12"}')
try:
    from workbench_desktop.storage import WorkspaceLease
    from workbench_desktop.source_adapter import executor
    with WorkspaceLease(root):
        result=executor(root)(root,'2026-10-13','CATCH_UP',capture_only=True)
    print(json.dumps(result,default=str))
except Exception:
    print(traceback.format_exc())
