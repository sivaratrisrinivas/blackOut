from streamlit.testing.v1 import AppTest


def test_app_displays_ask_your_memory_answer_from_a_suggested_prompt():
    app = AppTest.from_file("app.py")

    app.run()
    app.button[1].click().run()
    app.button[2].click().run()
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
    app.button[2].click().run()
    app.button("ask-prompt-0").click().run()

    app.checkbox[0].check().run()
    app.button("forget-current-window").click().run()

    assert all("espresso machine" not in markdown.value for markdown in app.markdown)
