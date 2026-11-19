"""Unit tests for src/normalize.py: synonyms and typo correction before the AI matcher."""
import pytest

from normalize import apply_synonyms, build_vocabulary, correct_typos, normalize_name


@pytest.fixture(scope="module")
def vocab(foods):
    return build_vocabulary(foods["name"])


@pytest.mark.parametrize("name,expected", [
    ("aubergine", "eggplant"),
    ("cilantro", "coriander"),
    ("scallions", "spring onion"),
    ("garbanzo beans", "chick pea"),
    ("can chickpeas", "can chick pea"),
    ("ground beef", "minced beef"),
    ("mince", "minced beef"),
    ("lardons", "lardoons"),
    ("plain flour", "wheat flour"),
    ("cornflour", "corn starch"),
    ("red bell pepper", "red sweet pepper"),
])
def test_synonyms(name, expected):
    assert apply_synonyms(name) == expected


def test_synonyms_whole_words_only():
    # "beet" must not touch "beetroot", "mince" must not touch "minced".
    assert apply_synonyms("beetroot") == "beetroot"
    assert apply_synonyms("minced beef") == "minced beef"


def test_synonyms_single_pass():
    # "passata" -> "tomato puree" must not then become "tomato paste".
    assert apply_synonyms("passata") == "tomato puree"


@pytest.mark.parametrize("name,expected", [
    ("chiken breasts", "chicken breasts"),
    ("brocoli", "broccoli"),
    ("parmesean", "parmesan"),
    ("mozarella", "mozzarella"),
    ("spinnach", "spinach"),
])
def test_typos_are_corrected(name, expected, vocab):
    assert correct_typos(name, vocab) == expected


@pytest.mark.parametrize("name", ["minced beef", "olive oil", "tomatoes", "chicken fillets", "xanthan gum"])
def test_correct_words_are_left_alone(name, vocab):
    assert correct_typos(name, vocab) == name


def test_synonyms_before_typos(vocab):
    # Without the synonym step, "scallions" would be "corrected" to a seafood.
    assert normalize_name("scallions", vocab) == "spring onion"
