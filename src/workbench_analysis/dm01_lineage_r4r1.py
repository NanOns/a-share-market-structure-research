"""Scoped target observation, inherited provenance and explicit first availability.

No provider-first-availability authority is silently inferred from a receive time.
Engineering checks exercise the predicates without creating real evidence.
"""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TARGET = 'TARGET_SESSION_PIT_OBSERVATION'
INHERITED = 'INHERITED_ACCEPTED_PARENT_RECONSTRUCTED'
DERIVED = 'DERIVED_FROM_MIXED_PARENT_AND_TARGET'
STATIC = 'STATIC_ACCEPTED_AUTHORITY_KNOWN_BEFORE_TARGET'
MIXED = 'MIXED_ACCEPTED_PARENT_PLUS_TARGET_SESSION_PIT'
SIMULATION = 'CONTRACT_DESIGN_OR_ENGINEERING_SIMULATION'


def runtime():
    from . import dm01_runtime_r4
    return dm01_runtime_r4


def observation(freeze, root):
    r=runtime(); flag=freeze.get('engineering_simulation',False)
    r.require(type(flag) is bool,'ENGINEERING_SIMULATION_FLAG_MUST_BE_BOOLEAN')
    simulation=flag
    r.validate_lineage(freeze,root,simulation=simulation)
    now=datetime.fromisoformat(freeze['observed_at'].replace('Z','+00:00'))
    local=now.astimezone(ZoneInfo('Asia/Shanghai'))
    r.require(local.date().isoformat()==freeze['trade_date'] and local.hour>=15,'TARGET_OBSERVATION_BEFORE_ELIGIBLE_CLOSE')
    # Simulation timestamps never become public real-PIT claims.
    evidence=freeze['availability_evidence']
    for item in evidence.values():
        for key in ('captured_at','received_at'):
            stamp=datetime.fromisoformat(item[key].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Shanghai'))
            r.require(stamp.hour>=15,'NATIVE_TARGET_OBSERVATION_BEFORE_ELIGIBLE_CLOSE')
    return dict(contract_id='DM01_TARGET_SESSION_OBSERVATION_R4R1_V1',target_trade_date=freeze['trade_date'],
        target_session_observation_proven=not simulation,target_session_observed_at=freeze['observed_at'],
        target_session_received_at={k:v['received_at'] for k,v in evidence.items()},native_source_bindings={k:v['binding'] for k,v in evidence.items()},
        availability_evidence_digest=r.digest(evidence),engineering_observation_checks_passed=True,
        engineering_simulation=simulation,evidence_class=SIMULATION if simulation else 'PIT_OBSERVED',
        first_available_at_target_proven=False,real_forward_evidence=False)


def first_availability(freeze, root):
    """Proof is exact and narrow; the whole head never acquires this claim."""
    r=runtime(); result={}
    contract=r.read(r.ROOT,r.ref(r.ROOT,r.ROOT/r.CONTRACT))
    approved=contract.get('accepted_first_availability_authorities',[])
    for family,evidence in freeze['availability_evidence'].items():
        provider=evidence.get('source_provider_available_at'); binding=evidence.get('first_availability_proof')
        proven=False; checks=False
        if provider and binding:
            native=r.read(root,evidence['binding']);proof=r.read(root,binding)
            r.require(native.get('first_availability_proof')==binding and native.get('source_provider_available_at')==provider,'FIRST_AVAILABILITY_NOT_NATIVE_READBACK')
            r.require(proof.get('contract_id')=='SOURCE_FIRST_AVAILABILITY_PROOF_V1' and
                proof.get('source_family')==family and proof.get('trade_date')==freeze['trade_date'] and
                proof.get('first_available_at')==provider and proof.get('assertion')=='PROVIDER_FIRST_AVAILABILITY', 'FIRST_AVAILABILITY_PROOF_SCOPE')
            # Source-content digest avoids circular native-receipt/proof hashes.
            content=native.get('download',{}).get('sha256') if family=='TDX_FULL_PACKAGE' else native.get('query_operations',[{}])[0].get('response_sha256')
            r.require(content is not None and proof.get('source_content_digest')==content,'FIRST_AVAILABILITY_CONTENT_MISMATCH')
            stamp=datetime.fromisoformat(provider.replace('Z','+00:00'))
            received=datetime.fromisoformat(evidence['received_at'].replace('Z','+00:00'))
            r.require(stamp.tzinfo is not None and stamp<=received and stamp.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()==freeze['trade_date'],'FIRST_AVAILABILITY_TIMESTAMP_SCOPE')
            checks=True
            if not freeze.get('engineering_simulation'):
                authority=proof.get('accepted_authority')
                r.require(authority in approved and authority in freeze['source_authority_bindings'],'FIRST_AVAILABILITY_AUTHORITY_NOT_ACCEPTED')
                r.read(root,authority);proven=True
        result[family]=dict(first_available_at_target_proven=proven,proof=binding if proven else None,
            scope='EXACT_PROVIDER_SOURCE_CONTENT_ONLY',engineering_proof_checks_passed=checks)
    return result


def composition(parent, cap, observed):
    mixed=cap not in ('RAW_DAILY','TRADING_STATUS','ISST')
    return dict(parent_head_lineage=parent['head'].get('knowledge_lineage','UNKNOWN'),
        parent_AS_RECORDED=parent['head'].get('AS_RECORDED',False),parent_head=parent['binding'],
        target_session_observation_class=observed['evidence_class'],contains_inherited_parent_state=mixed,
        artifact_lineage='MIXED_ACCEPTED_PARENT_PLUS_TARGET_PIT' if mixed else 'TARGET_ONLY_PIT',
        as_recorded_scope='TARGET_SESSION_OBSERVATION_ONLY',
        source_classes=[TARGET,STATIC]+([INHERITED,DERIVED] if mixed else []))


def annotate_rows(c, rows, observed):
    r=runtime(); comp=composition(c['parent'],c['cap'],observed)
    real=bool(observed['target_session_observation_proven'] and not c['freeze'].get('engineering_simulation'))
    for row in rows:
        # Historical closed rows must remain byte-equivalent to the inherited rows.
        if c['cap'].startswith('PERIOD_') and row.get('as_of_date',row.get('trade_date',''))!=c['target']:
            continue
        inherited=comp['contains_inherited_parent_state']
        old=row.get('knowledge_lineage')
        row.update(lineage_class=DERIVED if inherited else TARGET,
            as_recorded_scope='TARGET_SESSION_OBSERVATION_ONLY',
            target_session_observation_scope='NATIVE_SOURCE_INPUT_OBSERVATION_ONLY',
            knowledge_lineage=SIMULATION if not real else (MIXED if inherited else 'PIT_OBSERVED'),
            AS_RECORDED=bool(real and not inherited),first_available_at_target_proven=False,
            target_session_observation_proven=real,target_session_observed_at=observed['target_session_observed_at'],
            target_session_received_at=observed['target_session_received_at'],parent_head_binding=c['parent']['binding'],
            kernel_lineage_before_composition=old,availability_evidence_digest=observed['availability_evidence_digest'])
    return comp


def forward_admission(parent,freeze,cal,receipts,post,root):
    r=runtime();obs=observation(freeze,root)
    r.require(r.kernels.resolve_target_session(parent['head']['accepted_trade_date'],cal,freeze['observed_at'],freeze['trade_date'])==freeze['trade_date'],'FORWARD_NEXT_SESSION_MISMATCH')
    checks=set(receipts)==set(r.CAPABILITIES) and post['status']=='PASS'
    r.require(checks,'FORWARD_ALL_NINE_CHECKS_MISSING')
    simulation=freeze.get('engineering_simulation') is True
    if not simulation:
        r.accepted_envelope(root)
        r.require(parent['binding']==r.current_parent(root)['binding'] and cal['binding']==r.calendar(root)['binding'],'FORWARD_AUTHORITY_MOVED')
        r.require(all(v['target_session_observation_proven'] is True for v in receipts.values()),'FORWARD_COMPONENT_OBSERVATION_MISSING')
    obs.update(real_forward_evidence=bool(not simulation and obs['target_session_observation_proven'] and checks),
        parent_head=parent['binding'],source_manifest_digest=freeze['manifest_sha256'],permissions=r.PERMISSIONS,
        all_nine_checks_passed=True,first_availability_by_source=first_availability(freeze,root))
    return obs


def require_real_forward(candidate,freeze,parent,cal,root):
    r=runtime()
    r.require(candidate.get('real_forward_evidence') is True,'REAL_FORWARD_EVIDENCE_REQUIRED')
    r.require(not freeze.get('engineering_simulation') and not candidate.get('engineering_simulation'),'SIMULATION_REAL_FORWARD_FORBIDDEN')
    r.require(candidate.get('knowledge_lineage')==MIXED and candidate.get('AS_RECORDED') is False and
        candidate.get('first_available_at_target_proven') is False,'WHOLE_CANDIDATE_LINEAGE_OVERCLAIM')
    comp=candidate['lineage_composition']
    r.require(comp['parent_head']==parent['binding'] and comp['parent_head_lineage']==parent['head'].get('knowledge_lineage','UNKNOWN') and
        comp['parent_AS_RECORDED']==parent['head'].get('AS_RECORDED',False),'FORWARD_PARENT_LINEAGE_MISMATCH')
    post=r.read(root,candidate['cross_postcheck'])
    actual=forward_admission(parent,freeze,cal,candidate['components'],post,root)
    receipt=r.read(root,candidate['target_session_observation_receipt'])
    r.require(actual==receipt and actual['real_forward_evidence'] and candidate.get('target_session_observation_proven') is True,'FORWARD_OBSERVATION_RECEIPT_MISMATCH')
    return actual


def head_lineage(parent,candidate,observation_binding):
    real=candidate.get('real_forward_evidence') is True and not candidate.get('engineering_simulation')
    return dict(knowledge_lineage=MIXED,AS_RECORDED=False,first_available_at_target_proven=False,
        lineage_composition=dict(parent_head_lineage=parent.get('knowledge_lineage','UNKNOWN'),
            parent_AS_RECORDED=parent.get('AS_RECORDED',False),contains_inherited_parent_state=True,
            artifact_lineage='MIXED_ACCEPTED_PARENT_PLUS_TARGET_PIT',as_recorded_scope='TARGET_SESSION_OBSERVATION_ONLY'),
        target_session_evidence_class='PIT_OBSERVED' if real else SIMULATION,
        target_session_observation_proven=bool(real and candidate.get('target_session_observation_proven')),
        target_session_trade_date=candidate['target_trade_date'],target_session_source_manifest=candidate['source_manifest'],
        target_session_all_nine_receipts=candidate['components'],target_session_observation_receipt=observation_binding,
        target_session_real_forward_evidence=real)


def validate_head_lineage(head,parent):
    r=runtime()
    r.require(head.get('knowledge_lineage')==MIXED and head.get('AS_RECORDED') is False and
        head.get('first_available_at_target_proven') is False,'WHOLE_HEAD_LINEAGE_OVERCLAIM')
    r.require(head['lineage_composition']['parent_head_lineage']==parent.get('knowledge_lineage','UNKNOWN') and
        head['lineage_composition']['parent_AS_RECORDED']==parent.get('AS_RECORDED',False),'INHERITED_PARENT_LINEAGE_ERASED')


def validate_r25_binding(root,binding,*,engineering=False):
    """Validate a bridge contract only; this function cannot issue an R25 grant."""
    r=runtime();b=r.read(root,binding)
    r.require(b.get('contract_id')=='DM01_R25_TARGET_SESSION_PIT_BINDING_R4R1_V1','R25_EXACT_TARGET_SESSION_BINDING_REQUIRED')
    parent=r.read(root,b['parent_data_head']);child=r.read(root,b['child_data_head']);candidate=r.read(root,b['candidate'])
    obs=r.read(root,b['target_session_observation_receipt']);freeze=r.read(root,b['target_session_source_manifest'])
    validate_head_lineage(child,parent)
    r.require(child['final_candidate']==b['candidate'] and child['parent_archive']==b['parent_data_head'] and
        child['target_session_trade_date']==b['target_trade_date']==candidate['target_trade_date']==freeze['trade_date'] and
        candidate['source_manifest']==b['target_session_source_manifest']==child['target_session_source_manifest'] and
        candidate['target_session_observation_receipt']==b['target_session_observation_receipt']==child['target_session_observation_receipt'] and
        b['target_session_all_nine_receipts']==candidate['components']==child['target_session_all_nine_receipts'] and
        set(candidate['components'])==set(r.CAPABILITIES),'R25_TARGET_BINDING_MISMATCH')
    r.require(b['parent_data_head']['sha256']==candidate['parent_data_head_digest']==child['parent_head_sha256'],'R25_PARENT_CHILD_DIGEST_MISMATCH')
    for value in candidate['components'].values():
        artifact=Path(value['artifact_path']);r.require(r.sha(artifact)==value['artifact_sha256'],'R25_COMPONENT_DIGEST_MISMATCH')
    if engineering:
        r.require(obs['engineering_simulation'] is True and obs['real_forward_evidence'] is False and
            candidate['real_forward_evidence'] is False and child['target_session_real_forward_evidence'] is False,
            'ENGINEERING_BRIDGE_MUST_NOT_BE_REAL')
        return dict(status='PASS_ENGINEERING_CONTRACT_PATH',r25_grant=False,real_forward_evidence=False)
    r.current_parent(root)
    r.require(child['target_session_evidence_class']=='PIT_OBSERVED' and child['target_session_observation_proven'] is True and
        child['target_session_real_forward_evidence'] is True,'R25_CHILD_TARGET_OBSERVATION_MISSING')
    r.require(b['child_data_head']==r.ref(root,Path(root)/r.HEAD),'R25_CHILD_NOT_CURRENT_ACCEPTED_HEAD')
    r.require(candidate.get('real_forward_evidence') is True and obs.get('real_forward_evidence') is True and
        not freeze.get('engineering_simulation') and obs.get('engineering_simulation') is False,'R25_REAL_TARGET_OBSERVATION_REQUIRED')
    r.require(obs['source_manifest_digest']==freeze['manifest_sha256'] and
        obs['parent_head']['sha256']==candidate['parent_data_head_digest'] and obs['permissions']==r.PERMISSIONS and
        obs['all_nine_checks_passed'] is True,'R25_OBSERVATION_PROVENANCE_MISMATCH')
    r.accepted_envelope(root)
    observed=observation(freeze,root)
    r.require(all(obs.get(k)==v for k,v in observed.items() if k not in ('real_forward_evidence',)), 'R25_NATIVE_OBSERVATION_MISMATCH')
    context=r.read(root,candidate['parent_context'])
    cal=r.calendar(root)
    r.require(candidate['calendar']==child['calendar']==cal['binding'] and
        r.kernels.resolve_target_session(parent['accepted_trade_date'],cal,freeze['observed_at'],freeze['trade_date'])==freeze['trade_date'],
        'R25_EXACT_NEXT_SESSION_REQUIRED')
    r.require(context['head']==parent and context['components']==parent['component_artifacts'],'R25_PARENT_CONTEXT_MISMATCH')
    post=r.check_cross_components(candidate['components'],freeze,context,cal,
        dict(binding=candidate['identity'],publication_id=candidate['identity']['sha256'],records=r.read(root,candidate['identity'])['records']))
    r.require(post['status']=='PASS' and r.digest(post)==candidate['postcheck_digest'],'R25_TARGET_COMPONENT_POSTCHECK_FAILED')
    return dict(status='PASS_EXACT_TARGET_SESSION_BINDING',r25_grant=False)
