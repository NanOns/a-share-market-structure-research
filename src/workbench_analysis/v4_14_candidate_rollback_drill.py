"""Sandbox-only exact-parent CAS using the accepted atomic/archive IO."""
import os,json
from pathlib import Path
from contextlib import contextmanager
from .v4_13_io import atomic,exact,file_ref,canonical
PREFIX='reports/r18r1r1r1a/sandbox/'

class Sandbox:
    def __init__(self,root,path,parent,candidate,evidence):
        self.root=Path(root).resolve();self.path=path
        if not path.startswith(PREFIX) or '..' in Path(path).parts or not (self.root/path).resolve().is_relative_to(self.root/PREFIX):raise ValueError('SANDBOX_PATH_ESCAPE')
        self.parent=parent;self.candidate=candidate;self.evidence=evidence;self.head=path+'/head.json';self.archive=path+'/parent_archive.json'
        raw=exact(self.root,parent);atomic(self.root,self.archive,raw,append_only=True);atomic(self.root,self.head,raw,append_only=True)
        self.activation=dict(status='SANDBOX_CANDIDATE_UNACCEPTED',previous_accepted_head=parent,candidate_seal=candidate,production=False,shadow=False,focus=False,V4_15=False,ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT')
    @contextmanager
    def locked(self):
        lock=self.root/self.path/'cas.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        try:yield
        finally:os.close(fd);lock.unlink()
    def verify_evidence(self):
        for r in [self.candidate,*self.evidence]:exact(self.root,r)
    def activate(self,expected=None,candidate=None,fail_before=False):
        with self.locked():
            self.verify_evidence();exact(self.root,candidate or self.candidate)
            raw=exact(self.root,self.parent);observed=file_ref(self.root,self.head);expected=expected or self.parent
            if observed['sha256']!=expected['sha256'] or observed['bytes']!=expected['bytes'] or (self.root/self.head).read_bytes()!=raw:raise ValueError('STALE_PREDECESSOR_CAS')
            if fail_before:raise ValueError('INJECTED_FAILURE_BEFORE_ACTIVATION')
            archive=file_ref(self.root,self.archive)
            if exact(self.root,archive)!=raw:raise ValueError('PARENT_ARCHIVE_MISMATCH')
            atomic(self.root,self.head,canonical(self.activation)+b'\n')
            return file_ref(self.root,self.head)
    def rollback(self,parent_archive=None):
        with self.locked():
            self.verify_evidence();raw=exact(self.root,self.parent);archive=parent_archive or dict(self.parent,path=self.archive)
            if exact(self.root,archive)!=raw:raise ValueError('ROLLBACK_NON_PARENT_BYTES')
            current=(self.root/self.head).read_bytes()
            if current==raw:return dict(status='IDEMPOTENT',head=file_ref(self.root,self.head))
            if current!=canonical(self.activation)+b'\n':raise ValueError('ROLLBACK_CURRENT_HEAD_CAS_MISMATCH')
            atomic(self.root,self.head,raw)
            return dict(status='RESTORED',head=file_ref(self.root,self.head))
    def snapshot(self,label):
        path=self.path+'/'+label+'.json';atomic(self.root,path,(self.root/self.head).read_bytes(),append_only=True);return file_ref(self.root,path)
