"""Smoke test: the whole Streamlit page renders on the real database without errors (no LLM call)."""
from streamlit.testing.v1 import AppTest


def test_app_renders_all_tabs():
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Overview", "Forecast", "Analyst", "Segmentation"]
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Orders"] == "5,496"
    assert metrics["Loyal Count"] == "460"
