from adjustment.engine import adjustment_history_changed


def test_adjustment_history_change_triggers_rebuild() -> None:
    assert adjustment_history_changed("before", "after")
    assert not adjustment_history_changed("same", "same")

