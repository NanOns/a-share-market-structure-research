"""FEP source-discovery check that never opens an isolated or writable database."""

from pathlib import Path

from workbench_analysis.fep_e5.trusted_authority import resolve_current_sources


def test_current_source_discovery_fails_closed_without_formal_owner():
    root = Path(__file__).resolve().parents[2]
    result = resolve_current_sources(root)

    assert result["production_authorized"] is False
    assert result["formal_owner"] is None
    assert "FORMAL_PRODUCTION_DB_OWNER_NOT_ADMITTED" in result["errors"]
