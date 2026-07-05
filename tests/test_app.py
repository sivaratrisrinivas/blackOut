import json
from pathlib import Path

import pytest
from server import app as flask_app


@pytest.fixture
def client():
    with flask_app.test_client() as c:
        c.post("/api/reset")
        yield c


class TestHTMLPage:
    """Tests for the Flask-served HTML page content."""

    def test_welcome_page_contains_narrative_copy(self, client):
        resp = client.get("/")
        html = resp.data.decode()
        assert resp.status_code == 200
        assert "Reconstruct" in html
        assert "Recognize" in html
        assert "Repair" in html

    def test_welcome_page_avoids_out_of_scope_integrations(self, client):
        resp = client.get("/")
        html = resp.data.decode().lower()
        out_of_scope = ["oauth", "sign in", "connect your", "link your", "log in"]
        for phrase in out_of_scope:
            assert phrase not in html, f"Found out-of-scope phrase: {phrase}"

    def test_welcome_page_defers_screenshot_as_secondary(self, client):
        resp = client.get("/")
        html = resp.data.decode().lower()
        assert "screenshot" in html
        assert "coming soon" in html

    def test_copy_avoids_shame_and_diagnosis_language(self, client):
        resp = client.get("/")
        html = resp.data.decode().lower()
        forbidden = ["shame", "guilt", "bad decision", "mistake", "diagnosis", "patholog"]
        for word in forbidden:
            assert word not in html, f"Found forbidden word: {word}"


class TestAPIFlow:
    """Tests for the Flask API endpoints."""

    def test_load_demo_returns_timeline_with_decisions(self, client):
        resp = client.post("/api/load-demo")
        data = resp.get_json()
        assert data["success"] is True
        decisions = data["recall"]["timeline"]
        assert any("espresso" in d["summary"] for d in decisions)

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

    def test_ask_memory_returns_answer(self, client):
        client.post("/api/load-demo")
        resp = client.post("/api/ask", json={
            "question": "What did I buy after midnight?"
        })
        data = resp.get_json()
        assert data["success"] is True
        assert "espresso" in data["answer"].lower()

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
