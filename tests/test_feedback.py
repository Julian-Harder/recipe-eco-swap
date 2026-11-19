"""Feedback is the evidence for level 4, so losing or mangling it must be caught."""
import csv
import json

from feedback import read_feedback, save_feedback


def test_feedback_is_appended_with_header(tmp_path):
    path = tmp_path / "feedback.csv"
    assert read_feedback(path) == ""

    matches = [{"line": "400g minced beef", "food": "Beef, minced steak", "grams": 400},
               {"line": "salt to taste", "food": None, "grams": None}]
    save_feedback("Ana (team 3)", "yes", ["salt to taste"], "  Nice, but salt was not counted ",
                  "400g minced beef\nsalt to taste", 14.28, matches, path=path)
    save_feedback("", None, [], "", "1 onion", 0.06, [{"line": "1 onion"}], path=path)

    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == 2
    assert rows[0]["tester"] == "Ana (team 3)"
    assert rows[0]["comment"] == "Nice, but salt was not counted"
    assert rows[0]["wrong_lines"] == "salt to taste"
    assert rows[0]["total_kg_co2e"] == "14.28"
    assert json.loads(rows[0]["matches"])[0]["food"] == "Beef, minced steak"
    assert rows[1]["useful"] == ""


def test_commas_and_newlines_survive(tmp_path):
    path = tmp_path / "feedback.csv"
    save_feedback("x", "no", ["1 onion, finely chopped"], 'Said "beef", meant lamb,\nsorry',
                  "1 onion, finely chopped", 0.06, [], path=path)
    row = next(csv.DictReader(path.open(encoding="utf-8")))
    assert row["comment"] == 'Said "beef", meant lamb,\nsorry'
    assert row["wrong_lines"] == "1 onion, finely chopped"
