-- Disposable engineering rollback; never remove published evidence.
DROP TABLE v4.confirmation_candidate_events_r1;
DROP TABLE v4.confirmation_candidate_event_publications_r1;
DROP TABLE v4.confirmation_candidate_facts_r1;
DROP TABLE v4.confirmation_candidate_publications_r1;
DROP FUNCTION v4.confirmation_candidate_immutable_r1();
DROP FUNCTION v4.guard_confirmation_candidate_publication_r1();
DROP FUNCTION v4.guard_confirmation_candidate_result_r1();
DROP FUNCTION v4.guard_confirmation_candidate_complete_r1();
