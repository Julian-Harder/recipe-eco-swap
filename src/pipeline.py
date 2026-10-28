"""Level 2: recipe text -> parse -> match -> score -> swaps.

Run from the project root: python src/pipeline.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from match import KeywordMatcher, load_categories  # noqa: E402
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


def run(recipe_text: str, matcher=None, categories=None, swaps=None):
    categories = load_categories() if categories is None else categories
    swaps = load_swaps() if swaps is None else swaps
    matcher = KeywordMatcher(categories) if matcher is None else matcher
    lines = []
    for raw in recipe_text.splitlines():
        if not raw.strip():
            continue
        parsed = parse_line(raw)
        lines.append({"line": raw.strip(), "name": parsed["name"], "grams": parsed["grams"],
                      "category": matcher.match(parsed["name"])})
    scored, total = score_recipe(lines, categories)
    return scored, total, suggest_swaps(scored, swaps, categories)


if __name__ == "__main__":
    scored, total, suggestions = run(SAMPLE_RECIPE)
    pd.set_option("display.width", 120)
    print("Spaghetti bolognese (4 servings)\n")
    print(scored[["line", "category", "grams", "co2_kg_per_kg", "kg_co2e", "share"]]
          .to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\nTotal: {total:.2f} kg CO2e\n")
    print("Suggested swaps:")
    for s in suggestions:
        print(f"  {s['from']} -> {s['to']}: saves {s['kg_co2e_saved']:.2f} kg CO2e "
              f"({s['kg_co2e_before']:.2f} -> {s['kg_co2e_after']:.2f}). {s['reason']}")
