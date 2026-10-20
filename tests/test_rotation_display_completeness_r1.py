from workbench_analysis.operational_successor_v1 import rotation_display_completeness


def test_rotation_display_completeness_is_bound_to_candidate_sector_owner():
    sectors = [{'sector_id': 'INDUSTRY:1'}, {'sector_id': 'THEME:2'}]
    rotations = [{'sector_id': 'INDUSTRY:1'}, {'sector_id': 'THEME:2'}]
    result = rotation_display_completeness(rotations, sectors,
        rotation_owner_bound=True, sector_owner_bound=True)
    assert result == dict(complete=True, expected_total=2, actual_total=2,
        covered_total=2, missing_total=0, unexpected_total=0, duplicate_total=0)


def test_rotation_display_completeness_rejects_missing_duplicate_and_unexpected_rows():
    sectors = [{'sector_id': 'INDUSTRY:1'}, {'sector_id': 'THEME:2'}]
    cases = [
        [{'sector_id': 'INDUSTRY:1'}],
        [{'sector_id': 'INDUSTRY:1'}, {'sector_id': 'INDUSTRY:1'}],
        [{'sector_id': 'INDUSTRY:1'}, {'sector_id': 'THEME:3'}],
        [{'sector_id': 'INDUSTRY:1'}, {'sector_id': 'THEME:2'}],
    ]
    for index, rows in enumerate(cases):
        result = rotation_display_completeness(rows, sectors,
            rotation_owner_bound=True, sector_owner_bound=index != 3)
        assert result['complete'] is False


def test_rotation_display_completeness_requires_owner_bindings():
    sectors = [{'sector_id': 'INDUSTRY:1'}]
    rows = [{'sector_id': 'INDUSTRY:1'}]
    assert not rotation_display_completeness(rows, sectors,
        rotation_owner_bound=False, sector_owner_bound=True)['complete']
    assert not rotation_display_completeness(rows, sectors,
        rotation_owner_bound=True, sector_owner_bound=False)['complete']
