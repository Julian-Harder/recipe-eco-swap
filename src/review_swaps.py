"""Human review of the swaps: are they sensible in the dish?

There is no ground truth for "a good swap", so a person judges them. This script runs the full pipeline
(AI matcher, curated + AI swaps) on seven varied recipes and writes every suggested swap to
data/eval/swap_review.csv with an empty `sensible` column.

    python src/review_swaps.py              # write the CSV (overwrites an unfilled one only)
    python src/review_swaps.py --summary    # after filling `sensible` with y / n: share of sensible swaps

Judge each swap as a home cook would: would you make this swap in this dish? y = yes, n = no.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from pipeline import SAMPLE_RECIPE, run  # noqa: E402

REVIEW = Path(__file__).resolve().parents[1] / "data" / "eval" / "swap_review.csv"

RECIPES = {
    "spaghetti bolognese": SAMPLE_RECIPE,
    "chicken curry": """400g boneless chicken thighs
2 tbsp vegetable oil
1 onion, finely diced
3 cloves garlic
2 tbsp curry powder
400ml coconut milk
250g basmati rice""",
    "lamb tagine": """600g lamb shoulder, diced
1 onion
400g can chickpeas
1 tsp ground cumin
300ml vegetable stock
100g dried apricots""",
    "salmon with dill": """4 salmon fillets (150g each)
2 tbsp unsalted butter
1 lemon
1 bunch fresh dill
500g new potatoes""",
    "chocolate cake": """200g dark chocolate
150g unsalted butter
150g caster sugar
3 eggs
120g plain flour""",
    "cheese omelette and salad": """3 eggs
50g grated cheddar
100g feta
100g rocket
200ml whole milk""",
    "prawn stir-fry": """300g king prawns
200g egg noodles
1 red bell pepper
2 tbsp soy sauce
1 tbsp sesame oil""",
}


def build() -> pd.DataFrame:
    rows = []
    for dish, recipe in RECIPES.items():
        _, total, swaps = run(recipe)
        print(f"{dish}: {len(swaps)} swaps (total ≈ {total:.1f} kg CO2e)")
        for s in swaps:
            rows.append({"dish": dish, "line": s["line"], "from": s["from"], "to": s["to"], "source": s["source"],
                         "kg_co2e_saved": round(s["kg_co2e_saved"], 2), "sensible": ""})
    return pd.DataFrame(rows)


def summary(df: pd.DataFrame) -> None:
    judged = df[df["sensible"].astype(str).str.lower().isin(["y", "n"])]
    if judged.empty:
        print(f"No judgements yet: fill the `sensible` column of {REVIEW} with y or n.")
        return
    judged = judged.assign(ok=judged["sensible"].str.lower() == "y")
    for source, g in judged.groupby("source"):
        print(f"[{source}] sensible {g['ok'].sum()}/{len(g)} = {g['ok'].mean():.0%}")
    print(f"[all] sensible {judged['ok'].sum()}/{len(judged)} = {judged['ok'].mean():.0%}\n")
    for _, r in judged[~judged["ok"]].iterrows():
        print(f"  not sensible ({r['source']}) in {r['dish']}: {r['line']} -> {r['to']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    if args.summary:
        summary(pd.read_csv(REVIEW, dtype={"sensible": str}).fillna({"sensible": ""}))
    else:
        if REVIEW.exists() and pd.read_csv(REVIEW, dtype={"sensible": str})["sensible"].notna().any():
            sys.exit(f"{REVIEW} already has judgements; move it away to rebuild.")
        df = build()
        df.to_csv(REVIEW, index=False)
        print(f"\nWrote {len(df)} swaps to {REVIEW}. Fill `sensible` with y / n, then run with --summary.")
