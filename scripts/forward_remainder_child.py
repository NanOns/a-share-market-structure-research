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
sys.argv=[module,*arguments]
try:runpy.run_module(module,run_name='__main__')
finally:flush()
