from datetime import datetime

from blackout.workflow import BlackOutWorkflow, FakeMemoryAdapter


class RecordingMemoryAdapter(FakeMemoryAdapter):
    def __init__(self):
        super().__init__()
        self.recall_count = 0

    def recall_morning_after(self):
        self.recall_count += 1
        return super().recall_morning_after()


def test_morning_after_recall_reconstructs_seeded_evidence_as_a_decision_timeline():
    workflow = BlackOutWorkflow(memory=FakeMemoryAdapter())

    seed_result = workflow.load_seed_demo_dataset(
        current_time=datetime.fromisoformat("2026-07-04T09:30:00+05:30")
    )
    result = workflow.morning_after_recall()

    assert result.late_night_window == seed_result.most_recent_window
    assert [decision.timestamp for decision in result.timeline] == [
        "00:38",
        "01:46",
        "03:12",
        "04:21",
    ]
    assert [decision.category for decision in result.timeline] == [
        "note",
        "message",
        "purchase",
        "subscription",
    ]

    purchase = result.timeline[2]
    assert purchase.summary == "Bought espresso machine from BeanForge"
    assert purchase.source_type == "receipt"
    assert purchase.people_or_vendors == ["BeanForge"]
    assert purchase.amount == "$249"
    assert purchase.regret_signals == ["purchase after midnight", "amount over $100"]
    assert purchase.evidence_excerpt.text == (
        "03:12 - BeanForge receipt: espresso machine, $249."
    )

    message = result.timeline[1]
    assert message.people_or_vendors == ["Maya", "Rowan"]
    assert message.regret_signals == ["emotionally loaded message after midnight"]
    assert message.evidence_excerpt.text == (
        '01:46 - Text to Maya: "I am definitely not texting Rowan again. Unless?"'
    )

    assert result.raw_evidence == [
        '00:38 - Notes app: "Tomorrow me should absolutely build the espresso cart."',
        '01:46 - Text to Maya: "I am definitely not texting Rowan again. Unless?"',
        "03:12 - BeanForge receipt: espresso machine, $249.",
        '04:21 - Todoist: "Cancel trial subscription before it becomes a tiny monthly ghost."',
    ]


def test_morning_after_recall_surfaces_prior_pattern_insights_separate_from_raw_evidence():
    workflow = BlackOutWorkflow(memory=FakeMemoryAdapter())

    workflow.load_seed_demo_dataset(
        current_time=datetime.fromisoformat("2026-07-04T09:30:00+05:30")
    )
    result = workflow.morning_after_recall()

    assert result.pattern_insights

    insight = next(
        pattern
        for pattern in result.pattern_insights
        if pattern.current_decision.summary == "Bought espresso machine from BeanForge"
    )
    assert insight.status == "possible risk"
    assert insight.summary == (
        "BeanForge purchases appeared in this Late-Night Window and a prior one."
    )
    assert insight.current_decision.summary == "Bought espresso machine from BeanForge"
    assert len(insight.related_prior_decisions) == 1

    prior_decision = insight.related_prior_decisions[0]
    assert prior_decision.summary == "Bought premium grinder from BeanForge"
    assert prior_decision.timestamp == "02:58"
    assert prior_decision.amount == "$179"
    assert prior_decision.evidence_excerpt.text not in result.raw_evidence


def test_morning_after_recall_reconstructs_pasted_evidence_as_a_decision_timeline():
    workflow = BlackOutWorkflow(memory=FakeMemoryAdapter())

    remembered_window = workflow.remember_evidence(
        primary_evidence="""Late-Night Window: Pasted evidence
00:12 - ShopSwift receipt: novelty keyboard, $129.
01:05 - Text to Priya: "I can totally redesign the slides by breakfast."
""",
        current_time=datetime.fromisoformat("2026-07-04T09:30:00+05:30"),
    )
    result = workflow.morning_after_recall()

    assert result.late_night_window == remembered_window
    assert [decision.category for decision in result.timeline] == [
        "purchase",
        "message",
    ]

    purchase = result.timeline[0]
    assert purchase.summary == "Bought novelty keyboard from ShopSwift"
    assert purchase.source_type == "receipt"
    assert purchase.people_or_vendors == ["ShopSwift"]
    assert purchase.amount == "$129"
    assert purchase.evidence_excerpt.text == (
        "00:12 - ShopSwift receipt: novelty keyboard, $129."
    )

    message = result.timeline[1]
    assert message.summary == (
        "Texted Priya: I can totally redesign the slides by breakfast."
    )
    assert message.source_type == "message"
    assert message.people_or_vendors == ["Priya"]
    assert message.evidence_excerpt.text == (
        '01:05 - Text to Priya: "I can totally redesign the slides by breakfast."'
    )


def test_morning_after_recall_uses_the_memory_lifecycle_seam():
    memory = RecordingMemoryAdapter()
    workflow = BlackOutWorkflow(memory=memory)

    workflow.morning_after_recall()

    assert memory.recall_count == 1
