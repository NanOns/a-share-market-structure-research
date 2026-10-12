"""Versioned exact-identity reader for V4-13 beneath accepted descendant stages.

The historical V4-12/13 readers remain unchanged. This reader grants no owner or
production admission; registered archives may relocate bytes, never replace them.
"""
import json
import re
import os
from pathlib import Path
from .v4_13_io import exact, digest
from .historical_stage_governance_r17 import resolve, accepted_static_binding

HEAD = 'data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json'
HEAD_SHA = '98f222ba4d62318ee900a69b8cad7c25359a30bcc7097efe0a55b8ffea09aa65'


class DescendantContracts:
    contract_id = 'V4_13_DESCENDANT_STAGE_ENGINEERING_READER_V1'

    def __init__(self, root):
        self.root=Path(root).resolve(); stage=json.loads((self.root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes())
        self.historical_git_repository=self.root
        repository=os.environ.get('R4_ENGINEERING_HISTORICAL_GIT_ROOT')
        if repository:
            import subprocess
            if os.environ.get('R4_NATIVE_ISOLATION')!='1' or not self.root.is_relative_to(Path('G:/codex_tmp').resolve()):
                raise ValueError('HISTORICAL_GIT_ROOT_REQUIRES_ISOLATED_ENGINEERING')
            repository=Path(repository).resolve()
            if not repository.is_relative_to(Path('G:/codex work').resolve()):
                raise ValueError('HISTORICAL_GIT_ROOT_OUTSIDE_G_WORKSPACE')
            actual=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=repository,text=True).strip()).resolve()
            if actual!=repository:raise ValueError('EXACT_HISTORICAL_GIT_REPOSITORY_REQUIRED')
            self.historical_git_repository=repository
        match=re.fullmatch(r'V4_00_TO_V4_(\d+)_ACCEPTED',stage['accepted_stage_range'])
        if not match or not 13<=int(match[1])<=15:
            raise ValueError('UNAUTHORIZED_V4_13_DESCENDANT_STAGE')
        binding=stage['v4_13_binding']
        if binding['path']!=HEAD or binding['sha256']!=HEAD_SHA:
            raise ValueError('DESCENDANT_V4_13_IDENTITY_CHANGED')
        head=json.loads(exact(self.root,binding))
        if any(head[k] for k in ('production','shadow','focus','global_mandatory_adoption')):
            raise ValueError('V4_13_ENGINEERING_SCOPE_REQUIRED')
        entry=json.loads(exact(self.root,head['formal_entry_contract']))
        if entry['contract_refs']!=head['contract_refs'] or entry['authority_namespace']!=HEAD:
            raise ValueError('V4_13_ENTRY_BINDING_MISMATCH')
        self.refs=head['contract_refs'];self.digest=digest(self.refs)
        if self.digest!=head['contract_digest']:raise ValueError('V4_13_PACKAGE_DIGEST_MISMATCH')
        self.config={Path(r['path']).stem.removeprefix('v4_13_').rsplit('_v',1)[0]:json.loads(exact(self.root,r)) for r in self.refs}
        self.owner_refs=self.config['loo_context']['accepted_owner_bindings'];self.resolutions=[]
        self.owners={k:json.loads(self._historical_exact(r)) for k,r in self.owner_refs.items()}
        self.dependencies={k:json.loads(exact(self.root,r)) for k,r in self.config['loo_context']['accepted_sector_dependencies'].items()}
        for k in ('native_producer','rotation_producer','b2_producer'):self._historical_exact(self.owners['V4_08'][k])
        exact(self.root,self.config['loo_context']['relative_state']['owner'])
        self.authority=head;self.authority_ref=binding

    def _historical_exact(self, binding):
        try:return exact(self.root,binding)
        except ValueError:
            # Only the signed registry's exact original namespace/hash is eligible.
            try:p=resolve(self.root,binding,source=True)
            except ValueError:
                try:p=accepted_static_binding(self.root,binding)
                except ValueError:
                    import subprocess
                    book=json.loads((self.root/'config/v4_corrected_historical_archives_v1.json').read_bytes())
                    row=next((r for r in book['entries'] if r['original']==binding),None)
                    if row is None:raise ValueError('UNREGISTERED_CORRECTED_HISTORICAL_IDENTITY')
                    raw=exact(self.root,row['archive'])
                    from .portable_historical_archives_r1 import PATH,resolve as portable
                    if (self.root/PATH).exists():p=portable(self.root,binding)
                    else:
                        original=subprocess.check_output(['git','show',row['source_commit']+':'+binding['path']],cwd=self.historical_git_repository)
                        if raw!=original:raise ValueError('CORRECTED_ARCHIVE_NOT_EXACT_HISTORICAL_GIT_BYTES')
                        p=self.root/row['archive']['path']
            raw=p.read_bytes()
            import hashlib
            if hashlib.sha256(raw).hexdigest()!=binding['sha256']:
                raise ValueError('REGISTERED_ARCHIVE_IDENTITY_MISMATCH')
            self.resolutions.append(dict(original=binding,archive=str(p.relative_to(self.root))))
            return raw
