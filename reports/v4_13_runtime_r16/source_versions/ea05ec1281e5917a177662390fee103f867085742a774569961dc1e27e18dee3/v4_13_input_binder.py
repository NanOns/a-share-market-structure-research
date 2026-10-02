"""Accepted heads only; no raw, provider, directory scan or candidate substitute."""
from collections import defaultdict
import json
from .v4_13_io import exact,rows,available,digest,envelope,file_ref

COUNTERS=['raw_fallback_count','provider_direct_read_count','raw_reconstruction_count','current_membership_silent_fallback_count','self_including_context_reuse_count','unauthorized_v4_12_candidate_use_count','context_to_raw_qualification_mutation_count']


class AcceptedInputBinder:
    def __init__(self, contracts, trade_date, cutoff):
        self.contracts=contracts;self.root=contracts.root;self.date=trade_date;self.cutoff=cutoff
        self.counters=dict.fromkeys(COUNTERS,0);self.refs=list(contracts.owner_refs.values())
        route=contracts.config['membership_consumer_route'];stage=json.loads(exact(self.root,route['stage_binding']))
        sector=contracts.owners['V4_08'];member=contracts.owners['V4_08_PIT_MEMBERSHIP']
        if stage['v4_08_binding']['sha256']!=route['sector_owner']['sha256'] or sector['membership_binding']['sha256']!=route['membership_owner']['sha256'] or sector['capabilities']['ACCEPTED_CONTEXT_ROUTING']!='ENGINEERING_ACCEPTED':raise ValueError('BLOCKED_MEMBERSHIP_CONSUMER_SCOPE')
        exact(self.root,sector['membership_binding'])
        self.membership_head=member;self.snapshot=json.loads(exact(self.root,member['snapshot']));exact(self.root,member['source_revision'])
        self.membership_complete=self.snapshot['target_trade_date']==trade_date and self.snapshot['membership_basis']=='PIT_OBSERVED' and available(self.snapshot['cutoff'],cutoff)
        self.memberships=[]
        if self.membership_complete:
            for row in rows(self.root,member['facts']):
                if row['target_trade_date']!=trade_date or row['snapshot_id']!=member['membership_snapshot_id'] or row['source_revision_id']!=self.snapshot['source_revision_id'] or row['membership_basis']!='PIT_OBSERVED' or row['membership_quality']!='PIT_OBSERVED_ACCEPTED' or not available(row['provider_available_at'],cutoff):raise ValueError('MEMBERSHIP_EXACT_IDENTITY_OR_CUTOFF_MISMATCH')
                if row['identity_status']=='MAPPED':self.memberships.append(row)
            self.refs.extend([member['snapshot'],member['facts'],member['source_revision']])
        self.groups=defaultdict(list);self.by_security=defaultdict(list)
        for row in self.memberships:self.groups[row['sector_id']].append(row);self.by_security[row['security_id']].append(row)
        self.current={};self.stock={};self.seed={};self.history={};self.history_digest=digest([])
        # Registry fields bind exact owners; profile/native publications are never interchangeable.
        core_rows={};native_rows={}
        for owner,collection in [('V4_04',core_rows),('V4_05',native_rows)]:
            head=contracts.owners[owner]
            ref=head['accepted_artifact'] if owner=='V4_04' else head['accepted_artifacts']['full_scope_factors']
            self.refs.append(ref);exact(self.root,ref)
            if head.get('target_trade_date',head.get('accepted_at_date'))!=trade_date:continue
            for row in rows(self.root,ref):
                if row.get('trade_date')!=trade_date:continue
                if row.get('source_cutoff') and not available(row['source_cutoff'],cutoff):raise ValueError('FUTURE_ACCEPTED_OWNER_PUBLICATION')
                collection[row['security_id']]=row
        def owned_value(row,name):
            item=row.get('fields',{}).get(name,row.get('derived_fields',{}).get(name))
            if not isinstance(item,dict):return None
            if item.get('quality_state',item.get('quality')) not in ['OBSERVED','ACCEPTED','KNOWN']:return None
            return item.get('value')
        for sid in sorted(set(core_rows)|set(native_rows)):
            core=core_rows.get(sid,{});native=native_rows.get(sid,{})
            primitive={}
            for spec in contracts.config['field_registry']['input_fields']:
                name=spec.get('source_field');owner=spec.get('owner_binding',{}).get('path')
                if not name or name in ['membership_snapshot','base_seed_raw']:continue
                row=core if owner==contracts.owner_refs['V4_04']['path'] else native if owner==contracts.owner_refs['V4_05']['path'] else {}
                value=owned_value(row,name);primitive[name]=dict(value=value,quality='ACCEPTED' if value is not None else 'UNKNOWN')
            # No unpublished close/MA spread reconstruction; native owner will mark missing input.
            self.current[sid]=dict(trade_date=trade_date,fields=primitive)
            self.stock[sid]={name:owned_value(core,name) for name in ['rps5','rps20','rps20_delta3','stock_ret1','stock_ret5']}
            for name in ['compression_state','ma_structure_state']:
                state=core.get('states',{}).get(name,{})
                self.stock[sid][name]=state.get('value','UNKNOWN')
        self.seed_capability=False
        seed_head=contracts.owners['V4_07'];seed_ref=seed_head['candidate_artifact'];self.refs.append(seed_ref);exact(self.root,seed_ref)
        if seed_head['accepted_input']['trade_date']==trade_date:
            for row in rows(self.root,seed_ref):
                if row.get('trade_date')!=trade_date:raise ValueError('BASE_SEED_DATE_MISMATCH')
                if row.get('created_at') and not available(row['created_at'],cutoff):raise ValueError('FUTURE_BASE_SEED_PUBLICATION')
                self.seed[row['security_id']]=True if row['base_seed_state']=='TRUE' else False if row['base_seed_state']=='FALSE' else None
            self.seed_capability=True
        calendar_ref=member['calendar_head'];calendar_head=json.loads(exact(self.root,calendar_ref));calendar=json.loads(exact(self.root,calendar_head['accepted_extension']))
        sessions=calendar.get('sessions',calendar.get('trade_dates',[]));self.sessions=[s['trade_date'] if isinstance(s,dict) else s for s in sessions]
        prior=[s for s in self.sessions if s<trade_date]
        self.prior_session=max(prior) if prior else None
        self.prior_session_ref=dict(calendar_head=calendar_ref,calendar=calendar_head['accepted_extension'],trade_date=self.prior_session,context_publication=None,reason='NO_ACCEPTED_PRIOR_LOO_CONTEXT')
        self.structure={};self.structure_ref=None

    def relationship(self, security_id):
        basis='PIT_OBSERVED' if self.membership_complete else 'UNKNOWN'
        meta=dict(membership_basis=basis,loo_basis='NOT_REQUIRED',refs=[self.membership_head['facts']])
        if not self.membership_complete:return {f:envelope(**meta) for f in ['primary_industry','supporting_concepts']}
        related=self.by_security.get(security_id,[]);industry=[r for r in related if r['sector_type']=='INDUSTRY'];concepts=sorted({r['sector_id'] for r in related if r['sector_type']=='THEME'})
        if len(industry)>1 and any('official_classification_priority' not in r or 'taxonomy_depth' not in r for r in industry):primary=envelope(reason='UNKNOWN_CLASSIFICATION_CONFLICT_METADATA',**meta)
        else:
            ordered=sorted(industry,key=lambda r:(r.get('official_classification_priority',0),-r.get('taxonomy_depth',0),r['sector_id']))
            primary=envelope(ordered[0]['sector_id'] if ordered else None,'KNOWN' if ordered else 'NOT_APPLICABLE',None,**meta)
        return dict(primary_industry=primary,supporting_concepts=envelope(concepts,'KNOWN' if concepts else 'NOT_APPLICABLE',None,**meta))

    def load_structure(self):
        head=self.contracts.owners['V4_12'];projection=self.contracts.config['projection'];matches=[]
        for r in head['publication_authority']['authorized_manifests']:
            manifest=json.loads(exact(self.root,r))
            if manifest['trade_date']==self.date and manifest.get('scope')=='REAL_ACCEPTED_SOURCE_CANDIDATE' and available(manifest['available_at'],self.cutoff):matches.append((manifest['revision'],r,manifest))
        if not matches:return
        _,ref,manifest=max(matches,key=lambda x:x[0]);self.structure_ref=ref;self.refs.append(ref)
        if manifest['contract_id']!=projection['source_publication_contract']:raise ValueError('UNAUTHORIZED_V4_12_PUBLICATION_CONTRACT')
        artifact=next(r for r in manifest['artifacts'] if r['path'].endswith('runtime_security.jsonl.gz'))
        for row in rows(self.root,artifact):
            self.structure[row['identity']['security_id']]={k:row[k] for k in ['active_selection','active_projection','anchor_states','basic_breakout_state','events','identity','breakout_projection_quality','breakout_projection_reason']}
        self.structure_artifact_ref=artifact;self.refs.append(artifact)
