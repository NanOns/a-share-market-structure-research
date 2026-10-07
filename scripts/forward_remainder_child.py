"""Replay an original historical worker with exact lazy Git inputs in its process."""
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

repository=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(repository))
from tests.remainder_historical_profiles import profile,install
sys.path.remove(str(repository))
commit,module,*arguments=sys.argv[1:]
root,entries=profile(commit)
if Path.cwd().resolve()!=root.resolve():raise ValueError('HISTORICAL_CHILD_ROOT_MISMATCH')
flush=install(SimpleNamespace(setattr=setattr),root,entries)
# The profile loader imports current-repository helpers. Do not let their
# cached package paths resolve a historical worker against today's sources.
for name in list(sys.modules):
    if name=='scripts' or name.startswith('scripts.') or name=='workbench_analysis' or name.startswith('workbench_analysis.'):
        del sys.modules[name]
sys.path[:0]=[str(root/'src'),str(root)]
sys.argv=[module,*arguments]
try:runpy.run_module(module,run_name='__main__')
finally:flush()
