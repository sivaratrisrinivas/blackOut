import json
import time
from pathlib import Path

import pytest
import server as server_module
from blackout.cognee_adapter import CogneeHttpClient, RealCogneeMemoryAdapter
from blackout.workflow import BlackOutWorkflow, FakeMemoryAdapter
from server import app as flask_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("BLACKOUT_MEMORY_ADAPTER", "fake")
    server_module._workflow = None
    with flask_app.test_client() as c:
        c.post("/api/reset")
        yield c
    server_module._workflow = None


class TestHTMLPage:
    """Tests for the Flask API service boundary."""

    def test_root_identifies_api_service(self, client):
        resp = client.get("/")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["service"] == "BlackOut API"
        assert "Next.js" in data["ui"]

    def test_frontend_source_contains_narrative_copy(self):
        page = (Path(__file__).resolve().parent.parent / "frontend/app/page.tsx").read_text()
        assert "Reconstruct" in page
        assert "recognize repeat patterns" in page
        assert "repair memory" in page

    def test_frontend_calls_configurable_api_base_url(self):
        page = (Path(__file__).resolve().parent.parent / "frontend/app/page.tsx").read_text()
        assert "NEXT_PUBLIC_BLACKOUT_API_BASE_URL" in page
        assert "http://127.0.0.1:5000" in page

    def test_frontend_copy_avoids_out_of_scope_integrations(self):
        page = (Path(__file__).resolve().parent.parent / "frontend/app/page.tsx").read_text().lower()
        out_of_scope = ["oauth", "sign in", "connect your", "link your", "log in"]
        for phrase in out_of_scope:
            assert phrase not in page, f"Found out-of-scope phrase: {phrase}"

    def test_frontend_copy_avoids_shame_and_diagnosis_language(self):
        page = (Path(__file__).resolve().parent.parent / "frontend/app/page.tsx").read_text().lower()
        forbidden = ["shame", "guilt", "bad decision", "mistake", "diagnosis", "patholog"]
        for word in forbidden:
            assert word not in page, f"Found forbidden word: {word}"


