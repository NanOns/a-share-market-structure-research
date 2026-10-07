"""Read-only independent archive trace for the immutable prior source incident."""
import hashlib
import json
import zipfile
from pathlib import Path
from scripts.full_chain_repair_io import ROOT, binding, write
from scripts.forward_final_bootstrap import P


def build():
    old = 'reports/forward_r2_remainder_consolidated_20261007/TDX_INPUT_WRITE_INCIDENT.json'
    incident = json.loads((ROOT / old).read_bytes())
    archives = sorted((ROOT / 'data/v4/source_snapshots').rglob('*.zip'))
    rows = []
    for affected in incident['affected_unique_TDX_files']:
        name = Path(affected['path']).name
        matches = []
        for archive in archives:
            with zipfile.ZipFile(archive) as source:
                for item in source.infolist():
                    if Path(item.filename).name.lower() == name.lower():
                        digest = hashlib.sha256()
                        with source.open(item) as stream:
                            while block := stream.read(1024 * 1024):
                                digest.update(block)
                        matches.append(dict(archive=archive.relative_to(ROOT).as_posix(), member=item.filename,
                                            bytes=item.file_size, sha256=digest.hexdigest(),
                                            matches_post_incident_content=digest.hexdigest() == affected['sha256']))
        rows.append(dict(path=affected['path'], post_incident_sha256=affected['sha256'], independent_archive_members=matches,
                         status='INDEPENDENT_ARCHIVE_CONTENT_MATCH' if any(r['matches_post_incident_content'] for r in matches)
                         else 'PRE_INCIDENT_CONTENT_NOT_INDEPENDENTLY_VERIFIABLE',
                         pre_incident_mtime_recoverable=False))
    write(P + 'TDX_PRE_INCIDENT_CONTENT_TRACE.json', dict(prior_incident=binding(old),
        prior_write_calls=5, prior_unique_files=4, prior_TDX_ZERO_WRITE=False,
        search_scope='Existing accepted source ZIP archives only; user confirmed no other backup directories',
        rows=rows, source_bytes_or_metadata_restored=False, prior_incident_erased=False))


if __name__ == '__main__':
    build()
