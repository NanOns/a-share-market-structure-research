from __future__ import annotations

from workbench_analysis.security_entity_identity import bao_source_entity, bse_alias_entity, stable_security_id


def test_source_symbol_is_not_security_id_and_identity_is_deterministic():
    first = bao_source_entity("SH", "sh.600000", "1999-11-10")
    second = bao_source_entity("SH", "sh.600000", "1999-11-10")
    assert first == second
    assert first["security_id"] != "SH.600000"
    assert str(first["security_id"]).startswith("SEC-")


def test_same_symbol_reused_on_new_listing_lifecycle_gets_new_identity():
    prior = stable_security_id("SH", "SH.600000", "1999-11-10")
    reused = stable_security_id("SH", "SH.600000", "2030-01-02")
    assert prior != reused


def test_official_bse_old_new_aliases_share_one_entity_identity():
    mapped = bse_alias_entity("830799", "920799", "2020-07-27")
    assert mapped["security_id"] != "BJ.830799"
    assert mapped["security_id"] == stable_security_id("BJ", "BJ.830799", "2020-07-27")
    assert mapped["old_symbol"] != mapped["new_symbol"]


def test_missing_listing_date_fails_closed():
    unresolved = bao_source_entity("SZ", "sz.000001", None)
    assert unresolved["security_id"] is None
    assert unresolved["identity_quality"] == "UNRESOLVED_LIST_DATE"
