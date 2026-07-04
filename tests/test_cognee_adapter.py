import pytest

from blackout.cognee_adapter import (
    CogneeConfigurationError,
    RealCogneeMemoryAdapter,
    build_memory_adapter_from_env,
)
from blackout.workflow import FakeMemoryAdapter, LateNightWindow


class RecordingCogneeClient:
    def __init__(self):
        self.calls = []

    def add(self, data, dataset_name=None):
        self.calls.append(("add", data, dataset_name))

    def cognify(self, dataset_name=None):
        self.calls.append(("cognify", dataset_name))

    def search(self, query_text, query_type=None, datasets=None):
        self.calls.append(("search", query_text, query_type, datasets))
        return "Remembered context from Cognee"

    def improve(self, dataset_name=None):
        self.calls.append(("improve", dataset_name))

    def delete_dataset(self, dataset_name):
        self.calls.append(("delete_dataset", dataset_name))


def test_memory_adapter_defaults_to_fake_for_deterministic_local_runs(monkeypatch):
    monkeypatch.delenv("BLACKOUT_MEMORY_ADAPTER", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    adapter = build_memory_adapter_from_env()

    assert isinstance(adapter, FakeMemoryAdapter)


def test_memory_adapter_reports_missing_cognee_credentials_without_secret_values(
    monkeypatch,
):
    monkeypatch.setenv("BLACKOUT_MEMORY_ADAPTER", "cognee")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(CogneeConfigurationError) as error:
        build_memory_adapter_from_env()

    message = str(error.value)
    assert "LLM_API_KEY" in message
    assert "BLACKOUT_MEMORY_ADAPTER" in message
    assert "secret" not in message.lower()


def test_memory_adapter_can_choose_real_cognee_adapter_when_configured(monkeypatch):
    monkeypatch.setenv("BLACKOUT_MEMORY_ADAPTER", "cognee")
    monkeypatch.setenv("LLM_API_KEY", "not-shown")

    adapter = build_memory_adapter_from_env(cognee_client=RecordingCogneeClient())

    assert isinstance(adapter, RealCogneeMemoryAdapter)


def test_real_cognee_adapter_remembers_evidence_as_a_separable_late_night_window():
    cognee = RecordingCogneeClient()
    adapter = RealCogneeMemoryAdapter(cognee_client=cognee)
    window = LateNightWindow(
        label="Pasted late-night window",
        starts_at="2026-07-04T00:00:00+05:30",
        ends_at="2026-07-04T05:00:00+05:30",
        memory_key="late-night-window:2026-07-04",
    )

    adapter.remember_late_night_window(
        window=window,
        primary_demo_evidence="00:12 - ShopSwift receipt: novelty keyboard, $129.",
    )

    assert cognee.calls == [
        (
            "add",
            (
                "Late-Night Window: Pasted late-night window\n"
                "Starts at: 2026-07-04T00:00:00+05:30\n"
                "Ends at: 2026-07-04T05:00:00+05:30\n"
                "Memory key: late-night-window:2026-07-04\n"
                "Evidence:\n"
                "00:12 - ShopSwift receipt: novelty keyboard, $129."
            ),
            "blackout_late_night_window_2026_07_04",
        ),
        ("cognify", "blackout_late_night_window_2026_07_04"),
    ]


def test_real_cognee_adapter_recalls_morning_after_result_through_cognee_search():
    cognee = RecordingCogneeClient()
    adapter = RealCogneeMemoryAdapter(cognee_client=cognee)
    window = LateNightWindow(
        label="Pasted late-night window",
        starts_at="2026-07-04T00:00:00+05:30",
        ends_at="2026-07-04T05:00:00+05:30",
        memory_key="late-night-window:2026-07-04",
    )
    adapter.remember_late_night_window(
        window=window,
        primary_demo_evidence=(
            "00:12 - ShopSwift receipt: novelty keyboard, $129.\n"
            '01:05 - Text to Priya: "I can totally redesign the slides by breakfast."'
        ),
    )

    result = adapter.recall_morning_after()

    assert any(
        call[0] == "search" and "Morning-After Recall" in call[1]
        for call in cognee.calls
    )
    assert result.late_night_window == window
    assert [decision.summary for decision in result.timeline] == [
        "Bought novelty keyboard from ShopSwift",
        "Texted Priya: I can totally redesign the slides by breakfast.",
    ]


def test_real_cognee_adapter_answers_ask_your_memory_through_cognee_search():
    cognee = RecordingCogneeClient()
    adapter = RealCogneeMemoryAdapter(cognee_client=cognee)
    window = LateNightWindow(
        label="Pasted late-night window",
        starts_at="2026-07-04T00:00:00+05:30",
        ends_at="2026-07-04T05:00:00+05:30",
        memory_key="late-night-window:2026-07-04",
    )
    adapter.remember_late_night_window(
        window=window,
        primary_demo_evidence="00:12 - ShopSwift receipt: novelty keyboard, $129.",
    )

    answer = adapter.ask_memory("What did I buy after midnight?")

    assert any(
        call[0] == "search" and "What did I buy after midnight?" in call[1]
        for call in cognee.calls
    )
    assert answer.answer == "You bought novelty keyboard from ShopSwift at 00:12 for $129."
    assert answer.evidence == [
        "00:12 - ShopSwift receipt: novelty keyboard, $129.",
    ]


def test_real_cognee_adapter_improves_memory_from_feedback_label():
    cognee = RecordingCogneeClient()
    adapter = RealCogneeMemoryAdapter(cognee_client=cognee)
    window = LateNightWindow(
        label="Pasted late-night window",
        starts_at="2026-07-04T00:00:00+05:30",
        ends_at="2026-07-04T05:00:00+05:30",
        memory_key="late-night-window:2026-07-04",
    )
    adapter.remember_late_night_window(
        window=window,
        primary_demo_evidence="00:12 - ShopSwift receipt: novelty keyboard, $129.",
    )
    decision = adapter.recall_morning_after().timeline[0]

    adapter.improve_decision_memory(decision, "Regret")
    updated_result = adapter.recall_morning_after()

    assert ("improve", "blackout_late_night_window_2026_07_04") in cognee.calls
    assert updated_result.timeline[0].feedback_label == "Regret"


def test_real_cognee_adapter_forgets_late_night_window_dataset():
    cognee = RecordingCogneeClient()
    adapter = RealCogneeMemoryAdapter(cognee_client=cognee)
    window = LateNightWindow(
        label="Pasted late-night window",
        starts_at="2026-07-04T00:00:00+05:30",
        ends_at="2026-07-04T05:00:00+05:30",
        memory_key="late-night-window:2026-07-04",
    )
    adapter.remember_late_night_window(
        window=window,
        primary_demo_evidence="00:12 - ShopSwift receipt: novelty keyboard, $129.",
    )

    adapter.forget_late_night_window(window)
    result = adapter.recall_morning_after()

    assert ("delete_dataset", "blackout_late_night_window_2026_07_04") in cognee.calls
    assert result.timeline == []
