from datetime import datetime

from blackout.workflow import BlackOutWorkflow, FakeMemoryAdapter


def test_seed_demo_mode_loads_three_separable_late_night_windows():
    memory = FakeMemoryAdapter()
    workflow = BlackOutWorkflow(memory=memory)

    result = workflow.load_seed_demo_dataset(
        current_time=datetime.fromisoformat("2026-07-04T09:30:00+05:30")
    )

    assert result.loaded_window_count == 3
    assert result.most_recent_window.label == "Most recent late-night window"
    assert result.most_recent_window.starts_at == "2026-07-04T00:00:00+05:30"
    assert result.most_recent_window.ends_at == "2026-07-04T05:00:00+05:30"

    remembered_windows = [call.window for call in memory.remember_calls]
    assert len(remembered_windows) == 3
    assert [window.label for window in remembered_windows] == [
        "Most recent late-night window",
        "Prior late-night window: impulse purchase pattern",
        "Prior late-night window: emotional message pattern",
    ]
    assert len({window.memory_key for window in remembered_windows}) == 3

    remembered_evidence = [call.primary_demo_evidence for call in memory.remember_calls]
    assert all("Late-Night Window:" in evidence for evidence in remembered_evidence)
    assert any("BeanForge" in evidence for evidence in remembered_evidence)


def test_seed_demo_mode_uses_yesterday_when_current_window_is_not_complete():
    workflow = BlackOutWorkflow(memory=FakeMemoryAdapter())

    result = workflow.load_seed_demo_dataset(
        current_time=datetime.fromisoformat("2026-07-04T02:15:00+05:30")
    )

    assert result.most_recent_window.starts_at == "2026-07-03T00:00:00+05:30"
    assert result.most_recent_window.ends_at == "2026-07-03T05:00:00+05:30"
