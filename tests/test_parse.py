"""Unit tests for src/parse.py: ingredient line -> quantity, unit, name, grams.

Wrong grams give a wrong CO2e even when the food is matched correctly, so every change to the
parser must keep these passing.

Cases marked xfail are KNOWN BUGS (see LOG.md and the Step 2 plan). They are expected to fail today.
When someone fixes one, pytest reports it as XPASS and the run fails (strict=True): remove the
xfail marker in the same pull request so the fix stays protected.
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
    ("2 tins chickpeas", 800, "tins chickpeas"),
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


# ---- Known bugs: Step 2 fixes these. Remove the marker when a case passes. ----

KNOWN_BUGS = [
    # "can" is not a unit, and "tomato" (120 g) is found before "can" (400 g) in PIECE_GRAMS.
    pytest.param("1 can chopped tomatoes", 400, "chopped tomatoes", id="can-of-tomatoes"),
    # "head of" stays in the name, so the matcher sees "head of broccoli"; default 100 g.
    pytest.param("1 head of broccoli", 350, "broccoli", id="head-of"),
    # "bunch" is not a unit.
    pytest.param("1 bunch fresh coriander", 30, "fresh coriander", id="bunch"),
    # "a handful of" gives no quantity at all.
    pytest.param("a handful of spinach", 30, "spinach", id="handful"),
]


@pytest.mark.xfail(strict=True, reason="known parser bug, fixed in Step 2")
@pytest.mark.parametrize("line,grams,name", KNOWN_BUGS)
def test_known_parser_bugs(line, grams, name):
    out = parse_line(line)
    assert out["grams"] == pytest.approx(grams, rel=0.3)
    assert out["name"] == name


@pytest.mark.xfail(strict=True, reason="known parser bug, fixed in Step 2")
def test_unknown_amount_name_is_clean():
    # "to taste" should not be sent to the matcher as part of the name.
    assert parse_line("salt to taste")["name"] == "salt"
