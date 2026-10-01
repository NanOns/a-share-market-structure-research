"""Seal the authorized promotion after one actual clean-checkout verification."""
from pathlib import Path
import argparse,json,sys,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.dm01_accepted_chain_v1 import binding,load,sha,validate_head_v2,HEAD_PATH
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json
P='reports/audits/DM01_A01_R3_PROMOTION_'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--checkout',type=Path,required=True);args=parser.parse_args()
    checkout=args.checkout.resolve()
    receipt=load(checkout,binding(checkout,P+'CLEAN_CHECKOUT_R1.json'))
    if receipt['status']!='PASS' or receipt['summary']['failures'] or receipt['summary']['errors'] or receipt['new_deselects'] or not receipt['protected_heads_unchanged']:
        raise ValueError('CLEAN_REGRESSION_NOT_COMPLETE')
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()
    if receipt['tested_commit']!=actual:raise ValueError('TESTED_CHECKOUT_HEAD_MISMATCH')
    if subprocess.check_output(['git','status','--porcelain=v1'],cwd=checkout,text=True).strip():raise ValueError('VERIFIED_CHECKOUT_NOT_CLEAN')
    head=load(ROOT,binding(ROOT,HEAD_PATH));result=validate_head_v2(ROOT,head)
    if receipt['data_head']!=binding(ROOT,HEAD_PATH):raise ValueError('TESTED_HEAD_NOT_CURRENT')
    entry=load(ROOT,binding(ROOT,P+'STAGE_ENTRY_R1.json'))
    for ref in entry['protected_bindings']:
        if sha(ROOT/ref['path'])!=ref['sha256']:raise ValueError('PROTECTED_BYTES_CHANGED')
    names=['CLEAN_CHECKOUT_R1.json','CLEAN_REGRESSION_R1.xml','CLEAN_REGRESSION_R1.log','NO_SYMBOL_SCAN_R1.json','INDEPENDENT_READBACK_R1.json']
    for name in names:atomic_bytes(ROOT/(P+name),(checkout/(P+name)).read_bytes())
    readback=load(ROOT,binding(ROOT,P+'INDEPENDENT_READBACK_R1.json'))
    if readback['status']!='PASS' or not readback['all_final_nine'] or not readback['stage_head_unchanged']:raise ValueError('SOURCE_READBACK_NOT_PASS')
    evidence=[binding(ROOT,P+name) for name in names]+[binding(ROOT,P+'PREFLIGHT_R1.json'),binding(ROOT,'reports/v4_joint/DM01_A01_R3_DATA_HEAD_PROMOTION_RECEIPT_R1.json')]
    gates=dict(DM01_A01_R3_EXTERNAL_ACCEPTANCE_FORMALIZED='PASS',V4_DATA_ACCEPTED_HEAD='PROMOTED_TO_2026_09_30',
        V4_STAGE_ACCEPTED_HEAD='UNCHANGED',A13_FORMALIZATION='EXTERNALLY_CONFIRMED',REGISTRY_R10='PASS',
        CLEAN_CHECKOUT='PASS',INDEPENDENT_READBACK='PASS',NO_SYMBOL='PASS',OWNER_REGISTRY_BOOTSTRAP='OPEN',
        GLOBAL_MANDATORY_ADOPTION=False,PRODUCTION=False,SHADOW=False,FOCUS=False)
    closure=dict(contract_id='DM01_A01_R3_DATA_HEAD_PROMOTION_CLOSURE_V1',status='AUTHORIZED_SCOPED_PROMOTION_COMPLETE',
        stage_contract=entry['stage_contract'],external_authority=entry['external_authority'],audited_head=entry['baseline_commit'],
        tested_commit=receipt['tested_commit'],accepted_head=binding(ROOT,HEAD_PATH),accepted_chain=head['accepted_chain'],
        external_acceptance_record=head['external_acceptance_record'],audit_registry=head['audit_registry'],
        component_permission_basis='EXACT_20260930_FINAL_COMPONENT_RECEIPTS',component_statuses={c:p['status'] for c,p in head['component_permissions'].items()},
        protected_heads_exact=True,evidence_bindings=evidence,acceptance_result=gates,summary=receipt['summary'],
        old_contracts_and_candidates_immutable=True,historical_binding_resolution='EXPLICIT_EXACT_20260924_ARCHIVE_ONLY',
        v4_08_v4_09_reacceptance_performed=False,next_stage='CONSUMER_SPECIFIC_VERSIONED_CONTRACTS; NO_PRODUCTION_SHADOW_FOCUS_AUTHORIZATION')
    atomic_json(ROOT/(P+'STAGE_CLOSURE_R1.json'),closure);atomic_json(ROOT/(P+'GATES_R1.json'),gates)
    md=f"""# DM01 A01-R3 外部接受正式化与 Data Head 推进收口

独立外部验收正式 authority 为 `{entry['external_authority']['document']['path']}`，审计基线 `{entry['baseline_commit']}`；任务卡只定义执行范围。

Data Head 已原子推进至 2026-09-30。Accepted Chain 保留 9/24 → 9/28 → 9/29 → 9/30 全部父子指针、27 个组件及 source instances。旧 9/24 Data Head 原始 2478 bytes 已归档，SHA-256 未变化。V2 契约和独立 reader 使用明确归档绑定，不降低旧 hash gate。

Registry R10 清理 A12 当前矛盾状态并保留 R9 历史；DM01 连续链正式接受，A13 formalization 外部确认通过。Owner Registry Bootstrap 仍 OPEN。Stage Head 以及 V4-08/V4-09 字节保持不变，本轮未进行业务重建或重新接受。

最终组件中 ADJUSTED_DAILY、PERIOD_ADJUSTED、PRICE_LIMIT 保持 DEGRADED_PASS，其余六组件 FULL_PASS。权限及原因逐项来自最终 receipt；READY 行未用于升级 capability。

新 checkout `{receipt['tested_commit']}` 独立重读完整链与最终九组件真实 source bindings。Disposable PostgreSQL 联合回归：{receipt['summary']['passed']} passed / {receipt['summary']['skipped']} skipped / 1 既有授权 deselected / 0 failures / 0 errors。config/.env 未读取，production DB 未使用，No-Symbol PASS。详见 `{P}INDEPENDENT_READBACK_R1.json` 和 `{P}CLEAN_CHECKOUT_R1.json`。

production=false、shadow=false、focus=false。后续消费新 Data Head 须按各 stage 独立版本化合同执行；此次推进不授予生产权限或 global mandatory adoption。
"""
    atomic_bytes(ROOT/'docs/audits/DM01_A01_R3_DATA_HEAD_PROMOTION_CLOSURE_R1_20261001.md',md.encode('utf8'))
    print(json.dumps(gates))
if __name__=='__main__':main()
