from datetime import date
import pytest

from workbench_publish import OneClickPublisher, PublicationRequest, SimulatedCrash

def publisher(root):
    return OneClickPublisher(root,bundle_verifier=lambda _:{"status":"PASS","source_bundle_id":"bundle-1"})


def request():
    return PublicationRequest(date(2026, 9, 7), "bundle-1", "model-1", "compute-1",
        stocks=({"security_id":"SH.600001", "security_name":"测试"},),
        observations=({"observation_id":"obs-1", "security_id":"SH.600001"},),
        outcomes=({"observation_id":"obs-1", "horizon":5, "target_revision":1, "status":"OBSERVED"},))


def counts(pub):
    from workbench_db.repository import WorkbenchRepository
    with WorkbenchRepository(pub.root, pub.database_path) as repo:
        c=repo.connection
        return {t:c.execute(f"select count(*) from {t}").fetchone()[0] for t in ("publications","publication_heads","stock_daily","observations","outcomes")}


def test_crash_before_commit_has_no_half_publication_and_retry_is_clean(tmp_path):
    pub=publisher(tmp_path)
    with pytest.raises(SimulatedCrash): pub.run(request(), crash_at="before_commit")
    assert counts(pub)=={"publications":0,"publication_heads":0,"stock_daily":0,"observations":0,"outcomes":0}
    result=pub.run(request())
    assert result["status"]=="SUCCESS"
    assert counts(pub)=={"publications":1,"publication_heads":1,"stock_daily":1,"observations":1,"outcomes":1}


def test_crash_after_commit_recovers_without_duplicate_observation(tmp_path):
    pub=publisher(tmp_path)
    with pytest.raises(SimulatedCrash): pub.run(request(), crash_at="after_commit")
    before=counts(pub)
    result=pub.run(request())
    assert result["recovered"] is True and counts(pub)==before


def test_same_day_same_identity_is_idempotent(tmp_path):
    pub=publisher(tmp_path)
    first=pub.run(request()); second=pub.run(request())
    assert first["publication_id"]==second["publication_id"]
    assert counts(pub)["observations"]==1


def test_same_day_different_model_creates_audited_revision(tmp_path):
    pub=publisher(tmp_path); pub.run(request())
    changed=PublicationRequest(date(2026,9,7),"bundle-1","model-2","compute-1")
    result=pub.run(changed)
    from workbench_db.repository import WorkbenchRepository
    with WorkbenchRepository(tmp_path,pub.database_path) as repo:
        rows=repo.connection.execute("select revision,publication_id from publications order by revision").fetchall()
        head=repo.connection.execute("select publication_id from publication_heads").fetchone()[0]
    assert [x[0] for x in rows]==[1,2] and head==result["publication_id"]


def test_invalid_compute_result_fails_before_publication(tmp_path):
    pub=publisher(tmp_path)
    bad=lambda r: PublicationRequest(r.trade_date,r.source_bundle_id,"changed",r.computation_contract_id)
    with pytest.raises(ValueError,match="COMPUTE_IDENTITY_CHANGED"): pub.run(request(),bad)
    assert counts(pub)["publications"]==0

def test_missing_bundle_and_dangling_outcome_are_blocked(tmp_path):
    with pytest.raises((ValueError,FileNotFoundError)): OneClickPublisher(tmp_path).run(request())
    bad=PublicationRequest(date(2026,9,7),"bundle-1","model-1","compute-1",outcomes=({"observation_id":"missing","horizon":5,"target_revision":1},))
    with pytest.raises(ValueError,match="OUTCOME_OBSERVATION_MISSING"): publisher(tmp_path).run(bad)


def test_background_submit_returns_job_and_finishes(tmp_path):
    pub=publisher(tmp_path)
    job_id=pub.submit(request())
    assert job_id.startswith("job-")
    assert pub.wait(job_id)["status"]=="SUCCESS"

def test_restart_recovers_persisted_request_and_creates_new_attempt(tmp_path):
    pub=publisher(tmp_path)
    with pytest.raises(SimulatedCrash): pub.run(request(),crash_at="before_commit")
    recovered=publisher(tmp_path).recover_interrupted()
    assert recovered[0]["status"]=="SUCCESS"
    from workbench_db.repository import WorkbenchRepository
    with WorkbenchRepository(tmp_path,pub.database_path) as repo:
        assert repo.connection.execute("select count(*) from job_attempts").fetchone()[0]==2

def test_all_workbench_result_groups_commit_together(tmp_path):
    pub=publisher(tmp_path)
    r=PublicationRequest(date(2026,9,7),"bundle-1","model-all","compute-1",
      stocks=({"security_id":"SH.600001"},),sectors=({"sector_id":"concept:G1"},),candidates=({"security_id":"SH.600001"},),
      structures=({"queue_name":"STEADY","security_id":"SH.600001"},),queue_memberships=({"queue_name":"STEADY_QUEUE","security_id":"SH.600001","queue_tier":"CORE"},),
      unified_board=({"security_id":"SH.600001"},),queue_rankings=({"security_id":"SH.600001"},),observations=({"observation_id":"obs-all"},),outcomes=({"observation_id":"obs-all","horizon":5,"target_revision":1},))
    pub.run(r)
    from workbench_db.repository import WorkbenchRepository
    with WorkbenchRepository(tmp_path,pub.database_path) as repo:
      for table in ("stock_daily","sector_daily","candidate_daily","structure_details","queue_memberships","unified_board","queue_rankings","observations","outcomes"):
        assert repo.connection.execute(f"select count(*) from {table}").fetchone()[0]==1

def test_membership_snapshot_requires_content_hash_not_only_row_count(tmp_path):
    pub=publisher(tmp_path)
    first=PublicationRequest(date(2026,9,7),"bundle-1","model-1","compute-1",memberships=({"sector_id":"concept:A","security_id":"SH.600001"},))
    second=PublicationRequest(date(2026,9,7),"bundle-1","model-2","compute-1",memberships=({"sector_id":"concept:B","security_id":"SH.600001"},))
    pub.run(first); pub.run(second)
    from workbench_db.repository import WorkbenchRepository
    with WorkbenchRepository(tmp_path,pub.database_path) as repo:
        snapshots=repo.connection.execute("select membership_snapshot_id from publication_memberships order by publication_id").fetchall()
    assert len(set(snapshots))==2

def test_conflicting_outcome_payload_is_blocked(tmp_path):
    pub=publisher(tmp_path);pub.run(request())
    changed=PublicationRequest(date(2026,9,7),"bundle-1","model-2","compute-1",outcomes=({"observation_id":"obs-1","horizon":5,"target_revision":1,"status":"CHANGED"},))
    with pytest.raises(ValueError,match="OUTCOME_IDENTITY_CONFLICT"):
        pub.run(changed)

def test_repeated_submit_does_not_start_a_second_running_job(tmp_path):
    pub=publisher(tmp_path)
    job=pub.submit(request())
    assert pub.submit(request())==job

def test_new_publication_observation_ids_are_distinct_from_historical_outcome_binding(tmp_path):
    from workbench_publish.orchestrator import _observation_row_id
    row={"security_id":"SH.600001"}
    historic=_observation_row_id("signal-1",row)
    today=_observation_row_id("signal-1",row,"m4-new-publication")
    assert historic != today
