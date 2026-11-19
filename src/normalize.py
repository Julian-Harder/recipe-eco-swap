"""Clean an ingredient name before it goes to the AI matcher: synonyms first, then typos.

    normalize_name("2 aubergines")  -> handled by parse.py first, then "aubergines" -> "eggplant"
    normalize_name("chiken breasts") -> "chicken breasts"

Why: the embedding model compares wording. Agribalyse is written in (translated) French-style English
("Eggplant", "Chick pea", "Lardoons", "Maize/corn starch"), while recipes use British or American words
and contain typos. Those were the matcher's main remaining misses (see LOG.md).

1. SYNONYMS maps common British/American kitchen words to the wording Agribalyse uses. The list comes
   from general UK/US food glossaries, not from our evaluation misses; one pass, longest phrase first,
   whole words only, so a replacement is never replaced again.
2. Typo correction: a word of 5+ letters that is not in the vocabulary (words of all food names + the
   synonym targets + common recipe words) is replaced by its closest vocabulary word if the similarity
   is at least TYPO_CUTOFF (difflib ratio). Words with no close match are left alone.
"""
import difflib
import re
from functools import lru_cache

# British / American word or phrase -> Agribalyse wording.
SYNONYMS = {
    # vegetables
    "aubergine": "eggplant", "aubergines": "eggplant",
    "zucchini": "courgette", "zucchinis": "courgette",
    "arugula": "rocket", "rucola": "rocket",
    "cilantro": "coriander",
    "scallion": "spring onion", "scallions": "spring onion",
    "green onion": "spring onion", "green onions": "spring onion",
    "salad onion": "spring onion", "salad onions": "spring onion",
    "bell pepper": "sweet pepper", "bell peppers": "sweet pepper",
    "capsicum": "sweet pepper", "capsicums": "sweet pepper",
    "chilli": "chili pepper", "chillies": "chili pepper", "chilies": "chili pepper",
    "chile": "chili pepper", "chiles": "chili pepper",
    "beet": "beetroot", "beets": "beetroot",
    "rutabaga": "swede",
    "fava bean": "broad bean", "fava beans": "broad bean",
    "green beans": "french bean", "green bean": "french bean",
    "string beans": "french bean", "runner beans": "french bean",
    # pulses
    "chickpea": "chick pea", "chickpeas": "chick pea",
    "garbanzo": "chick pea", "garbanzos": "chick pea",
    "garbanzo bean": "chick pea", "garbanzo beans": "chick pea",
    # meat and fish
    "mince": "minced beef", "beef mince": "minced beef", "ground beef": "minced beef",
    "hamburger meat": "minced beef",
    "lardons": "lardoons", "lardon": "lardoons",
    "streaky bacon": "bacon", "bacon rashers": "bacon", "rashers": "bacon",
    "prosciutto": "cured ham", "parma ham": "cured ham",
    "gammon": "ham",
    "shrimps": "shrimp", "king prawns": "prawn", "prawns": "prawn",
    # dairy
    "double cream": "liquid cream 30% fat", "heavy cream": "liquid cream 30% fat",
    "whipping cream": "liquid cream 30% fat",
    "single cream": "liquid cream light", "light cream": "liquid cream light",
    # baking and store cupboard
    "plain flour": "wheat flour", "all-purpose flour": "wheat flour", "all purpose flour": "wheat flour",
    "self-raising flour": "wheat flour self-raising", "self raising flour": "wheat flour self-raising",
    "self-rising flour": "wheat flour self-raising",
    "cornflour": "corn starch", "cornstarch": "corn starch",
    "bicarbonate of soda": "sodium bicarbonate", "baking soda": "sodium bicarbonate",
    "sultanas": "raisin", "sultana": "raisin",
    "tomato puree": "tomato paste", "tomato purée": "tomato paste",
    "passata": "tomato puree",
}

# Recipe words that are not in any food name but must not be "corrected".
RECIPE_WORDS = {
    "chopped", "diced", "sliced", "grated", "minced", "crushed", "peeled", "fresh", "frozen", "large",
    "small", "medium", "whole", "fillet", "fillets", "breast", "breasts", "thigh", "thighs", "boneless",
    "skinless", "finely", "roughly", "ripe", "unsalted", "salted", "dried", "canned", "tinned", "cooked",
    "leaves", "sprigs", "cloves", "stalks", "baby", "extra", "virgin", "light", "dark", "brown", "white",
}

TYPO_CUTOFF = 0.85
MIN_TYPO_LENGTH = 5

_SYNONYM_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(SYNONYMS, key=len, reverse=True)) + r")\b"
)


def apply_synonyms(name: str) -> str:
    return _SYNONYM_RE.sub(lambda m: SYNONYMS[m.group(1)], name.lower())


@lru_cache(maxsize=1)
def _default_vocabulary() -> frozenset[str]:
    from foods import load_foods

    return build_vocabulary(load_foods()["name"])


def build_vocabulary(food_names) -> frozenset[str]:
    vocab = set(RECIPE_WORDS)
    for text in list(food_names) + list(SYNONYMS.values()):
        vocab.update(re.findall(r"[a-z]+", str(text).lower()))
    return frozenset(vocab)


def correct_typos(name: str, vocabulary: frozenset[str] | None = None) -> str:
    vocab = _default_vocabulary() if vocabulary is None else vocabulary
    sorted_vocab = sorted(vocab)

    def fix(match: re.Match) -> str:
        word = match.group(0)
        if len(word) < MIN_TYPO_LENGTH or word in vocab:
            return word
        # Plural of a known word ("tomatoes", "fillets") is not a typo.
        if word.endswith("s") and (word[:-1] in vocab or word[:-2] in vocab):
            return word
        close = difflib.get_close_matches(word, sorted_vocab, n=1, cutoff=TYPO_CUTOFF)
        return close[0] if close else word

    return re.sub(r"[a-z]+", fix, name.lower())


def normalize_name(name: str, vocabulary: frozenset[str] | None = None) -> str:
    """Synonyms first (so "scallions" is not "corrected" to "scallops"), then typos."""
    return correct_typos(apply_synonyms(name), vocabulary)
