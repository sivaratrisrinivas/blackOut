import pytest
from urllib.error import HTTPError

from blackout.cognee_adapter import (
    CogneeConfigurationError,
    CogneeHttpClient,
    RealCogneeMemoryAdapter,
    _record_document,
    _records_from_search_result,
    build_memory_adapter_from_env,
)
from blackout.workflow import FakeMemoryAdapter, LateNightWindow


class RecordingCogneeClient:
    def __init__(self):
        self.calls = []
        self.data_by_dataset = {}
        self.deleted_datasets = set()

    def add(self, data, dataset_name=None):
        self.calls.append(("add", data, dataset_name))
        self.data_by_dataset.setdefault(dataset_name, []).append(data)

    def cognify(self, dataset_name=None):
        self.calls.append(("cognify", dataset_name))

    def search(self, query_text, query_type=None, datasets=None):
        self.calls.append(("search", query_text, query_type, datasets))
        if datasets is None:
            selected_datasets = [
                dataset_name
                for dataset_name in self.data_by_dataset
                if dataset_name not in self.deleted_datasets
            ]
        else:
            selected_datasets = [
                dataset_name
                for dataset_name in datasets
                if dataset_name not in self.deleted_datasets
            ]
        return "\n".join(
            data
            for dataset_name in selected_datasets
            for data in self.data_by_dataset.get(dataset_name, [])
        )

    def improve(self, dataset_name=None):
        self.calls.append(("improve", dataset_name))

    def delete_dataset(self, dataset_name):
        self.calls.append(("delete_dataset", dataset_name))
        self.deleted_datasets.add(dataset_name)


