CREATE TABLE IF NOT EXISTS v4.owner_versions_risk_r1(
 token text NOT NULL,T0 text NOT NULL,contract text NOT NULL,digest text NOT NULL,
 row_count integer NOT NULL,database_identity jsonb NOT NULL,sealed boolean NOT NULL DEFAULT false,
 PRIMARY KEY(token,T0));
CREATE TABLE IF NOT EXISTS v4.owner_payloads_risk_r1(
 token text NOT NULL,T0 text NOT NULL,payload jsonb NOT NULL,payload_sha256 text NOT NULL,
 PRIMARY KEY(token,T0),FOREIGN KEY(token,T0) REFERENCES v4.owner_versions_risk_r1(token,T0));
CREATE TABLE IF NOT EXISTS v4.owner_versions_priority_r1(
 token text NOT NULL,T0 text NOT NULL,contract text NOT NULL,digest text NOT NULL,
 row_count integer NOT NULL,database_identity jsonb NOT NULL,sealed boolean NOT NULL DEFAULT false,
 PRIMARY KEY(token,T0));
CREATE TABLE IF NOT EXISTS v4.owner_payloads_priority_r1(
 token text NOT NULL,T0 text NOT NULL,payload jsonb NOT NULL,payload_sha256 text NOT NULL,
 PRIMARY KEY(token,T0),FOREIGN KEY(token,T0) REFERENCES v4.owner_versions_priority_r1(token,T0));
CREATE TABLE IF NOT EXISTS v4.sector_lifecycle_owner_versions_r1(
 token text NOT NULL,T0 text NOT NULL,contract text NOT NULL,digest text NOT NULL,
 producer_sha256 text NOT NULL,parameter_digest text NOT NULL,input_digest text NOT NULL,
 row_count integer NOT NULL,database_identity jsonb NOT NULL,sealed boolean NOT NULL DEFAULT false,
 PRIMARY KEY(token,T0));
CREATE TABLE IF NOT EXISTS v4.sector_lifecycle_owner_rows_r1(
 token text NOT NULL,T0 text NOT NULL,sector_id text NOT NULL,payload jsonb NOT NULL,payload_sha256 text NOT NULL,
 PRIMARY KEY(token,T0,sector_id),FOREIGN KEY(token,T0) REFERENCES v4.sector_lifecycle_owner_versions_r1(token,T0));
CREATE TABLE IF NOT EXISTS v4.owner_schema_migration_map_r1(
 family text NOT NULL CHECK(family IN ('operational_risk','research_priority','sector_lifecycle')),
 source_schema text NOT NULL,token text NOT NULL,T0 text NOT NULL,digest text NOT NULL,
 contract text NOT NULL,row_count integer NOT NULL,verification jsonb NOT NULL,
 migrated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(family,source_schema,token,T0));
