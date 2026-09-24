import pytest

from scripts.sync_latest_publication_to_postgres import validate_table_contract


def test_runtime_heads_are_postgres_projections_not_compute_source_tables():
    sources = {"publications", "publication_heads", "research_runs_v3_3", "research_candidates_v3_3"}
    targets = sources | {"research_bundle_heads", "analysis_snapshot_heads"}
    validate_table_contract(sources, targets, require_research_bundle=True)


def test_daily_v33_sync_fails_closed_when_bundle_tables_are_missing():
    sources = {"publications", "publication_heads"}
    targets = {"publications", "publication_heads", "research_bundle_heads", "analysis_snapshot_heads"}
    with pytest.raises(RuntimeError, match="required V3.3 bundle table missing"):
        validate_table_contract(sources, targets, require_research_bundle=True)


def test_runtime_projection_missing_in_postgres_fails_closed():
    sources = {"publications", "publication_heads"}
    targets = {"publications", "publication_heads", "analysis_snapshot_heads"}
    with pytest.raises(RuntimeError, match="required PostgreSQL table missing: research_bundle_heads"):
        validate_table_contract(sources, targets, require_research_bundle=False)
