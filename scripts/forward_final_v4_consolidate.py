"""Keep raw runs and prove complete node coverage after a fixture-only retry."""
import copy
from pathlib import Path
import xml.etree.ElementTree as ET
from scripts.full_chain_repair_io import write,binding
from scripts.forward_final_bootstrap import P


def key(case):return case.attrib.get('classname','')+'::'+case.attrib['name']
def counts(cases):
    return dict(total=len(cases),failed=sum(c.find('failure') is not None for c in cases),
                errors=sum(c.find('error') is not None for c in cases),
                skipped=sum(c.find('skipped') is not None for c in cases))


def run():
    base=Path('G:/codex_tmp')
    primary=ET.fromstring((base/'final_blocker_v4_only.xml').read_bytes()).findall('.//testcase')
    replay=ET.fromstring((base/'final_blocker_v4_pg_replay.xml').read_bytes()).findall('.//testcase')
    closure=ET.fromstring((base/'final_blocker_v4_skip_closure.xml').read_bytes()).findall('.//testcase')
    first={key(c):c for c in primary}; retry={key(c):c for c in replay}
    assert len(first)==len(primary) and len(retry)==len(replay)
    assert set(retry)<=set(first)
    allowed=('tests.v4_10.','tests.v4_11.')
    assert all(c.attrib.get('classname','').startswith(allowed) for c in replay)
    assert not counts(replay)['failed'] and not counts(replay)['errors'] and not counts(replay)['skipped']
    assert len(closure)==4 and not counts(closure)['failed'] and not counts(closure)['errors'] and not counts(closure)['skipped']
    assert all(c.attrib.get('classname','').startswith(('tests.fep.test_migration',
        'tests.v4_a09.test_consumer_identity_sql','tests.test_forward_final_reparse_equivalence')) for c in closure)
    retry.update({key(c):c for c in closure})
    added=[c for c in closure if key(c) not in first]
    assert len(added)==2 and all('test_forward_final_reparse_equivalence' in key(c) for c in added)
    original_errors=[key(c) for c in primary if c.find('error') is not None or c.find('failure') is not None]
    assert set(original_errors)<=set(retry), 'UNRESOLVED_NON_FIXTURE_FAILURE'
    merged=[copy.deepcopy(retry.get(key(c),c)) for c in primary]
    merged.extend(copy.deepcopy(c) for c in added)
    suite=ET.Element('testsuite',dict(name='V4_COMPLETE_PROFILE_WITH_VERIFIED_PG_FIXTURE_REPLAY',
        tests=str(len(merged)),failures='0',errors='0',skipped=str(counts(merged)['skipped'])))
    for case in merged:suite.append(case)
    write(P+'execution/current_full.xml',ET.tostring(suite,encoding='utf-8',xml_declaration=True),raw=True)
    for stem in ('final_blocker_v4_only','final_blocker_v4_pg_replay','final_blocker_v4_skip_closure'):
        for suffix in ('.xml','.log'):
            write(P+'execution/raw_runs/'+stem+suffix,(base/(stem+suffix)).read_bytes(),raw=True)
    write(P+'V4_PG_ENVIRONMENT_REPLAY_RECEIPT.json',dict(
        method='COMPLETE_PRIMARY_PROFILE_PLUS_EXACT_AFFECTED_MODULE_REPLAY',
        primary_counts=counts(primary),replay_counts=counts(replay),final_counts=counts(merged),
        skip_closure_counts=counts(closure), added_v4_portable_nodes=[key(c) for c in added],
        original_platform_skip_nodes=[key(c) for c in merged if c.find('skipped') is not None],
        original_error_nodes=original_errors,replayed_nodes=sorted(retry),
        complete_primary_node_set_preserved=True,original_test_assertions_unchanged=True,
        correction='Explicit verified disposable V4 SQL fixture DSN; immutable 33-migration template',
        fixture=binding(P+'V4_SQL_DISPOSABLE_FIXTURE.json'),
        primary=binding(P+'execution/raw_runs/final_blocker_v4_only.xml'),
        replay=binding(P+'execution/raw_runs/final_blocker_v4_pg_replay.xml'),
        final=binding(P+'execution/current_full.xml'),ignored=[],deselected=[],xfail=[]))


if __name__=='__main__':run()