class TestAPIFlow:
    """Tests for the Flask API endpoints."""

    def test_load_demo_returns_timeline_with_decisions(self, client):
        resp = client.post("/api/load-demo")
        data = resp.get_json()
        assert data["success"] is True
        decisions = data["recall"]["timeline"]
        assert any("espresso" in d["summary"] for d in decisions)

    def test_load_demo_does_not_wait_for_slow_cognee_uploads(self, monkeypatch):
        class Response:
            headers = {"Content-Type": "application/json"}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return None

            def read(self):
                return b'{"ok": true}'

        def urlopen(request, timeout):
            time.sleep(0.2)
            return Response()

        def build_adapter(*, load_shell_exports):
            return RealCogneeMemoryAdapter(
                cognee_client=CogneeHttpClient(
                    base_url="https://example.invalid",
                    api_key="not-shown",
                    urlopen=urlopen,
                )
            )

        monkeypatch.setattr(server_module, "build_memory_adapter_from_env", build_adapter)
        server_module._workflow = None

        with flask_app.test_client() as c:
            c.post("/api/reset")
            started_at = time.perf_counter()
            resp = c.post("/api/load-demo")
            elapsed = time.perf_counter() - started_at

        data = resp.get_json()
        assert elapsed < 0.2
        assert data["success"] is True
        assert any("espresso" in d["summary"] for d in data["recall"]["timeline"])
        server_module._workflow = None

    def test_full_flow_feedback_and_forget(self, client):
        resp = client.post("/api/load-demo")
        data = resp.get_json()
        assert data["success"] is True
        recall = data["recall"]
        assert len(recall["timeline"]) > 0

        first = recall["timeline"][0]
        fb_resp = client.post("/api/feedback", json={
            "evidence_text": first["evidence_excerpt"],
            "label": "Regret",
        })
        fb_data = fb_resp.get_json()
        assert fb_data["success"] is True
        assert fb_data["recall"]["timeline"][0]["feedback_label"] == "Regret"

        memory_key = recall["window"]["memory_key"]
        forget_resp = client.post("/api/forget", json={"memory_key": memory_key})
        forget_data = forget_resp.get_json()
        assert forget_data["success"] is True
        assert forget_data.get("forgotten") is True

    def test_feedback_can_save_current_decision_without_recalling_first(self):
        class RecordingMemoryAdapter(FakeMemoryAdapter):
            def __init__(self):
                super().__init__()
                self.recall_count = 0

            def recall_morning_after(self):
                self.recall_count += 1
                return super().recall_morning_after()

        memory = RecordingMemoryAdapter()
        workflow = BlackOutWorkflow(memory=memory)
        workflow.load_seed_demo_dataset()
        recall = workflow.morning_after_recall()
        decision = recall.timeline[0]
        server_module._workflow = workflow

        with flask_app.test_client() as c:
            resp = c.post("/api/feedback", json={
                "window": {
                    "label": recall.late_night_window.label,
                    "starts_at": recall.late_night_window.starts_at,
                    "ends_at": recall.late_night_window.ends_at,
                    "memory_key": recall.late_night_window.memory_key,
                },
                "decision": {
                    "timestamp": decision.timestamp,
                    "summary": decision.summary,
                    "category": decision.category,
                    "source_type": decision.source_type,
                    "people_or_vendors": decision.people_or_vendors,
                    "amount": decision.amount,
                    "regret_signals": decision.regret_signals,
                    "evidence_excerpt": decision.evidence_excerpt.text,
                    "feedback_label": decision.feedback_label,
                },
                "label": "Fine",
            })

        data = resp.get_json()
        assert data["success"] is True
        assert data["decision"]["feedback_label"] == "Fine"
        assert memory.recall_count == 1
        assert [call.feedback_label for call in memory.improve_calls] == ["Fine"]
        server_module._workflow = None

    def test_ask_memory_returns_answer(self, client):
        client.post("/api/load-demo")
        resp = client.post("/api/ask", json={
            "question": "What did I buy after midnight?"
        })
        data = resp.get_json()
        assert data["success"] is True
        assert "espresso" in data["answer"].lower()

    def test_ask_memory_survives_cognee_search_timeout(self, monkeypatch):
        class TimeoutAskCogneeClient:
            def __init__(self):
                self.data_by_dataset = {}

            def remember(self, data, dataset_name=None, run_in_background=False):
                self.data_by_dataset.setdefault(dataset_name, []).append(data)

            def recall(self, query_text, query_type=None, datasets=None):
                if str(query_text).startswith("Ask Your Memory:"):
                    raise TimeoutError("Cognee recall timed out")
                selected_datasets = datasets or list(self.data_by_dataset)
                return "\n".join(
                    data
                    for dataset_name in selected_datasets
                    for data in self.data_by_dataset.get(dataset_name, [])
                )

            def improve(self, dataset_name=None):
                return None

            def delete_dataset(self, dataset_name):
                return None

        def build_adapter(*, load_shell_exports):
            return RealCogneeMemoryAdapter(cognee_client=TimeoutAskCogneeClient())

        monkeypatch.setattr(server_module, "build_memory_adapter_from_env", build_adapter)
        server_module._workflow = None

        with flask_app.test_client() as c:
            c.post("/api/reset")
            c.post("/api/load-demo")
            resp = c.post("/api/ask", json={
                "question": "What did I buy after midnight?"
            })

        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert "espresso" in data["answer"].lower()
        server_module._workflow = None

    def test_prompts_endpoint_returns_suggestions(self, client):
        client.post("/api/load-demo")
        resp = client.get("/api/prompts")
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["prompts"]) > 0

    def test_forget_marks_window_as_forgotten(self, client):
        data = client.post("/api/load-demo").get_json()
        memory_key = data["recall"]["window"]["memory_key"]

        resp = client.post("/api/forget", json={"memory_key": memory_key})
        result = resp.get_json()
        assert result["success"] is True
        assert result["forgotten"] is True

    def test_reset_uses_env_selected_memory_adapter(self, monkeypatch):
        calls = []

        def build_adapter(*, load_shell_exports):
            calls.append(load_shell_exports)
            return FakeMemoryAdapter()

        monkeypatch.setattr(server_module, "build_memory_adapter_from_env", build_adapter)
        server_module._workflow = None

        with flask_app.test_client() as c:
            resp = c.post("/api/reset")

        assert resp.get_json()["success"] is True
        assert calls == [True]
        assert isinstance(server_module._workflow._memory, FakeMemoryAdapter)
        server_module._workflow = None

    def test_api_allows_local_next_frontend_origin(self, client):
        resp = client.post(
            "/api/load-demo",
            headers={"Origin": "http://localhost:3000"},
        )

        assert resp.status_code == 200
        assert resp.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert "Content-Type" in resp.headers["Access-Control-Allow-Headers"]

    def test_api_allows_local_next_frontend_preflight(self, client):
        resp = client.options(
            "/api/load-demo",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        assert resp.status_code == 200
        assert resp.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert "POST" in resp.headers["Access-Control-Allow-Methods"]

    def test_api_allows_private_next_frontend_network_origin(self, client):
        resp = client.options(
            "/api/load-demo",
            headers={
                "Origin": "http://10.255.255.254:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        assert resp.status_code == 200
        assert resp.headers["Access-Control-Allow-Origin"] == "http://10.255.255.254:3000"

    def test_local_dev_server_does_not_restart_on_file_changes(self, monkeypatch):
        run_kwargs = []

        def run_app(**kwargs):
            run_kwargs.append(kwargs)

        monkeypatch.setattr(server_module.app, "run", run_app)
        monkeypatch.setenv("PORT", "5050")

        server_module.run_local_dev_server()

        assert run_kwargs == [
            {
                "debug": True,
                "host": "0.0.0.0",
                "port": 5050,
                "use_reloader": False,
            }
        ]


def test_readme_covers_hackathon_submission_narrative():
    readme = (Path(__file__).resolve().parent.parent / "README.md").read_text()
    assert "## Hackathon Submission" in readme
    assert "Reconstruct" in readme
    assert "Recognize" in readme
    assert "Repair" in readme
    assert "Seed Demo Mode" in readme
    assert "COGNEE_BASE_URL" in readme
    assert "COGNEE_API_KEY" in readme
    assert "LLM_API_KEY" in readme