def test_memory_adapter_defaults_to_cognee_and_reports_missing_credentials(monkeypatch):
    monkeypatch.delenv("BLACKOUT_MEMORY_ADAPTER", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("COGNEE_BASE_URL", raising=False)
    monkeypatch.delenv("COGNEE_API_KEY", raising=False)

    with pytest.raises(CogneeConfigurationError) as error:
        build_memory_adapter_from_env()

    message = str(error.value)
    assert "LLM_API_KEY" in message
    assert "COGNEE_BASE_URL" in message
    assert "COGNEE_API_KEY" in message
    assert "secret" not in message.lower()


def test_memory_adapter_uses_fake_when_explicitly_configured(monkeypatch):
    monkeypatch.setenv("BLACKOUT_MEMORY_ADAPTER", "fake")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("COGNEE_BASE_URL", raising=False)
    monkeypatch.delenv("COGNEE_API_KEY", raising=False)

    adapter = build_memory_adapter_from_env()

    assert isinstance(adapter, FakeMemoryAdapter)


def test_memory_adapter_reports_missing_cognee_credentials_without_secret_values(
    monkeypatch,
):
    monkeypatch.setenv("BLACKOUT_MEMORY_ADAPTER", "cognee")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("COGNEE_BASE_URL", raising=False)
    monkeypatch.delenv("COGNEE_API_KEY", raising=False)

    with pytest.raises(CogneeConfigurationError) as error:
        build_memory_adapter_from_env()

    message = str(error.value)
    assert "LLM_API_KEY" in message
    assert "COGNEE_BASE_URL" in message
    assert "COGNEE_API_KEY" in message
    assert "BLACKOUT_MEMORY_ADAPTER" in message
    assert "secret" not in message.lower()


def test_memory_adapter_can_choose_real_cognee_adapter_when_configured(monkeypatch):
    monkeypatch.setenv("BLACKOUT_MEMORY_ADAPTER", "cognee")
    monkeypatch.setenv("LLM_API_KEY", "not-shown")
    monkeypatch.setenv("COGNEE_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("COGNEE_API_KEY", "not-shown")

    adapter = build_memory_adapter_from_env(cognee_client=RecordingCogneeClient())

    assert isinstance(adapter, RealCogneeMemoryAdapter)


def test_memory_adapter_uses_cognee_cloud_http_client_when_configured(monkeypatch):
    monkeypatch.setenv("BLACKOUT_MEMORY_ADAPTER", "cognee")
    monkeypatch.setenv("LLM_API_KEY", "not-shown")
    monkeypatch.setenv("COGNEE_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("COGNEE_API_KEY", "not-shown")

    adapter = build_memory_adapter_from_env()

    assert isinstance(adapter._cognee, CogneeHttpClient)


def test_memory_adapter_can_load_cognee_config_from_bashrc_exports(
    monkeypatch, tmp_path
):
    bashrc = tmp_path / ".bashrc"
    bashrc.write_text(
        "\n".join(
            [
                'export COGNEE_BASE_URL="https://example.invalid"',
                'export COGNEE_API_KEY="not-shown"',
                'export LLM_API_KEY="not-shown"',
            ]
        )
    )
    monkeypatch.setenv("BLACKOUT_MEMORY_ADAPTER", "cognee")
    monkeypatch.delenv("COGNEE_BASE_URL", raising=False)
    monkeypatch.delenv("COGNEE_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr("blackout.cognee_adapter.Path.home", lambda: tmp_path)

    adapter = build_memory_adapter_from_env(
        cognee_client=RecordingCogneeClient(),
        load_shell_exports=True,
    )

    assert isinstance(adapter, RealCogneeMemoryAdapter)


def test_cognee_http_client_calls_cloud_endpoints_without_printing_secrets():
    requests = []

    class Response:
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return b'{"ok": true}'

    def urlopen(request, timeout):
        requests.append(request)
        return Response()

    client = CogneeHttpClient(
        base_url="https://example.invalid",
        api_key="not-shown",
        urlopen=urlopen,
    )

    client.add("remember this", dataset_name="blackout_window")
    client.cognify(dataset_name="blackout_window")
    client.search("find this", query_type="GRAPH_COMPLETION", datasets=["blackout"])
    client.improve(dataset_name="blackout_window")
    client.delete_dataset("blackout_window")

    assert [request.full_url for request in requests] == [
        "https://example.invalid/api/v1/add",
        "https://example.invalid/api/v1/cognify",
        "https://example.invalid/api/v1/search",
        "https://example.invalid/api/v1/memify",
        "https://example.invalid/api/v1/forget",
    ]
    assert all(request.headers["X-api-key"] == "not-shown" for request in requests)
    assert b'filename="blackout-memory.txt"' in requests[0].data


def test_cognee_http_client_reads_raw_dataset_data_by_name():
    class Response:
        def __init__(self, body, content_type="application/json"):
            self._body = body
            self.headers = {"Content-Type": content_type}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return self._body

        def close(self):
            return None

    def urlopen(request, timeout):
        if request.full_url == "https://example.invalid/api/v1/datasets":
            return Response(b'[{"id": "dataset-1", "name": "blackout_index"}]')
        if request.full_url == "https://example.invalid/api/v1/datasets/dataset-1/data":
            return Response(b'[{"id": "data-1"}]')
        if (
            request.full_url
            == "https://example.invalid/api/v1/datasets/dataset-1/data/data-1/raw"
        ):
            return Response(b"raw BlackOut record", content_type="text/plain")
        raise AssertionError(request.full_url)

    client = CogneeHttpClient(
        base_url="https://example.invalid",
        api_key="not-shown",
        urlopen=urlopen,
    )

    assert client.raw_data("blackout_index") == ["raw BlackOut record"]


def test_cognee_http_client_tolerates_missing_memify_endpoint():
    class Response:
        def __init__(self, body=b"{}", status=200):
            self._body = body
            self.status = status
            self.headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return self._body

        def close(self):
            return None

    def urlopen(request, timeout):
        if request.full_url == "https://example.invalid/api/v1/memify":
            raise HTTPError(
                request.full_url,
                404,
                "Not Found",
                {},
                Response(b'{"detail":"Not Found"}', status=404),
            )
        raise AssertionError(request.full_url)

    client = CogneeHttpClient(
        base_url="https://example.invalid",
        api_key="not-shown",
        urlopen=urlopen,
    )

    assert client.improve(dataset_name="blackout_window") is None


def test_record_parser_reads_nested_cognee_search_results():
    record = {"record_type": "window_index", "memory_key": "late-night-window:test"}

    records = _records_from_search_result(
        [{"payload": {"text": _record_document(record)}}]
    )

    assert records == [record]


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

    assert ("cognify", "blackout_index") in cognee.calls
    assert ("cognify", "blackout_late_night_window_2026_07_04") in cognee.calls
    assert "blackout_index" in cognee.data_by_dataset
    assert "blackout_late_night_window_2026_07_04" in cognee.data_by_dataset
    assert "00:12 - ShopSwift receipt: novelty keyboard, $129." in "\n".join(
        cognee.data_by_dataset["blackout_late_night_window_2026_07_04"]
    )


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
        call[0] == "search" and call[3] == ["blackout_index"]
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


def test_real_cognee_adapter_recalls_memory_saved_by_a_previous_adapter_instance():
    cognee = RecordingCogneeClient()
    window = LateNightWindow(
        label="Pasted late-night window",
        starts_at="2026-07-04T00:00:00+05:30",
        ends_at="2026-07-04T05:00:00+05:30",
        memory_key="late-night-window:2026-07-04",
    )
    RealCogneeMemoryAdapter(cognee_client=cognee).remember_late_night_window(
        window=window,
        primary_demo_evidence="00:12 - ShopSwift receipt: novelty keyboard, $129.",
    )

    fresh_adapter = RealCogneeMemoryAdapter(cognee_client=cognee)
    result = fresh_adapter.recall_morning_after()

    assert result.late_night_window == window
    assert result.timeline[0].summary == "Bought novelty keyboard from ShopSwift"


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
    fresh_adapter = RealCogneeMemoryAdapter(cognee_client=cognee)
    updated_result = fresh_adapter.recall_morning_after()

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
    fresh_adapter = RealCogneeMemoryAdapter(cognee_client=cognee)
    result = fresh_adapter.recall_morning_after()

    assert ("delete_dataset", "blackout_late_night_window_2026_07_04") in cognee.calls
    assert result.timeline == []
