"""Suggest lower-impact swaps for the highest-impact ingredients of a scored recipe.

Two sources, curated first:
1. Curated swaps (data/curated/swaps.csv) between our 41 categories, written by hand. They can cross food
   groups (beef mince -> lentils), which no similarity search would propose. Each swap may have a `not_when`
   pattern: if it matches the recipe line or the rest of the recipe, the swap is skipped, because it does not
   fit the dish (parmesan grated on a bolognese is not replaced by yogurt).
2. AI swaps for matched foods in sub-groups where foods play the same role (SWAPPABLE_SUBGROUPS: meats, fish,
   cheeses, dairy, fats, cereals): foods from the same sub-group with at least MIN_SAVING less CO2e per kg, ranked by how similar the embedding model finds them to the original.
   Offal and processed or cooked forms are left out unless the original is one, and a swap must save at least
   MIN_KG_SAVED in this recipe.

Savings assume the same weight of the replacement (a simplification; see the notes).
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

CURATED = Path(__file__).resolve().parents[1] / "data" / "curated"

MIN_SAVING = 0.30  # an AI swap must cut the CO2e factor by at least 30%
MIN_KG_SAVED = 0.1  # ...and save at least 0.1 kg CO2e in this recipe (about half a km by car), or it is noise
# Sub-groups where foods play the same role in a dish, so a similar food is a real substitute (beef -> chicken,
# salmon -> mackerel, parmesan -> another cheese, rice -> barley). Not vegetables, fruit, herbs, spices or sauces:
# there "same group" does not mean "same role" (canned tomatoes -> raw beetroot), and their footprint is small.
SWAPPABLE_SUBGROUPS = {
    "viandes crues", "viandes cuites", "charcuteries", "poissons crus", "poissons cuits",
    "mollusques et crustacés crus", "mollusques et crustacés cuits", "fromages", "laits",
    "produits laitiers frais et assimilés", "crèmes et spécialités à base de crème", "beurres",
    "huiles et graisses végétales", "pâtes, riz et céréales",
}
OFFAL = re.compile(r"\b(?:brain|heart|liver|kidney|gizzard|tongue|tripe|foot|feet|sweetbread|offal|blood|lung|"
                   r"spleen|marrow|cheek|tail|ear|snout)s?\b", re.I)
PROCESSED_FORM = re.compile(r"\b(?:cooked|boiled|roasted|baked|fried|grilled|steamed|canned|frozen|dried|smoked|"
                            r"breaded|puree|powder|prepacked|sauce|in oil|in brine|reconstituted|dehydrated)\b", re.I)


def load_swaps(path: Path = CURATED / "swaps.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    if "not_when" not in df.columns:
        df["not_when"] = ""
    df["not_when"] = df["not_when"].fillna("")
    return df


def fits_dish(not_when: str, line: str, recipe_text: str) -> bool:
    """False if the swap's not_when pattern appears in the recipe line or anywhere in the recipe."""
    if not not_when:
        return True
    pattern = re.compile(rf"\b(?:{not_when})\b", re.I)
    return not (pattern.search(line) or pattern.search(recipe_text))


def ai_candidates(code: str, foods: pd.DataFrame, similarity: np.ndarray, k: int = 2) -> list[tuple[str, float]]:
    """Up to k (code, similarity) of same-sub-group foods with ≥ MIN_SAVING lower CO2e, most similar first.

    `similarity` is aligned with foods.index: the embedding similarity of every food to the original one.
    """
    original = foods.loc[code]
    if original["subgroup"] not in SWAPPABLE_SUBGROUPS:
        return []
    keep_processed = bool(PROCESSED_FORM.search(original["name"]))
    mask = ((foods["subgroup"] == original["subgroup"]).to_numpy()
            & (foods["co2_kg_per_kg"] <= (1 - MIN_SAVING) * original["co2_kg_per_kg"]).to_numpy()
            & ~foods["name"].str.contains(OFFAL).to_numpy())
    if not keep_processed:
        mask &= ~foods["name"].str.contains(PROCESSED_FORM).to_numpy()
    idx = np.flatnonzero(mask)
    best = idx[np.argsort(-similarity[idx])][:k]
    return [(foods.index[i], float(similarity[i])) for i in best]


def suggest_swaps(scored: pd.DataFrame, swaps_df: pd.DataFrame, categories_df: pd.DataFrame,
                  per_ingredient: int = 2, recipe_text: str = "", foods: pd.DataFrame | None = None,
                  similar=None) -> list[dict]:
    """Return swaps that save CO2, highest-impact ingredients first.

    similar: optional function code -> similarity array aligned with foods.index (AIMatcher.similar_foods).
    Without it (keyword pipeline, tests) only curated swaps are suggested.
    """
    co2 = categories_df.set_index("category")["co2_kg_per_kg"]
    out = []
    for _, ing in scored.dropna(subset=["kg_co2e"]).sort_values("kg_co2e", ascending=False).iterrows():
        options = []
        for _, s in swaps_df[swaps_df["from_category"] == ing.get("category")].iterrows():
            new_factor = co2.get(s["to_category"])
            if pd.isna(new_factor) or not fits_dish(s["not_when"], ing["line"], recipe_text):
                continue
            new_kg = ing["grams"] / 1000 * new_factor
            saved = ing["kg_co2e"] - new_kg
            if saved > 0:
                options.append({
                    "line": ing["line"], "from": ing["category"], "to": s["to_category"], "source": "curated",
                    "kg_co2e_before": ing["kg_co2e"], "kg_co2e_after": new_kg,
                    "kg_co2e_saved": saved, "reason": s["reason"], "notes": s["notes"],
                })
        options = sorted(options, key=lambda o: o["kg_co2e_saved"], reverse=True)[:per_ingredient]

        code = ing.get("food_code")
        if similar is not None and foods is not None and len(options) < per_ingredient \
                and isinstance(code, str) and code in foods.index:
            taken = {o["to"] for o in options}
            for cand, sim in ai_candidates(code, foods, similar(code), k=per_ingredient):
                if len(options) >= per_ingredient or cand in taken:
                    continue
                new_kg = ing["grams"] / 1000 * foods.at[cand, "co2_kg_per_kg"]
                if ing["kg_co2e"] - new_kg < MIN_KG_SAVED:
                    continue
                options.append({
                    "line": ing["line"], "from": foods.at[code, "name"], "to": foods.at[cand, "name"],
                    "source": "ai", "kg_co2e_before": ing["kg_co2e"], "kg_co2e_after": new_kg,
                    "kg_co2e_saved": ing["kg_co2e"] - new_kg,
                    "reason": "A similar food from the same Agribalyse group with a lower footprint",
                    "notes": f"Suggested by the embedding model (similarity {sim:.2f}): check it suits your dish",
                })
        out += options
    return out
