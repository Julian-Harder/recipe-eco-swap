"""The ingredient index (data/index/foods.csv) and the rule for when two foods count as the same."""
from pathlib import Path

import pandas as pd

INDEX = Path(__file__).resolve().parents[1] / "data" / "index" / "foods.csv"

# Near duplicates count as the same food unless their calories differ by more than 10% per 100 g.
KCAL_TOLERANCE = 0.10


def load_foods(path: Path = INDEX) -> pd.DataFrame:
    """One row per Agribalyse food, indexed by its Agribalyse code (a string such as "20047_2")."""
    return pd.read_csv(path, dtype={"code": str, "ciqual_code": str}).set_index("code", drop=False)


def base_name(name: str) -> str:
    """The part of an Agribalyse name before the first comma: "Beef, minced steak, raw" -> "beef"."""
    return name.split(",")[0].strip().lower()


def same_food(a: str | None, b: str | None, foods: pd.DataFrame) -> bool:
    """True if a and b are the same food or near duplicates of each other.

    Near duplicates share a sub-group and a base name, and their calories per 100 g are within
    KCAL_TOLERANCE of each other. Without calorie data for both, only an exact code match counts.
    """
    if a is None or b is None:
        return False
    if a == b:
        return True
    if a not in foods.index or b not in foods.index:
        return False
    fa, fb = foods.loc[a], foods.loc[b]
    if fa["subgroup"] != fb["subgroup"] or base_name(fa["name"]) != base_name(fb["name"]):
        return False
    ka, kb = fa["kcal_100g"], fb["kcal_100g"]
    if pd.isna(ka) or pd.isna(kb):
        return False
    high = max(ka, kb)
    return high == 0 or abs(ka - kb) <= KCAL_TOLERANCE * high
