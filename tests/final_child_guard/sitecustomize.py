"""Standard-library-only TDX write guard, also valid in historical Python children."""
import atexit
import json
import os
from pathlib import Path
import sys

if os.environ.get('FINAL_SOURCE_GUARD_ROOTS'):
    try:
        roots = tuple(Path(p).resolve() for p in json.loads(os.environ['FINAL_SOURCE_GUARD_ROOTS']))
        logroot = Path(os.environ['FINAL_CHILD_AUDIT_ROOT']).resolve()
        if not logroot.is_relative_to(Path('G:/codex_tmp/test_temp').resolve()):
            raise ValueError('CHILD_GUARD_LOG_ROOT_INVALID')
        logroot.mkdir(parents=True, exist_ok=True)
        events = []

        def record():
            target = logroot / (str(os.getpid()) + '.json')
            temp = target.with_suffix('.tmp')
            temp.write_text(json.dumps(dict(pid=os.getpid(), roots=[str(p) for p in roots],
                guard_installed=True, rejected=events, source_mutations_executed=0)), encoding='utf8')
            os.replace(temp, target)

        def source_guard(event, args):
            targets = []
            if event == 'open':
                mode, flags = args[1] or '', args[2]
                if any(c in mode for c in 'wax+') or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                    targets = args[:1]
            elif event in ('os.remove', 'os.rmdir', 'os.mkdir', 'os.utime', 'os.chmod', 'os.truncate', 'sqlite3.connect'):
                targets = args[:1]
            elif event in ('os.rename', 'os.link', 'os.symlink'):
                targets = args[:2]
            for value in targets:
                if not isinstance(value, (str, bytes, os.PathLike)):
                    continue
                path = Path(os.fsdecode(value)).resolve()
                if any(path == r or path.is_relative_to(r) for r in roots):
                    events.append(dict(event=event, path=str(path), decision='REJECT_BEFORE_OS_SOURCE_MUTATION'))
                    record()
                    raise ValueError('CONFIGURED_SOURCE_WRITE_FORBIDDEN')

        sys.addaudithook(source_guard)
        record()
        atexit.register(record)
    except Exception:
        os._exit(90)
