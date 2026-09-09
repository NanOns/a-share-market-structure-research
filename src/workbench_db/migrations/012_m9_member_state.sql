-- M9-02 strong-member state and point-in-time membership changes.
CREATE TABLE sector_member_state_daily (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    sector_id VARCHAR NOT NULL,
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    member_present BOOLEAN NOT NULL,
    member_rank DOUBLE,
    rank_valid_count BIGINT NOT NULL,
    member_percentile DOUBLE,
    strong_state BOOLEAN,
    strong_predicates JSON NOT NULL,
    structure_hit BOOLEAN,
    high_hit BOOLEAN,
    member_change_kind VARCHAR,
    strength_change_kind VARCHAR,
    previous_rank DOUBLE,
    rank_delta DOUBLE,
    queue_refs JSON NOT NULL,
    high_refs JSON NOT NULL,
    history_basis VARCHAR NOT NULL,
    contract_id VARCHAR NOT NULL,
    PRIMARY KEY (slice_id, sector_id, security_id, trade_date)
);
CREATE INDEX sector_member_state_daily_date_idx ON sector_member_state_daily (slice_id, trade_date, sector_id, security_id);

CREATE TABLE sector_membership_changes (
    slice_id VARCHAR NOT NULL REFERENCES analysis_slices(slice_id),
    sector_id VARCHAR NOT NULL,
    security_id VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    change_type VARCHAR NOT NULL,
    basis_version VARCHAR NOT NULL,
    reason VARCHAR NOT NULL,
    PRIMARY KEY (slice_id, sector_id, security_id, trade_date, change_type, basis_version)
);
CREATE INDEX sector_membership_changes_date_idx ON sector_membership_changes (slice_id, trade_date, sector_id, security_id);
