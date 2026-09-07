from common.input_snapshot import archive_source_revision,next_source_revision_id


def test_same_cutoff_source_revisions_are_append_only(tmp_path,manifest_factory):
    first_id=next_source_revision_id(tmp_path,'20260903','source-a')
    first=manifest_factory('run-1',first_id,'source-a')
    one=archive_source_revision(tmp_path,first,release_id='release-1')
    second_id=next_source_revision_id(tmp_path,'20260903','source-b')
    second=manifest_factory('run-2',second_id,'source-b')
    two=archive_source_revision(tmp_path,second,release_id='release-2',changed_source_components=['gbbq'])
    assert first_id==1 and second_id==2 and one['created'] and two['created']
    assert (tmp_path/'reports/revisions/20260903/revision-000001/REVISION_RECORD.json').exists()
    assert (tmp_path/'reports/revisions/20260903/revision-000002/REVISION_RECORD.json').exists()
    assert next_source_revision_id(tmp_path,'20260903','source-a')==1
