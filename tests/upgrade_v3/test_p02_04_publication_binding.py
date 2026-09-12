from datetime import date

import pytest

from workbench_publish import OneClickPublisher, PublicationRequest, SimulatedCrash
from workbench_service.legacy_relation_import import LEGACY_SOURCE_SCOPE
from workbench_service.membership_resolver import VersionedMembershipResolver


def _publisher(root):
    return OneClickPublisher(root, bundle_verifier=lambda _: {"status": "PASS", "source_bundle_id": "bundle-1"})


def _request(model="model-1", trade_date=date(2026, 9, 11)):
    return PublicationRequest(
        trade_date,
        "bundle-1",
        model,
        "compute-1",
        memberships=(
            {"sector_id": "INDUSTRY:A", "sector_name": "行业A", "sector_type": "INDUSTRY", "security_id": "SH.600001"},
            {"sector_id": "INDUSTRY:A", "sector_name": "行业A", "sector_type": "INDUSTRY", "security_id": "SH.600002"},
        ),
    )


def test_publication_binds_relation_observation_and_reuses_stable_edges(tmp_path):
    publisher = _publisher(tmp_path)
    first = publisher.run(_request())
    second = publisher.run(_request("model-2"))
    assert first["status"] == second["status"] == "SUCCESS"

    from workbench_db.repository import WorkbenchRepository

    with WorkbenchRepository(tmp_path, publisher.database_path) as repository:
        connection = repository.connection
        bindings = connection.execute(
            "SELECT publication_id, source_scope, revision_no, attribute_version_id FROM relation_publication_bindings ORDER BY publication_id"
        ).fetchall()
        observations = connection.execute(
            "SELECT source_scope, revision_no, quality FROM relation_observations ORDER BY observation_id"
        ).fetchall()
        edges = connection.execute(
            "SELECT sector_id, security_id, from_revision, to_revision, source_kind FROM relation_edge_intervals"
        ).fetchall()

    assert [row[0] for row in bindings] == sorted([first["publication_id"], second["publication_id"]])
    assert all(row[1] == LEGACY_SOURCE_SCOPE and row[2] == 1 and row[3] for row in bindings)
    assert len(observations) == 2 and all(row[0] == LEGACY_SOURCE_SCOPE and row[1] == 1 and row[2] == "READY" for row in observations)
    assert len(edges) == 2 and all(row[2:] == (1, None, "DIRECT") for row in edges)


def test_relation_binding_is_atomic_with_publication_commit(tmp_path):
    publisher = _publisher(tmp_path)
    try:
        publisher.run(_request(), crash_at="before_commit")
    except SimulatedCrash:
        pass

    from workbench_db.repository import WorkbenchRepository

    with WorkbenchRepository(tmp_path, publisher.database_path) as repository:
        connection = repository.connection
        assert connection.execute("SELECT count(*) FROM publications").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM relation_publication_bindings").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM relation_observations").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM relation_edge_intervals").fetchone()[0] == 0


def test_same_members_on_new_trade_date_adds_observation_not_edges(tmp_path):
    publisher = _publisher(tmp_path)
    publisher.run(_request("model-1", date(2026, 9, 11)))
    publisher.run(_request("model-1", date(2026, 9, 12)))

    from workbench_db.repository import WorkbenchRepository

    with WorkbenchRepository(tmp_path, publisher.database_path) as repository:
        connection = repository.connection
        assert connection.execute("SELECT count(*) FROM relation_revisions").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM relation_edge_intervals").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM relation_observations").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM relation_publication_bindings").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM membership_entries").fetchone()[0] == 0


def test_publication_binding_refuses_ambiguous_source_namespace(tmp_path):
    publisher = _publisher(tmp_path)
    published = publisher.run(_request())
    publication_id = published["publication_id"]
    from workbench_db.repository import WorkbenchRepository

    with WorkbenchRepository(tmp_path, publisher.database_path) as repository:
        connection = repository.connection
        existing = connection.execute(
            "SELECT observation_id, revision_no, attribute_version_id, hierarchy_version FROM relation_publication_bindings WHERE publication_id=?",
            [publication_id],
        ).fetchone()
        connection.execute(
            "INSERT INTO relation_publication_bindings VALUES (?, ?, ?, ?, ?, ?)",
            [publication_id, "SOURCE-A:direct-members-v3-v1", existing[0], existing[1], existing[2], existing[3]],
        )
        connection.execute(
            "INSERT INTO relation_publication_bindings VALUES (?, ?, ?, ?, ?, ?)",
            [publication_id, "SOURCE-B:direct-members-v3-v1", existing[0], existing[1], existing[2], existing[3]],
        )
        with pytest.raises(KeyError, match="RELATION_PUBLICATION_SOURCE_SCOPE_REQUIRED"):
            VersionedMembershipResolver(connection).publication_binding(publication_id)
