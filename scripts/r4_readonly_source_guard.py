"""Process-local source write guard. Audit observations contain paths, never data."""
import os,sys
from pathlib import Path

class ReadOnlySourceViolation(BaseException):pass

def install(roots):
    protected=tuple(Path(p).resolve() for p in roots)
    events=[]
    def checked(value,event):
        if not isinstance(value,(str,bytes,os.PathLike)):return
        path=Path(os.fsdecode(value)).resolve()
        if any(path==root or root in path.parents for root in protected):
            events.append(dict(event=event,path=str(path),decision='REJECT'))
            raise ReadOnlySourceViolation('R4_READ_ONLY_SOURCE_WRITE_FORBIDDEN:'+str(path))
    def hook(event,args):
        if event=='open':
            path,mode,flags=args
            if (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):checked(path,event)
        elif event in {'os.remove','os.rmdir','os.mkdir','os.chmod','os.chown','os.utime','os.truncate'}:checked(args[0],event)
        elif event in {'os.rename','os.link','os.symlink'}:
            checked(args[0],event);checked(args[1],event)
    sys.addaudithook(hook)
    return dict(contract_id='R4_PROCESS_SOURCE_WRITE_GUARD_R1',protected_roots=[str(p) for p in protected],events=events,limitation='Current Python process only; does not attest external processes or complete configured TDX root inventory')
