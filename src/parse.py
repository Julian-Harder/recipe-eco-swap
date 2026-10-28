"""Parse an ingredient line like "200g minced beef" into quantity, unit, name and grams."""
import re

# Grams per unit. ml/l assume water density, which is close enough for milk, stock, oil.
UNIT_GRAMS = {
    "g": 1, "kg": 1000, "ml": 1, "l": 1000,
    "tbsp": 15, "tsp": 5, "cup": 240, "clove": 5, "pinch": 0.5,
}

UNIT_ALIASES = {
    "g": "g", "gr": "g", "gram": "g", "grams": "g",
    "kg": "kg", "kilo": "kg", "kilos": "kg", "kilogram": "kg", "kilograms": "kg",
    "ml": "ml", "millilitre": "ml", "milliliter": "ml", "millilitres": "ml", "milliliters": "ml",
    "l": "l", "litre": "l", "liter": "l", "litres": "l", "liters": "l",
    "tbsp": "tbsp", "tbs": "tbsp", "tablespoon": "tbsp", "tablespoons": "tbsp",
    "tsp": "tsp", "teaspoon": "tsp", "teaspoons": "tsp",
    "cup": "cup", "cups": "cup",
    "clove": "clove", "cloves": "clove",
    "pinch": "pinch", "pinches": "pinch",
    "piece": "piece", "pieces": "piece", "pc": "piece", "pcs": "piece",
}

# Default weight of one item when a line gives a bare count ("2 eggs"). First keyword match wins.
PIECE_GRAMS = {
    "egg": 50, "garlic": 5, "onion": 150, "shallot": 40, "carrot": 80, "tomato": 120,
    "potato": 170, "pepper": 150, "avocado": 170, "banana": 120, "chicken breast": 170,
    "slice": 30, "can": 400, "tin": 400,
}
DEFAULT_PIECE_GRAMS = 100

UNICODE_FRACTIONS = {"½": 0.5, "⅓": 1 / 3, "⅔": 2 / 3, "¼": 0.25, "¾": 0.75}

# "1 1/2", "1/2", "1.5", "1,5", "2"
QTY = r"(?P<qty>\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?)"
LINE = re.compile(rf"^\s*{QTY}?\s*(?P<unit>[a-zA-Z]+\b)?\.?\s*(?P<rest>.*)$")


def _to_float(qty: str) -> float:
    qty = qty.replace(",", ".")
    if " " in qty:
        whole, frac = qty.split()
        return float(whole) + _to_float(frac)
    if "/" in qty:
        num, den = qty.split("/")
        return float(num) / float(den)
    return float(qty)


def _piece_grams(name: str) -> float:
    for key, grams in PIECE_GRAMS.items():
        if key in name:
            return grams
    return DEFAULT_PIECE_GRAMS


def parse_line(line: str) -> dict:
    """Return dict(quantity, unit, name, grams). Unknown amounts give grams=None."""
    text = line.strip().lower()
    for sym, val in UNICODE_FRACTIONS.items():
        text = re.sub(rf"(\d)\s*{sym}", lambda m: f"{m.group(1)} {val}", text)
        text = text.replace(sym, str(val))
    text = re.sub(r"(\d) (0\.\d+)", lambda m: str(float(m.group(1)) + float(m.group(2))), text)

    times = re.match(r"^(\d+)\s*x\s+(?=\d)", text)  # "2 x 150g salmon" -> 2 * parse("150g salmon")
    if times:
        out = parse_line(text[times.end():])
        k = int(times.group(1))
        return {**out, "quantity": out["quantity"] * k, "grams": round(out["grams"] * k, 1)}

    m = LINE.match(text)
    qty = _to_float(m.group("qty")) if m.group("qty") else None
    unit_word, rest = m.group("unit"), m.group("rest")
    unit = UNIT_ALIASES.get(unit_word or "")
    if unit is None and unit_word:  # the "unit" was really the first word of the name
        rest = f"{unit_word} {rest}"
    name = re.sub(r"^(of|x)\s+", "", rest).split(",")[0].strip()

    if qty is None and unit is None:
        if text.startswith(("a pinch", "pinch")):
            name = re.sub(r"^a?\s*pinch( of)?\s*", "", text)
            return {"quantity": 1, "unit": "pinch", "name": name, "grams": UNIT_GRAMS["pinch"]}
        return {"quantity": None, "unit": None, "name": name, "grams": None}
    qty = 1 if qty is None else qty
    if unit in (None, "piece"):
        unit = "piece"
        grams = qty * _piece_grams(name)
    else:
        grams = qty * UNIT_GRAMS[unit]
    return {"quantity": qty, "unit": unit, "name": name, "grams": round(grams, 1)}


if __name__ == "__main__":
    for s in ["200g minced beef", "1 tbsp olive oil", "2 large eggs", "1/2 cup milk",
              "1 1/2 kg potatoes", "3 cloves garlic", "400g can chopped tomatoes", "salt to taste"]:
        print(f"{s!r:30} -> {parse_line(s)}")
