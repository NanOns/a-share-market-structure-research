"""Current Python modules on an isolated port, with no DailyJobs worker."""
import json
import os
import sys
import threading
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from scripts.serve_core_product_qa_r1 import ReadOnlyJobs
from workbench_service.core_product_server_r1 import make_product_handler
from workbench_analysis.v4_14_replay_io import publish, ref


def main():
    for name in ('TMP','TEMP','TMPDIR'):
        os.environ[name] = 'G:/codex_tmp'
    heads = ['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json', 'data/v4/V4_DATA_ACCEPTED_HEAD.json']
    before = {p:ref(ROOT,p) for p in heads}
    # bind is the exact availability check. No connection to production jobs.
    server = ThreadingHTTPServer(('127.0.0.1',28768), make_product_handler(ROOT,ReadOnlyJobs()))
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    base = 'http://127.0.0.1:28768'
    try:
        with urllib.request.urlopen(base+'/api/v4/context',timeout=25) as response:
            context = json.load(response)
        token = context['context_token']
        with urllib.request.urlopen(base+'/api/v4/candidates/cohort?trade_date=2026-10-09&context_token='+token,timeout=25) as response:
            candidate = json.load(response)['candidate_research']
        with urllib.request.urlopen(base+'/api/operations/status',timeout=25) as response:
            jobs = json.load(response)
        assert candidate['formal_consumer_enabled'] is False and candidate['observed_count'] is None
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
    after = {p:ref(ROOT,p) for p in heads}
    assert before == after
    publish(ROOT,'docs/evidence/next_stage_after_audit_r1_20261010/B_ISOLATED_PYTHON_LOAD_HTTP.json',dict(
        contract_id='ISOLATED_NO_WORKER_PYTHON_HTTP_PREFLIGHT_R1', observed_at=datetime.now(timezone.utc).isoformat(),
        base=base, temporary_server_closed=True, daily_worker_started=False, jobs=jobs,
        code={p:ref(ROOT,p) for p in ['src/workbench_service/core_product_server_r1.py',
            'src/workbench_service/core_product_bff_r1.py','src/workbench_analysis/operational_daily_executor_v1.py',
            'src/workbench_analysis/next_t0_identity_preflight_v1.py']},
        candidate=candidate, before=before, after=after, protected_heads_unchanged=True,
        production_28765_restarted=False, formal_admission=False, acceptance='PASS_SCOPED_READ_ONLY_LOADING'))
    print(json.dumps(dict(port=28768,worker_started=False,temporary_server_closed=True,
        candidate_freeze_time=candidate.get('candidate_frozen_at'),heads_unchanged=True)))


if __name__ == '__main__':
    main()
