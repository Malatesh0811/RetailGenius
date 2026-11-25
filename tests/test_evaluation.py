"""Tests for the agent evaluation harness - all offline, no LLM calls."""
import pytest

from retailgenius.evaluation import (EVAL_SET, EvalCase, extract_numbers, grade, ground_truth, month_names,
                                     number_matches, run_eval, write_report)


@pytest.mark.parametrize("text, expected", [
    ("Total sales were $14,915,600.82.", [14915600.82]),
    ("about 3.72 million dollars", [3720000.0]),
    ("roughly $12K", [12000.0]),
    ("There are 5496 orders", [5496.0]),
    ("margin of 10.2%", [10.2]),
    ("it takes 2 months", [2.0]),            # 'months' must not be read as 'm' = million
])
def test_extract_numbers(text, expected):
    assert extract_numbers(text) == pytest.approx(expected)


def test_number_tolerance():
    assert number_matches("Sales were $14.92 million", 14_915_600.82)          # within 1%
    assert not number_matches("Sales were $13 million", 14_915_600.82)
    assert number_matches("There are 5,496 orders.", 5496, tolerance=0)
    assert not number_matches("There are 8,399 orders.", 5496, tolerance=0)     # the rows-vs-orders trap


def test_percent_accepts_fraction_form():
    assert number_matches("The margin is 10.2%", 10.2025, percent=True)
    assert number_matches("The margin is 0.102", 10.2025, percent=True)
    assert not number_matches("The margin is 0.102", 10.2025, percent=False)


def test_grade_text_list_month():
    text = EvalCase("q", "", "text")
    assert grade(text, "The top category is **Technology**.", "Technology")
    assert not grade(text, "Furniture leads.", "Technology")

    lst = EvalCase("q", "", "list")
    top3 = ["Emily Phan", "Deborah Brumfield", "Roy Skaria"]
    assert grade(lst, "1. Emily Phan\n2. Deborah  Brumfield\n3. Roy Skaria", top3)
    assert not grade(lst, "Emily Phan and Roy Skaria", top3)               # all must be present

    month = EvalCase("q", "", "month")
    assert month_names("2009-01") == ["2009-01", "January 2009", "Jan 2009", "01/2009"]
    assert grade(month, "January 2009 had the highest sales", "2009-01")
    assert not grade(month, "September 2010 had the highest sales", "2009-01")


def test_eval_set_is_complete_and_every_ground_truth_query_runs():
    assert len(EVAL_SET) == 20
    for case in EVAL_SET:
        value = ground_truth(case)
        assert value is not None and value != [], case.question


def test_known_ground_truths():
    by_q = {c.question: c for c in EVAL_SET}
    assert ground_truth(by_q["How many orders are there in total?"]) == 5496
    assert ground_truth(by_q["How many customers have placed more than 10 orders?"]) == 123


def test_run_eval_with_fake_agent(tmp_path):
    """The runner + report work end to end with a stand-in agent (no network)."""
    cases = [c for c in EVAL_SET if c.question in ("How many orders are there in total?",
                                                    "Which product category has the highest total sales?")]

    def fake_ask(agent, question):
        if "orders" in question:
            return "There are 8,399 orders.", ["SELECT COUNT(*) FROM orders"]   # the classic mistake
        return "Technology has the highest sales.", ["SELECT ..."]

    results = run_eval(agent=None, cases=cases, pause=0, ask_fn=fake_ask)
    assert [r.passed for r in results] == [False, True]

    assert write_report(results, "fake-model", out_dir=tmp_path) == 1
    report = (tmp_path / "results.md").read_text(encoding="utf-8")
    assert "Score: 1/2" in report and "SELECT COUNT(*) FROM orders" in report   # failures show the SQL


def test_runner_survives_errors():
    def broken(agent, question):
        raise RuntimeError("boom")
    results = run_eval(agent=None, cases=EVAL_SET[:1], pause=0, ask_fn=broken)
    assert not results[0].passed and "boom" in results[0].error
