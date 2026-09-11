from pathlib import Path


ROOT = Path(__file__).parents[2]
STATIC = ROOT / "src" / "workbench_service" / "static" / "v2"


def test_evidence_is_a_static_modal_section_not_a_table_expansion():
    app = (STATIC / "app.js").read_text(encoding="utf-8")

    assert "function evidenceSection(title, body)" in app
    assert "function evidenceDetails" not in app
    assert "document.createElement('details')" not in app
    assert "querySelector('summary')" not in app
    assert "heading.textContent = title" in app
    assert "innerHTML" not in app


def test_modal_boundaries_and_focus_contract_remain_explicit():
    modal = (STATIC / "modal.js").read_text(encoding="utf-8")
    table = (STATIC / "table.js").read_text(encoding="utf-8")
    css = (STATIC / "p01-03.css").read_text(encoding="utf-8")

    assert "setAttribute('role','dialog')" in modal
    assert "lastFocus.focus();" in modal
    assert "event.key==='Escape'" in modal
    assert "event.target===active" in modal
    assert "button.type='button'" in table
    assert "href" not in table
    assert "width: min(960px, 100%);" in css
    assert "max-height: 85vh;" in css
    assert ".evidence-section" in css
    assert "p01-03.css" in (STATIC / "index.html").read_text(encoding="utf-8")


def test_modal_async_paths_reject_stale_responses():
    app = (STATIC / "app.js").read_text(encoding="utf-8")
    api = (STATIC / "api.js").read_text(encoding="utf-8")

    assert "function beginModalRequest()" in app
    assert "function modalRequestActive(token)" in app
    assert app.count("var token = beginModalRequest();") == 4
    assert app.count("if (!modalRequestActive(token)) return;") >= 4
    assert "marketDayDetail:function(params,options)" in api
    assert "mainlineEvidence:function(params,options)" in api
    assert "sectorTimeline:function(params,options)" in api
    assert "sectorMembersHistory:function(params,options)" in api
    assert "sectorLeaderHistory:function(params,options)" in api
