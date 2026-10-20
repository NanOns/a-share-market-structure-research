-- Preserve independently sealed R2 projections that share context and date.
-- Their content digests are part of version identity; legacy hashed schemas
-- may legitimately contain different builds for the same head/date.
DROP TRIGGER IF EXISTS read_index_r2_immutable_guard ON v4.read_versions_r2;
DROP TRIGGER IF EXISTS read_index_r2_immutable_guard ON v4.read_items_r2;
DROP TRIGGER IF EXISTS read_index_r2_immutable_guard ON v4.read_responses_r2;
DROP TRIGGER IF EXISTS read_index_r2_truncate_guard ON v4.read_versions_r2;
DROP TRIGGER IF EXISTS read_index_r2_truncate_guard ON v4.read_items_r2;
DROP TRIGGER IF EXISTS read_index_r2_truncate_guard ON v4.read_responses_r2;
DROP TRIGGER IF EXISTS read_index_truncate_guard ON v4.read_versions_r2;
DROP TRIGGER IF EXISTS read_index_truncate_guard ON v4.read_items_r2;
DROP TRIGGER IF EXISTS read_index_truncate_guard ON v4.read_responses_r2;
ALTER TABLE v4.read_items_r2 DROP CONSTRAINT IF EXISTS read_items_r2_context_id_day_fkey;
ALTER TABLE v4.read_responses_r2 DROP CONSTRAINT IF EXISTS read_responses_r2_context_id_day_fkey;
ALTER TABLE v4.read_items_r2 ADD COLUMN IF NOT EXISTS digest text;
ALTER TABLE v4.read_responses_r2 ADD COLUMN IF NOT EXISTS digest text;

UPDATE v4.read_items_r2 i SET digest=v.digest
FROM v4.read_versions_r2 v
WHERE i.context_id=v.context_id AND i.day=v.day AND i.digest IS NULL;
UPDATE v4.read_responses_r2 i SET digest=v.digest
FROM v4.read_versions_r2 v
WHERE i.context_id=v.context_id AND i.day=v.day AND i.digest IS NULL;

ALTER TABLE v4.read_items_r2 ALTER COLUMN digest SET NOT NULL;
ALTER TABLE v4.read_responses_r2 ALTER COLUMN digest SET NOT NULL;
ALTER TABLE v4.read_versions_r2 DROP CONSTRAINT IF EXISTS read_versions_r2_context_id_day_key;
ALTER TABLE v4.read_versions_r2 DROP CONSTRAINT IF EXISTS read_versions_r2_pkey;
ALTER TABLE v4.read_items_r2 DROP CONSTRAINT IF EXISTS read_items_r2_pkey;
ALTER TABLE v4.read_responses_r2 DROP CONSTRAINT IF EXISTS read_responses_r2_pkey;
ALTER TABLE v4.read_versions_r2 ADD CONSTRAINT read_versions_r2_pkey PRIMARY KEY(context_id,day,digest);
ALTER TABLE v4.read_items_r2 ADD CONSTRAINT read_items_r2_pkey PRIMARY KEY(context_id,day,digest,domain,entity_id);
ALTER TABLE v4.read_responses_r2 ADD CONSTRAINT read_responses_r2_pkey PRIMARY KEY(context_id,day,digest,path);
ALTER TABLE v4.read_items_r2 ADD CONSTRAINT read_items_r2_version_fk FOREIGN KEY(context_id,day,digest)
  REFERENCES v4.read_versions_r2(context_id,day,digest);
ALTER TABLE v4.read_responses_r2 ADD CONSTRAINT read_responses_r2_version_fk FOREIGN KEY(context_id,day,digest)
  REFERENCES v4.read_versions_r2(context_id,day,digest);
CREATE INDEX IF NOT EXISTS read_items_r2_order ON v4.read_items_r2(context_id,day,digest,domain,entity_id);
