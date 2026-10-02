"""Versioned Breakout extension to unchanged V2 anchor-state schema."""
import gzip,json
from .v4_12_structure_io import exact_json,file_ref,digest
from .v4_12_frozen_snapshot import exact_bytes
from .v4_12_input_binder import InputBinder,check_availability
from .v4_12_multi_anchor_state import validate_state_set
from .v4_12_breakout_episode import episode_contract,validate_episodes

PATH='config/v4_12_frozen_snapshot_contract_v2.json'
def load_contract(c):
    ref=file_ref(c.root,PATH);gate=json.loads((c.root/'reports/v4_12_runtime_r12/R12A_CONTRACT_LOCAL_GATE.json').read_bytes())
    if gate['status']!='PASS' or gate['contract']['sha256']!=ref['sha256']:raise ValueError('R12A_CONTRACT_GATE_REQUIRED')
    contract=exact_json(c.root,ref)
    if contract['selector']['active_anchor_sort']!=c.config['output_schema']['active_anchor_sort']:raise ValueError('SELECTOR_CONTRACT_MISMATCH')
    return contract,ref

class EpisodeSnapshotLoader:
    def __init__(self,c,ref,cutoff):
        self.c=c;self.ref=ref;self.contract,self.contract_ref=load_contract(c);m=exact_json(c.root,ref);self.m=m
        self.episode_contract,self.episode_ref=episode_contract(c)
        if m['episode_contract']!=self.episode_ref:raise ValueError('EPISODE_CONTRACT_MISMATCH')
        if m['contract_id']!='V4_12_FROZEN_D1_BREAKOUT_EXTENSION_V1' or m['status']!='ENGINEERING_CANDIDATE_NOT_ACCEPTED' or m['snapshot_contract']!=self.contract_ref:raise ValueError('V2_PRIOR_MANIFEST_REQUIRED')
        if m['entry']!=c.entry_ref or m['contract_digest']!=c.digest:raise ValueError('PRIOR_D1_AUTHORITY_MISMATCH')
        check_availability(m['available_at'],cutoff)
        if m['knowledge_lineage']!='RECONSTRUCTED_CORRECTED' or m['AS_RECORDED'] is not False or m['formal_accepted'] is not False:raise ValueError('PRIOR_D1_LINEAGE_NOT_AUTHORIZED')
        source=exact_json(c.root,m['source_runtime_manifest'])
        if source['contract_id']!='V4_12_R13_RUNTIME_CANDIDATE_MANIFEST' or source['status']!='ENGINEERING_CANDIDATE_NOT_ACCEPTED' or source['entry']!=c.entry_ref or source['contract_digest']!=c.digest or source['snapshot_contract']!=self.contract_ref or source['episode_contract']!=self.episode_ref:raise ValueError('UNSEALED_RUNTIME_SOURCE')
        for n in ['trade_date','revision','available_at','knowledge_lineage','AS_RECORDED','formal_accepted']:
            if source[n]!=m[n]:raise ValueError('SOURCE_MANIFEST_LINEAGE_MISMATCH')
        rows=[json.loads(line) for line in gzip.decompress(exact_bytes(c.root,m['snapshot_bundle'])).splitlines()];self.rows={r['security_id']:r for r in rows};self.index=exact_json(c.root,m['security_index'])['rows']
        if len(rows)!=len(self.rows) or len(rows)!=m['row_count'] or set(self.rows)!=set(self.index) or digest(sorted(self.rows))!=m['security_ids_digest']:raise ValueError('SNAPSHOT_INDEX_MISMATCH')
    def read(self,sid,previous):
        if sid not in self.rows:raise ValueError('MISSING_FROZEN_SECURITY_ROW')
        row=self.rows[sid];m=self.m
        if row['trade_date']!=previous or m['trade_date']!=previous:raise ValueError('SAME_DAY_OR_FOREIGN_PRIOR_D1')
        if digest(row)!=self.index[sid]['row_digest']:raise ValueError('SNAPSHOT_ROW_DIGEST_MISMATCH')
        for n in ['revision','available_at','knowledge_lineage','AS_RECORDED','formal_accepted','contract_digest']:
            if row[n]!=m[n]:raise ValueError('SNAPSHOT_MANIFEST_ROW_MISMATCH')
        if row['namespace']!='Frozen D1[t]' or row['entry_digest']!=self.c.entry_ref['sha256'] or row['source_runtime_manifest_digest']!=m['source_runtime_manifest']['sha256'] or row['episode_contract']!=self.episode_ref:raise ValueError('PRIOR_D1_AUTHORITY_MISMATCH')
        validate_state_set(self.contract,row);validate_episodes(row)
        return row,dict(**m['snapshot_bundle'],security_id=sid,row_digest=self.index[sid]['row_digest'],candidate_manifest=self.ref)

