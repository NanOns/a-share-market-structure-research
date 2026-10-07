"""Load the current engineering boundary without contaminating frozen common."""
import importlib.util
from pathlib import Path
import sys

_name = '_final_disposable_destination_boundary'
if _name not in sys.modules:
    _path = Path(__file__).resolve().parents[1] / 'src/common/disposable_paths.py'
    _spec = importlib.util.spec_from_file_location(_name, _path)
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_name] = _module
    _spec.loader.exec_module(_module)
resolve_destination_inside_root = sys.modules[_name].resolve_destination_inside_root
configured_source_roots = sys.modules[_name].configured_source_roots
