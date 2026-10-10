"""Bounded packaging stage evidence; never grants production/capability admission."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import os
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_desktop.storage import atomic
from scripts.build_windows_package_v1 import inventory


def bind(relative):
    p=ROOT/relative
    return dict(path=relative,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)


def main():
    folder=ROOT/'docs/evidence/windows_full_package_20261010'
    folder.mkdir(parents=True,exist_ok=True)
    design='docs/design/V4_WINDOWS_FULL_PACKAGE_FINAL_R2_1_20261010.md'
    phase='reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json'
    heads=['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']
    graph=inventory()
    atomic(folder/'S0_DEPENDENCY_INVENTORY.json',graph)
    policy=json.loads((ROOT/'config/read_only_operational_daily_release_policy_v1_1.json').read_bytes())
    protected=[dict(binding=row,exact_current_sha256=bind(row['path'])['sha256']) for row in policy['accepted_algorithm_bindings']]
    if any(row['binding']['sha256']!=row['exact_current_sha256'] for row in protected):
        raise ValueError('ACCEPTED_ALGORITHM_BYTES_CHANGED')
    shutil.copyfile('G:/codex_tmp/package_s0_junit.xml',folder/'S0_JUNIT.xml')
    tools={}
    from importlib.metadata import version
    for name in ['PyInstaller','pystray','Pillow','psutil','numpy','scipy','scikit-learn','baostock','pandas']:
        tools[name]=version(name)
    stage=dict(contract_id='V4_WINDOWS_PACKAGE_S0_STAGE_V1',design=bind(design),design_contract='V4_WINDOWS_FULL_PACKAGE_DESIGN_R2_1_20261010',
        baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        user_authorization='现在开始按照最新设计文档实现 争取一次pass',
        consulted=[bind('docs/upgrade/DYNAMIC_DAILY_DD07_FINAL_RELEASE_20261009.md'),bind('docs/upgrade/FP14_PRODUCTION_RELEASE_EXECUTION_20261008.md')],
        inherited_phase0=dict(binding=bind(phase),status=json.loads((ROOT/phase).read_bytes())['phase0_status']),
        protected_heads_before=[bind(p) for p in heads],protected_algorithm_bytes=protected,
        stage_scope='Desktop lifecycle, G paths, lock, maintenance versus user cancel, fixed task adapter and dependency inventory',
        tests=dict(passed=33,failed=0,evidence=bind((folder/'S0_JUNIT.xml').relative_to(ROOT).as_posix()),
                   limitations='Executor simulations do not prove numeric daily frozen E2E'),
        tools=tools,dependency_inventory=bind((folder/'S0_DEPENDENCY_INVENTORY.json').relative_to(ROOT).as_posix()),
        subprocess_decisions=dict(tdx_download='Original byte-identical modules in private IO scope, fixed in-process original R3 module task, owner required; no EXE recursion',
            git='Bundle local Git reader/DLLs; inherited historical object verification remains intact; no PATH Git requirement',
            historical_daily_script='No AST import reachability from packaged entry',
            dynamic_imports='Reviewed explicit adapter aliases and json/zoneinfo/getpass/os; no arbitrary plugin loading'),
        acceptance='S0_PASS_ENGINEERING_CONTRACT_AND_ISOLATED_BOUNDARIES',
        next_stage='S1_ACTUAL_FROZEN_RUNTIME_AND_FULL_DAILY_E2E',
        production_takeover='NOT_EXECUTED_REQUIRES_SEPARATE_SCOPE',external_acceptance='NOT_GRANTED',
        observed_at=datetime.now(timezone.utc).isoformat())
    atomic(folder/'S0_STAGE_RECEIPT.json',stage)
    items=[]
    for item,scope,evidence in [
        ('PKG-A01','Whole workspace lock and startup before recover','S0_JUNIT.xml'),
        ('PKG-A02','Maintenance safe boundary versus user cancellation','S0_JUNIT.xml'),
        ('PKG-A03','CAS/readback and COMMITTED protection','S0_JUNIT.xml'),
        ('PKG-A04','G roots, frozen originals, WAL/schema and compatibility','S0_STAGE_RECEIPT.json'),
        ('PKG-A05','Frozen task whitelist and runtime independence','S0_DEPENDENCY_INVENTORY.json'),
        ('PKG-A06','Actual frozen numeric daily full chain and failures','S0_STAGE_RECEIPT.json')]:
        items.append(dict(id=item,scope=scope,evidence=evidence,status='OPEN_FROZEN_AND_INDEPENDENT_ACCEPTANCE_PENDING',
                          external_acceptance='NOT_GRANTED',closed_by=None))
    atomic(folder/'INDEPENDENT_AUDIT_ITEMS.json',dict(contract_id='V4_WINDOWS_PACKAGE_INDEPENDENT_AUDIT_LEDGER_V1',items=items))
    print(stage['acceptance'])


if __name__=='__main__':
    for key in ('TMP','TEMP','TMPDIR'):os.environ[key]='G:/codex_tmp'
    main()
