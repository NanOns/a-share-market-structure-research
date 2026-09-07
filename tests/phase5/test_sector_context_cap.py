from candidates.research_priority import sector_points
def test_cap(row):row.update(effective_pattern='SECTOR_LEADER',primary_leader_pattern='REACCELERATION');assert sector_points(row)[0]==20
