"""Unit tests for src/parse.py: ingredient line -> quantity, unit, name, grams.

Wrong grams give a wrong CO2e even when the food is matched correctly, so every change to the
parser must keep these passing.

For a newly found bug, add the case with @pytest.mark.xfail(strict=True): it documents the bug, and when
someone fixes it pytest reports XPASS and the run fails until the marker is removed, so the fix stays protected.
"""
import pytest

from parse import parse_line

# (line, expected grams, expected name)
WORKING = [
    ("200g minced beef", 200, "minced beef"),
    ("1 kg potatoes", 1000, "potatoes"),
    ("1 1/2 kg potatoes", 1500, "potatoes"),
    ("1,5 kg flour", 1500, "flour"),
    ("250 ml milk", 250, "milk"),
    ("1 litre vegetable stock", 1000, "vegetable stock"),
    ("2 tbsp olive oil", 30, "olive oil"),
    ("1 tsp salt", 5, "salt"),
    ("1/2 cup milk", 120, "milk"),
    ("½ cup rice", 120, "rice"),
    ("3 cloves garlic", 15, "garlic"),
    ("1 onion, finely chopped", 150, "onion"),
    ("2 x 150g salmon fillets", 300, "salmon fillets"),
    ("400g can chopped tomatoes", 400, "can chopped tomatoes"),
    ("2 chicken breasts", 340, "chicken breasts"),
]


@pytest.mark.parametrize("line,grams,name", WORKING)
def test_parse_grams_and_name(line, grams, name):
    out = parse_line(line)
    assert out["grams"] == pytest.approx(grams)
    assert out["name"] == name


def test_pinch():
    out = parse_line("a pinch of salt")
    assert out["unit"] == "pinch"
    assert out["name"] == "salt"
    assert out["grams"] == pytest.approx(0.5)


def test_unknown_amount_gives_no_grams():
    # The app must ask the user instead of guessing.
    out = parse_line("salt to taste")
    assert out["grams"] is None
    assert out["quantity"] is None


def test_bare_count_uses_piece_weight():
    out = parse_line("2 large eggs")
    assert out["unit"] == "piece"
    assert out["grams"] == pytest.approx(100)


# ---- Fixed in Step 2 (2026-11-19): these were known bugs, kept here so they cannot come back. ----

FIXED = [
    # "can"/"tin" is a 400 g unit, and the canned form is kept for the matcher.
    pytest.param("1 can chopped tomatoes", 400, "canned chopped tomatoes", id="can-of-tomatoes"),
    pytest.param("2 tins chickpeas", 800, "canned chickpeas", id="tins"),
    # "head" depends on the vegetable.
    pytest.param("1 head of broccoli", 350, "broccoli", id="head-of"),
    pytest.param("1 head garlic", 50, "garlic", id="head-garlic"),
    # bunch, handful and slice are units.
    pytest.param("1 bunch fresh coriander", 30, "fresh coriander", id="bunch"),
    pytest.param("a handful of spinach", 30, "spinach", id="handful"),
    pytest.param("2 slices of bread", 60, "bread", id="slices"),
    # Trailing notes are not part of the ingredient.
    pytest.param("3 tbsp pesto (optional)", 45, "pesto", id="optional"),
]


@pytest.mark.parametrize("line,grams,name", FIXED)
def test_fixed_parser_bugs(line, grams, name):
    out = parse_line(line)
    assert out["grams"] == pytest.approx(grams)
    assert out["name"] == name


def test_unknown_amount_name_is_clean():
    # "to taste" is not sent to the matcher as part of the name, and there is still no amount.
    out = parse_line("salt to taste")
    assert out["name"] == "salt"
    assert out["grams"] is None


def test_vague_amount_still_asks_the_user():
    # "a few" is not a unit: no guessed amount, the app asks for grams.
    assert parse_line("a few sprigs thyme")["grams"] is None
