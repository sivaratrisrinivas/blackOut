from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_deterministic_demo_path_loads_seed_recalls_applies_feedback_and_forgets():
    app = AppTest.from_file("app.py")

    app.run()

    app.button[1].click().run()

    assert any(
        "Decision timeline" in subheader.value for subheader in app.subheader
    )

    app.button[4].click().run()

    assert any(
        "Feedback Label: Regret" in success.value for success in app.success
    )

    app.checkbox[0].check().run()
    app.button("forget-current-window").click().run()

    assert any(
        "Forgot Late-Night Window" in success.value for success in app.success
    )


def test_app_shows_reconstruct_recognize_repair_narrative_on_first_screen():
    app = AppTest.from_file("app.py")

    app.run()

    page_text = " ".join(
        element.value for element in list(app.title) + list(app.markdown)
    )
    assert "Reconstruct" in page_text
    assert "Recognize" in page_text
    assert "Repair" in page_text


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


def test_app_does_not_imply_out_of_scope_integrations():
    app = AppTest.from_file("app.py")

    app.run()

    page_text = " ".join(
        element.value
        for element in list(app.title) + list(app.markdown) + list(app.caption)
    ).lower()

    out_of_scope = ["oauth", "sign in", "connect your", "link your", "log in"]
    for phrase in out_of_scope:
        assert phrase not in page_text, f"Found out-of-scope phrase: {phrase}"


def test_app_defers_screenshot_evidence_as_secondary_path():
    app = AppTest.from_file("app.py")

    app.run()

    page_text = " ".join(
        element.value
        for element in list(app.title) + list(app.markdown) + list(app.caption)
    ).lower()

    assert "screenshot" in page_text
    assert "coming soon" in page_text or "secondary" in page_text


def test_app_copy_avoids_shame_judgment_and_diagnosis_language():
    app = AppTest.from_file("app.py")

    app.run()
    app.button[1].click().run()

    page_text = " ".join(
        element.value
        for element in list(app.title) + list(app.markdown) + list(app.caption)
    ).lower()

    forbidden = ["shame", "guilt", "bad decision", "mistake", "diagnosis", "patholog"]
    for word in forbidden:
        assert word not in page_text, f"Found forbidden word: {word}"


def test_app_load_seed_demo_mode_shows_decision_timeline_immediately():
    app = AppTest.from_file("app.py")

    app.run()
    app.button[1].click().run()

    assert any(
        "Decision timeline" in subheader.value for subheader in app.subheader
    )


def test_app_shows_clear_message_when_cognee_credentials_are_missing(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("BLACKOUT_MEMORY_ADAPTER", "cognee")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("COGNEE_BASE_URL", raising=False)
    monkeypatch.delenv("COGNEE_API_KEY", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    app = AppTest.from_file("app.py")

    app.run()

    assert any("LLM_API_KEY" in error.value for error in app.error)


def test_app_displays_ask_your_memory_answer_from_a_suggested_prompt():
    app = AppTest.from_file("app.py")

    app.run()
    app.button[1].click().run()
    app.button("ask-prompt-0").click().run()

    assert any(
        "You bought espresso machine from BeanForge at 03:12 for $249."
        in markdown.value
        for markdown in app.markdown
    )
    assert any(
        "03:12 - BeanForge receipt: espresso machine, $249." in code.value
        for code in app.code
    )


def test_app_clears_displayed_ask_your_memory_answer_after_forgetting_window():
    app = AppTest.from_file("app.py")

    app.run()
    app.button[1].click().run()
    app.button("ask-prompt-0").click().run()

    app.checkbox[0].check().run()
    app.button("forget-current-window").click().run()

    assert all("espresso machine" not in markdown.value for markdown in app.markdown)
