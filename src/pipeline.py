"""Recipe text -> parse -> match to an Agribalyse food -> CO2e -> swaps.

Run from the project root:
    python src/pipeline.py             # AI matcher (sentence embeddings)
    python src/pipeline.py --keyword   # keyword baseline, for comparison
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from foods import load_foods, same_food  # noqa: E402
from match import AIMatcher, KeywordMatcher, load_categories  # noqa: E402
from parse import parse_line  # noqa: E402
from score import score_recipe  # noqa: E402
from swaps import load_swaps, suggest_swaps  # noqa: E402

SAMPLE_RECIPE = """\
400g minced beef
300g spaghetti
1 onion, finely chopped
2 cloves garlic
1 carrot
400g can chopped tomatoes
2 tbsp olive oil
40g grated parmesan
"""


SWAP_CO2_TOLERANCE = 0.25


def swap_category(code: str | None, categories: pd.DataFrame, foods: pd.DataFrame,
                  keyword: KeywordMatcher) -> str | None:
    """The curated category whose swaps apply to this food, if any.

    Either the food is the category's own food (or a near duplicate), or the category's synonyms
    appear in the food's name and the two CO2 factors are within 25%. So "Parmesan cheese" gets the
    hard-cheese swaps, but "Broth, stock or bouillon, beef" does not get the beef-mince ones.
    """
    if code is None or code not in foods.index:
        return None
    for category, cat_code in zip(categories["category"], categories["agribalyse_code"]):
        if isinstance(cat_code, str) and same_food(code, cat_code, foods):
            return category
    category = keyword.match(foods.at[code, "name"])
    if category is None:
        return None
    cat_co2 = categories.set_index("category").at[category, "co2_kg_per_kg"]
    food_co2 = foods.at[code, "co2_kg_per_kg"]
    if pd.notna(cat_co2) and abs(food_co2 - cat_co2) <= SWAP_CO2_TOLERANCE * cat_co2:
        return category
    return None


def run(recipe_text: str, matcher=None, foods=None, categories=None, swaps=None):
    foods = load_foods() if foods is None else foods
    categories = load_categories() if categories is None else categories
    swaps = load_swaps() if swaps is None else swaps
    matcher = AIMatcher(foods) if matcher is None else matcher
    keyword = KeywordMatcher(categories)
    lines = []
    for raw in recipe_text.splitlines():
        if not raw.strip():
            continue
        parsed = parse_line(raw)
        code, score = matcher.match_food(parsed["name"])
        food = foods.loc[code] if code in foods.index else None
        lines.append({
            "line": raw.strip(), "name": parsed["name"], "grams": parsed["grams"],
            "food_code": code, "food": None if food is None else food["name"], "match_score": score,
            "co2_kg_per_kg": None if food is None else food["co2_kg_per_kg"],
            "category": swap_category(code, categories, foods, keyword),
        })
    scored, total = score_recipe(lines)
    return scored, total, suggest_swaps(scored, swaps, categories)


if __name__ == "__main__":
    matcher = KeywordMatcher() if "--keyword" in sys.argv else None
    scored, total, suggestions = run(SAMPLE_RECIPE, matcher)
    pd.set_option("display.width", 160)
    print("Spaghetti bolognese (4 servings)\n")
    counted = scored.dropna(subset=["kg_co2e"]).copy()
    counted["food"] = counted["food"].str.slice(0, 40)
    print(counted[["line", "food", "match_score", "grams", "co2_kg_per_kg", "kg_co2e", "share"]]
          .to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print(f"\nTotal: ≈ {total:.1f} kg CO2e (estimate)")

    skipped = scored[scored["kg_co2e"].isna()]
    if len(skipped):
        print("\nNot counted:")
        for _, r in skipped.iterrows():
            reason = ("no confident match" if r["food_code"] is None or pd.isna(r["food_code"])
                      else "amount unknown")
            print(f"  {r['line']}: {reason} (match score {r['match_score']:.2f})")

    print("\nSuggested swaps:")
    for s in suggestions:
        print(f"  {s['from']} -> {s['to']}: saves ≈ {s['kg_co2e_saved']:.1f} kg CO2e "
              f"({s['kg_co2e_before']:.1f} -> {s['kg_co2e_after']:.1f}). {s['reason']}")
