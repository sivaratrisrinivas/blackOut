from blackout.workflow import BlackOutWorkflow, FakeMemoryAdapter


class RecordingMemoryAdapter(FakeMemoryAdapter):
    def __init__(self):
        self.recall_count = 0

    def recall_morning_after(self):
        self.recall_count += 1
        return super().recall_morning_after()


def test_morning_after_recall_returns_timeline_patterns_and_raw_evidence():
    workflow = BlackOutWorkflow(memory=FakeMemoryAdapter())

    result = workflow.morning_after_recall()

    assert result.late_night_window.label == "Most recent late-night window"
    assert len(result.timeline) == 1

    decision = result.timeline[0]
    assert decision.summary == "Bought a 3am espresso machine"
    assert decision.category == "purchase"
    assert decision.timestamp == "03:12"
    assert decision.people_or_vendors == ["BeanForge"]
    assert decision.amount == "$249"
    assert decision.regret_signals == ["high spend after midnight"]
    assert decision.evidence_excerpt.text == "03:12 - BeanForge receipt: espresso machine, $249"

    assert result.pattern_insights == [
        "Similar late-night purchases showed up in prior windows."
    ]
    assert result.raw_evidence == [
        "03:12 - BeanForge receipt: espresso machine, $249"
    ]


def test_morning_after_recall_uses_the_memory_lifecycle_seam():
    memory = RecordingMemoryAdapter()
    workflow = BlackOutWorkflow(memory=memory)

    workflow.morning_after_recall()

    assert memory.recall_count == 1
