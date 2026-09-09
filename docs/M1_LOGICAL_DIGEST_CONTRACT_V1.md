# M1 Logical Digest Contract V1

Version: `m1-logical-digest-v1.1`.

The logical digest identifies normalized table content, not Parquet/CSV bytes. Source columns are retained in source order. Rows are ordered by the declared primary key and then by their canonical JSON representation. Values use explicit type tags: NULL, boolean, integer, finite float formatted with 17 significant digits, UTF-8 string, list, and object. Because database payloads use JSON, source date and datetime scalars normalize to ISO-8601 strings before hashing; this is the canonical JSON transport representation and prevents unrecoverable source-type guesses during database reconstruction. CSV empty fields normalize to NULL; non-empty CSV fields remain strings so migration does not silently reinterpret source precision. Object keys are sorted. NaN and infinities are rejected.

The SHA-256 input is UTF-8 canonical JSON containing contract version, ordered columns, primary key and canonical rows. File SHA-256 and logical SHA-256 are stored separately and must never be compared as equivalent identities.

For M1 acceptance, database payloads are reconstructed and digested with the same contract. Equality requires column order, row count, primary-key uniqueness and logical SHA-256 equality. A row-count-only comparison cannot pass.
