"""Suggest curated swaps for the highest-impact ingredients of a scored recipe."""
from pathlib import Path

import pandas as pd

CURATED = Path(__file__).resolve().parents[1] / "data" / "curated"


def load_swaps(path: Path = CURATED / "swaps.csv") -> pd.DataFrame:
    return pd.read_csv(path)


def suggest_swaps(scored: pd.DataFrame, swaps_df: pd.DataFrame, categories_df: pd.DataFrame,
                  per_ingredient: int = 2) -> list[dict]:
    """Return swaps that save CO2, highest-impact ingredients first.

    Savings assume the same weight of the replacement (a simplification; see swaps.csv notes).
    """
    co2 = categories_df.set_index("category")["co2_kg_per_kg"]
    out = []
    for _, ing in scored.dropna(subset=["kg_co2e"]).sort_values("kg_co2e", ascending=False).iterrows():
        options = []
        for _, s in swaps_df[swaps_df["from_category"] == ing["category"]].iterrows():
            new_factor = co2.get(s["to_category"])
            if pd.isna(new_factor):
                continue
            new_kg = ing["grams"] / 1000 * new_factor
            saved = ing["kg_co2e"] - new_kg
            if saved > 0:
                options.append({
                    "line": ing["line"], "from": ing["category"], "to": s["to_category"],
                    "kg_co2e_before": ing["kg_co2e"], "kg_co2e_after": new_kg,
                    "kg_co2e_saved": saved, "reason": s["reason"], "notes": s["notes"],
                })
        out += sorted(options, key=lambda o: o["kg_co2e_saved"], reverse=True)[:per_ingredient]
    return out