class EpisodeBinder(InputBinder):
    def prior(self,snapshot,security_id):
        if snapshot is None:return None
        if set(snapshot)!=set(['frozen_manifest_episode']):raise ValueError('V2_PRIOR_MANIFEST_REQUIRED')
        if not hasattr(self,'v2_loaders'):self.v2_loaders={}
        ref=snapshot['frozen_manifest_episode'];key=ref['sha256']
        if key not in self.v2_loaders:self.v2_loaders[key]=EpisodeSnapshotLoader(self.contracts,ref,self.cutoff.isoformat())
        return self.v2_loaders[key].read(security_id,self.previous)

class EpisodeSnapshotMaterializer:
    def __init__(self,c,store):self.c=c;self.store=store;self.contract,self.ref=load_contract(c);self.episode_contract,self.episode_ref=episode_contract(c)
    def seal(self,results,source_ref,available_at):
        rows=[]
        for r in results:
            row=dict(snapshot_id=digest(dict(identity=r['identity'],snapshot_contract=self.ref['sha256'])),**r['identity'],available_at=available_at,namespace='Frozen D1[t]',
                breakout_episodes=r['breakout_episodes'],active_breakout_episode_id=r['active_breakout_episode_id'],breakout_episode_set_quality=r['breakout_episode_set_quality'],episode_contract=self.episode_ref,common_facts=r['common_facts'],global_state_observations=r['global_state_observations'],anchor_states=r['anchor_states'],
                active_anchor_id=r['active_selection']['active_anchor_id'],active_anchor_selection_quality=r['active_selection']['quality'],active_anchor_selection_reason=r['active_selection']['reason'],
                active_projection=r['active_projection'],knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False,contract_digest=self.c.digest,entry_digest=self.c.entry_ref['sha256'],source_runtime_manifest_digest=source_ref['sha256'],prior_state_ref=r['prior_state_ref'])
            validate_state_set(self.contract,row);validate_episodes(row);rows.append(row)
        if not rows or len({r['security_id'] for r in rows})!=len(rows) or len({(r['trade_date'],r['revision']) for r in rows})!=1:raise ValueError('INVALID_SNAPSHOT_SCOPE')
        bundle=self.store.jsonl('frozen_d1_episode.jsonl.gz',rows,True);index=self.store.json('frozen_d1_episode_index.json',dict(rows={r['security_id']:dict(row_digest=digest(r),snapshot_id=r['snapshot_id']) for r in rows}))
        m=dict(contract_id='V4_12_FROZEN_D1_BREAKOUT_EXTENSION_V1',status='ENGINEERING_CANDIDATE_NOT_ACCEPTED',trade_date=rows[0]['trade_date'],revision=rows[0]['revision'],available_at=available_at,entry=self.c.entry_ref,contract_digest=self.c.digest,snapshot_contract=self.ref,episode_contract=self.episode_ref,snapshot_bundle=bundle,security_index=index,row_count=len(rows),security_ids_digest=digest(sorted(r['security_id'] for r in rows)),source_runtime_manifest=source_ref,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False)
        return self.store.json('frozen_d1_episode_manifest.json',m)
