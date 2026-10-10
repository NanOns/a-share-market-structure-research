"""Map frozen module identities to their original source-layout resource paths."""
import importlib.abc
import importlib.machinery
import json
import hashlib
import linecache
import os
from pathlib import Path
import sys

root=Path(sys._MEIPASS)/'resources'
manifest=json.loads((root/'package_manifest.json').read_bytes())
locations={row['module']:str(root/row['path']) for row in manifest['module_locations']}
entries={row['path']:row['sha256'] for row in manifest['resources']}
relative={row['module']:row['path'] for row in manifest['module_locations']}
local_roots={name.split('.')[0] for name in relative}
os.environ.pop('DAAV4_WORKSPACE_ROOT',None)


class OriginalLayoutFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] not in local_roots:
            return None
        # Historical scripts prepend workspace/src to sys.path. Always choose
        # the PYZ loader; workspace originals are identities, never code fallback.
        frozen_parent=Path(sys._MEIPASS).joinpath(*fullname.split('.')[:-1])
        spec=importlib.machinery.PathFinder.find_spec(fullname,[str(frozen_parent)],target)
        if spec is None:
            raise ImportError('UNPACKAGED_LOCAL_MODULE:'+fullname)
        if fullname not in locations:
            return spec
        if spec is not None:
            # Python 3.13 inspect follows code.co_filename, which remains the
            # PYZ's relative compile path even when provenance __file__ changes.
            # Supply ONLY manifest-bound package originals; execute via PYZ.
            code=spec.loader.get_code(fullname)
            source=root/relative[fullname]
            raw=source.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=entries[relative[fullname]]:
                raise ImportError('SOURCE_INTROSPECTION_IDENTITY_MISMATCH:'+fullname)
            # Match tokenize.open()/linecache universal newline behavior,
            # preserving the original evaluator's logical source/kernel SHA.
            text=raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
            lines=text.splitlines(keepends=True)
            linecache.cache[code.co_filename]=(len(raw),None,lines,str(source))
            # PyInstaller's later inspect runtime hook normalizes a relative
            # compile name to _MEIPASS/<name>; supply that exact key too.
            frozen_filename=os.path.normpath(os.path.join(sys._MEIPASS,code.co_filename))
            linecache.cache[frozen_filename]=(len(raw),None,lines,str(source))
            origin=locations[fullname]
            workspace=os.environ.get('DAAV4_WORKSPACE_ROOT')
            if workspace and not fullname.startswith('workbench_desktop'):
                candidate=Path(workspace)/relative[fullname]
                if candidate.is_file() and hashlib.sha256(candidate.read_bytes()).hexdigest()==entries[relative[fullname]]:
                    origin=str(candidate)
            spec.origin=origin
            spec.has_location=True
            linecache.cache[origin]=(len(raw),None,lines,str(source))
        return spec


sys.meta_path.insert(0,OriginalLayoutFinder())
