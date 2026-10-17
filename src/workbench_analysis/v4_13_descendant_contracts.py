"""Versioned exact-identity reader for V4-13 beneath accepted descendant stages.

The historical V4-12/13 readers remain unchanged. This reader grants no owner or
production admission; registered archives may relocate bytes, never replace them.
"""
import json
import re
from pathlib import Path
from .v4_13_io import exact, digest

HEAD = 'data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json'
HEAD_SHA = '98f222ba4d62318ee900a69b8cad7c25359a30bcc7097efe0a55b8ffea09aa65'


class DescendantContracts:
    contract_id = 'V4_13_DESCENDANT_STAGE_ENGINEERING_READER_V1'

    def __init__(self, root):
        self.root=Path(root).resolve()
        from workbench_db.v4_historical_source_ingress_pg_r1 import read_path
        stage=read_path(self.root,'data/v4/V4_STAGE_ACCEPTED_HEAD.json')['value']
        self.historical_git_repository=self.root
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
        from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound,read_path
        import hashlib
        try:return exact(self.root,binding)
        except ValueError as error:
            if str(error)!='HISTORICAL_SOURCE_INGRESS_NOT_FOUND':raise

        from .historical_stage_governance_r17 import REGISTRY
        historic=read_path(self.root,REGISTRY)['value']
        rows=[row for key in ('entries','source_archives','static_byte_archives')
              for row in historic.get(key,[])
              if (row.get('original_namespace',{}).get('path'),
                  row.get('original_namespace',{}).get('sha256'))==(binding['path'],binding['sha256'])]
        for row in rows:
            archive=row['archive']
            try:raw=read_bound(self.root,archive['path'],archive['sha256'])['raw']
            except ValueError as error:
                if str(error)=='HISTORICAL_SOURCE_INGRESS_NOT_FOUND':continue
                raise
            if (hashlib.sha256(raw).hexdigest()!=binding['sha256']
                    or len(raw)!=binding.get('bytes',binding.get('byte_count',len(raw)))):
                raise ValueError('REGISTERED_ARCHIVE_IDENTITY_MISMATCH')
            self.resolutions.append(dict(original=binding,archive=archive['path'],source='PG_R17_ARCHIVE_REGISTRY'))
            return raw

        # This source has a separate immutable, authority-free archive witness.
        # Both the registry and witness are PG source facts; the workspace and
        # Git object database are not consulted by this runtime consumer.
        book_ref={'path':'config/v4_corrected_historical_archives_v1.json',
                  'sha256':'1686c398ffadd869704c25e1a1ff9bac9cfadde2aa364c67b6daa15bd3d37b38',
                  'bytes':1854}
        witness_ref={'path':'config/v4_portable_historical_archive_witness_r1.json',
                     'sha256':'5b1efdd62ceacbf6a0aeae9e563e47f2ad0003be961cf8b16229ece38ad7b937',
                     'bytes':2464}
        book=json.loads(exact(self.root,book_ref));witness=json.loads(exact(self.root,witness_ref))
        if (book.get('contract_id')!='V4_CORRECTED_EXACT_HISTORICAL_ARCHIVES_V1'
                or witness.get('contract_id')!='V4_PORTABLE_EXACT_HISTORICAL_ARCHIVE_WITNESS_R1'
                or witness.get('authority_granted') is not False
                or witness.get('production_permission') is not False
                or witness.get('registry_binding')!=book_ref):
            raise ValueError('PORTABLE_ARCHIVE_PG_WITNESS_CONTRACT_INVALID')
        row=next((item for item in book.get('entries',[]) if item.get('original')==binding),None)
        witnessed=next((item for item in witness.get('entries',[]) if item.get('original')==binding),None)
        if row is None or witnessed is None or any(witnessed.get(key)!=row.get(key)
                                                   for key in ('original','archive','source_commit')):
            raise ValueError('UNREGISTERED_CORRECTED_HISTORICAL_IDENTITY')
        archive=row['archive'];raw=exact(self.root,archive)
        if (hashlib.sha256(raw).hexdigest()!=binding['sha256']
                or len(raw)!=binding.get('bytes',binding.get('byte_count'))
                or witnessed.get('verified_git_blob_sha256')!=binding['sha256']):
            raise ValueError('CORRECTED_ARCHIVE_NOT_EXACT_HISTORICAL_BYTES')
        self.resolutions.append(dict(original=binding,archive=archive['path'],source='PG_PORTABLE_ARCHIVE_WITNESS'))
        return raw
