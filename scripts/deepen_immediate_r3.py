"""Current-snapshot deepening evidence; immutable inputs and G-only writes."""
from immediate_r3_common import *
from collections import defaultdict
import inspect
import sys
sys.path.insert(0,str(ROOT/'src'))
D=OUT/'11_DEEPENING'

def prepare():
    contracts=['D:/Users/lps/Desktop/阶段任务/V4_IMMEDIATE_EXECUTION_MASTER_AND_TASK_CARDS_R3_20261010.md',
      'AGENTS.md','scripts/AGENTS.md',
      'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md',
      'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md',
      'docs/evidence/core_algo_ui_r2_20261010/REMAINING_WORK_LEDGER.json',
      'docs/evidence/core_algo_ui_r2_20261010/CROSS_CUTTING_AUDIT_ITEMS.md']
    write(D/'STAGE_CONTRACT.json',dict(contract_id='V4_IMMEDIATE_R3_DEEPENING_V1',BASE_SHA=git('rev-parse','HEAD'),
      contracts=[binding(p) for p in contracts],T0='2026-10-09',
      protected_heads=[binding(p) for p in ('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json')],
      authorization='USER_CONTINUE_ALL_OTHER_TASKS_CURRENT_SNAPSHOT_ONLY',
      exclusions=[dict(scope='BSE',reason='USER_DEFERRED_NETWORK_IDENTITY_VERIFICATION'),
                  dict(scope='SZ.001235',reason='USER_REPORTED_DELISTED_EXCLUDED_THIS_ROUND',
                       provenance='User message in current chat; no source authority or historical identity replacement')],
      publication_authorized=False,acceptance='IN_PROGRESS',next_stage='ALG_OWNER_AMOUNT_COHORT_PRODUCT_QA'))

def cases():
    a=load(OUT/'02_P0_ALG/P0_ALG_ORACLE_RESULT.json');i=load(OUT/'02_P0_ALG/P0_ALG_ORACLE_INPUT.json')
    head=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');identity=load(load(head['membership_snapshot'])['identity_source'])
    names={r['security_id']:r for r in identity['rows']}
    groups=defaultdict(list)
    for r in a['transition_traces']:groups[r['entity_id']].append(r)
    first=next(k for k,v in groups.items() if len(v)>=3 and v[-1]['actual']['maturity']=='CONFIRMED')
    invalid=next(k for k,v in groups.items() if len(v)>=3 and v[-1]['actual']['validity']=='INVALIDATED')
    unknown=next(k for k,v in groups.items() if len(v)>=3 and all(r['actual']['validity']=='UNKNOWN' for r in v))
    descriptions=[(first,'未知前态至真实确认',
      '新增正式确认事实支持当前升级；更早会话缺必需判定输入，不能解释为当时已确认。',
      '技术反弹也可能形成同日正向条件；需要后续真实结构保持与失效条件区分，当前不保证持续。'),
      (invalid,'硬失效优先于正向场景',
      '既有 episode 的硬失效证据优先，退出不被当天正向标签覆盖。',
      '日线反弹可能改善短期场景，但不证明旧 episode 恢复；新入组必须满足后续合法状态条件。'),
      (unknown,'持续未知而非无资格',
      '现有已见事实可能偏弱，但必需输入未知，尚不足以作正式否定。',
      '部分条件也可能支持后续改善；缺源期间无法裁决，先补真实输入，不以 UNKNOWN=FALSE 排除。')]
    rows=[];text=['# 三个真实多会话递归案例\n\n来源为已有独立 oracle 的实际输入和逐行 expected/actual，不重算既有充分验收样本。均为 corrected replay，历史首次可用未证明；9/30→10/08 按交易会话递进。\n']
    for sid,title,h1,h2 in descriptions:
        label=names.get(sid,{}).get('source_security_key',sid)
        text.append(f'\n## {label}：{title}\n\n竞争解释一：{h1}\n\n竞争解释二：{h2}\n\n|真实日期|前态|新增 F/R|计数器变化|下一状态与理由|\n|---|---|---|---|---|\n')
        for r in groups[sid]:
            prior=r['prior_state'] or {};actual=r['actual'];facts=r['new_facts']
            counters={k:dict(prior=prior.get(k),next=actual.get(k)) for k in ('downgrade_count','expiry_count','market_age','exit_session_index')}
            rows.append(dict(r,identity=names.get(sid),competing_explanations=[h1,h2],counter_changes=counters))
            small={k:facts.get(k) for k in ('CONFIRMED','PREWATCH','core_price_damage','frozen_invalidation','risk','scenario')}
            text.append('|'+r['trade_date']+'|'+json.dumps({k:prior.get(k) for k in ('maturity','validity','tracking')})+'|'+json.dumps(small)+'|'+json.dumps(counters)+'|'+json.dumps({k:actual.get(k) for k in ('maturity','health','validity','tracking','final_eligibility','transition_reasons')})+'|\n')
        text.append('\n下一判别：后继真实会话的正式事实、失效和状态入口；未来未发生部分保持 WAIT_REAL_DAY。以上解释不涉及账户或资金行为。\n')
    write(D/'ALG_THREE_REAL_TRANSITION_CASES.json',dict(source_result=binding(OUT/'02_P0_ALG/P0_ALG_ORACLE_RESULT.json'),source_input=binding(OUT/'02_P0_ALG/P0_ALG_ORACLE_INPUT.json'),cases=rows,real_reentry='NOT_OBSERVED'))
    markdown(OUT/'02_P0_ALG/P0_ALG_TRANSITION_CASES_DEEPENED.md',''.join(text))
    print('real narrative rows',len(rows))

if __name__=='__main__':
    if '--prepare' in sys.argv:prepare()
    else:cases()
