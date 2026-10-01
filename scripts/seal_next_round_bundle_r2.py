"""Scoped external formalizations plus candidate execution registry, no promotion."""
from scripts.next_round_bundle_r2 import ROOT,P,read,write,bind,verify_protected,AUDIT,MASTER,BASELINE

def main():
    entry=verify_protected();scoped=read(P+'scoped_acceptance/SCOPED_FORMALIZATION_CLOSURE_R2.json')
    a02a05=read('reports/audits/next_round_r2/A02_A05_FORMAL_HANDOFF_R1.json')
    entries={}
    for key,state in scoped['scoped_current_states'].items():
        entries[key]=dict(current_state=state,acceptance='INDEPENDENT_EXTERNAL_ACCEPTANCE_FORMALIZED_SCOPED',
            acceptance_record=scoped['records'][key],handoff=bind(P+'scoped_acceptance/SCOPED_FORMALIZATION_CLOSURE_R2.json'))
    for key in ('A02','A05'):
        entries[key]=dict(current_state='ACCEPTED_SCOPED',acceptance='INDEPENDENT_EXTERNAL_ACCEPTANCE_FORMALIZED_SCOPED',
            acceptance_record=bind('reports/audits/next_round_r2/'+key+'_EXTERNAL_ACCEPTANCE_RECORD_R1.json'),
            business_amendments='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',handoff=bind('reports/audits/next_round_r2/A02_A05_FORMAL_HANDOFF_R1.json'))
    entries['A04']=dict(current_state='GO_FORWARD_CANDIDATE_WARMUP',acceptance='PENDING_INDEPENDENT_EXTERNAL_REAUDIT',
        historical_formal_capability='BLOCKED',current_real_sector_rows=378,current_real_known_amount_a_rows=0,missing_H21_sessions=20,
        consumer_adoption=False,handoff=bind('reports/audits/a04_r3/A04_R3_1_EXTERNAL_REAUDIT_HANDOFF_R1.json'))
    entries['V4-11']=dict(current_state='SEMANTIC_REPAIR_CANDIDATE',acceptance='PENDING_INDEPENDENT_EXTERNAL_REAUDIT',
        status='V4_11_R2_SEMANTIC_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',
        real_AMR20_target_accepted_producer='UNAVAILABLE',sector_amount_A_gate_removed=True,
        handoff=bind('reports/v4_11/candidate_r2/V4_11_SEMANTIC_REPAIR_EXTERNAL_REAUDIT_HANDOFF_R2.json'))
    registry=dict(contract_id='V4_CROSS_STAGE_SCOPED_FORMALIZATION_AND_CANDIDATE_REGISTRY_R12',
        baseline_commit=BASELINE,external_authority=bind(AUDIT),master=bind(MASTER),
        accepted_parent_registry=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R10.json'),
        candidate_parent_registry=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R11_CANDIDATE.json'),
        entries=entries,active_registry_changed=False,stage_head_action='KEEP',data_head_action='KEEP',
        permissions=entry['permissions'],new_repairs_external_acceptance=False,
        status='FORMALIZATION_COMPLETE_AND_CANDIDATES_READY_FOR_EXTERNAL_REAUDIT')
    rb=write('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R12_FORMALIZATION.json',registry)
    write(P+'BATCH_CANDIDATE_HANDOFF_R1.json',dict(contract_id='V4_NEXT_ROUND_R2_BATCH_HANDOFF',baseline_commit=BASELINE,
        status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',stage_entry=bind(P+'BATCH_STAGE_ENTRY_R1.json'),registry=rb,
        packages=entries,permissions=entry['permissions'],Phase0=entry['phase0'],
        DataHead='KEEP_2026-09-30',StageHead='KEEP_V4_00_TO_V4_10_ACCEPTED',V4_12_implemented=False,
        formal_V4_11_head_created=False,amendment_heads_promoted=False,
        clean_joint=P+'BATCH_CLEAN_CHECKOUT_R1.json',test_only_is_not_release_readiness=True,
        next_stage='COMMIT_PUSH_THEN_STOP_WAIT_FOR_INDEPENDENT_EXTERNAL_REAUDIT'))
    text='''# R2 批次候选交付（2026-10-01）\n\n以本轮独立外部审计为 scoped acceptance authority，按 Master R2 完成本轮五张执行卡。V4-11 stock AMR20 已与 sector Amount A 分离，保持原阈值；9/30 的5224只股票重跑中 sector审计导致的 UNKNOWN 为0。真实 AMR20/common-safety/episode 目标 producer 尚无对应 accepted publication，确认结果保持 UNKNOWN；TREND same-day LOO 保持 diagnostic-only。\n\nA02 正式接受 reconstructed 六日 RPS producer，独立RPS Head已建立，V4-05/V4-07/V4-09实际重放的业务变化为5222/5222/2811，均仅生成 amendment candidate。A05仅接受9/24 current snapshot，541板块B2 candidate为FALSE535/TRUE2/UNKNOWN4，没有跨日注入9/30。\n\nA04真实 accepted membership仅9/30，378板块均H21 WARMUP/UNKNOWN，缺20日；历史formal capability为BLOCKED。算术producer与consumer gate已分离，未授权统一5/.8门。A03工程正式接受、继续自然积累；A06接受无容差fail-closed；A07 pre-capture永久能力限制；Owner为inactive scoped accepted metadata；Reader v2仅accepted-history selector。\n\n新增R12 current-state记录，各项接受边界及新candidate分别绑定独立证据。旧R10/R11、全部既有Accepted Heads/source/evidence保留。Data Head保持2026-09-30，Stage Head保持V4_00_TO_V4_10_ACCEPTED；没有V4-12、V4-11正式Head、amendment promotion或Production/Shadow/Focus/Global Mandatory Adoption。\n\n实际干净checkout回归证据将由 reports/next_round_r2/BATCH_CLEAN_CHECKOUT_R1.json 提供。全部代码与evidence统一commit/push后STOP，等待下一轮独立外部验收。\n'''
    from scripts.next_round_bundle_r2 import atomic_bytes
    atomic_bytes('docs/audits/NEXT_ROUND_R2_CANDIDATE_CLOSURE_20261001.md',text.encode('utf8'))
    verify_protected()

if __name__=='__main__':main()
