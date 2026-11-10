"""Build data/index/foods.csv: the Agribalyse foods that recipe ingredients are matched against.

Needs the raw downloads listed in the README (Agribalyse + CIQUAL). The output is committed,
so the rest of the project runs without them. Run from the project root:
    python src/build_index.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "index" / "foods.csv"
CATEGORIES = ROOT / "data" / "curated" / "categories.csv"
CIQUAL_FILES = [  # newest first; older tables only fill calories the newer one lacks
    RAW / "ciqual" / "CIQUAL2025_ENG_2025_11_03.csv",
    RAW / "ciqual" / "CIQUAL2020_ENG_2020_07_07.csv",
]

# The tool helps people cook with ingredients, so finished products are left out.
DROP_GROUPS = {"entrées et plats composés", "aliments infantiles", "glaces et sorbets"}
DROP_SUBGROUPS = {"gâteaux et pâtisseries", "céréales de petit-déjeuner et biscuits",
                  "confiseries non chocolatées"}
# Stock is a cooking ingredient even though Agribalyse files it under soups.
KEEP_ANYWAY = re.compile(r"^broth, stock or bouillon", re.I)

# Recipes give raw weights, so a cooked food is dropped when a raw version of it exists
# (same name before the first comma, no cooking word). Only applied where "cooked" means
# the consumer cooked it, not to products sold cooked such as ham.
COOKED = re.compile(r"\b(?:cooked|boiled|grilled|roasted|fried|baked|steamed|braised|stewed|"
                    r"saut[eé]ed|reheated)\b", re.I)
COOKED_RULE_SUBGROUPS = {
    "viandes cuites", "viandes crues", "poissons cuits", "poissons crus",
    "mollusques et crustacés cuits", "mollusques et crustacés crus", "œufs", "légumes",
    "légumineuses", "pommes de terre et autres tubercules", "pâtes, riz et céréales", "fruits",
}


def base_name(name: str) -> str:
    return name.split(",")[0].strip().lower()


def _number(value) -> float | None:
    """CIQUAL values look like '123', '0,8', '< 0,5', 'traces' or '-'."""
    if pd.isna(value):
        return None
    value = str(value).strip().replace(",", ".").lstrip("<").strip()
    try:
        return float(value)
    except ValueError:
        return None


def load_kcal() -> dict[str, float]:
    kcal: dict[str, float] = {}
    for path in CIQUAL_FILES:
        if not path.exists():
            print(f"warning: {path.name} missing, skipping")
            continue
        df = pd.read_csv(path, sep="\t", dtype=str)
        df.columns = [re.sub(r"\s+", " ", c) for c in df.columns]
        col = next(c for c in df.columns if "kcal" in c and "1169" in c)
        for code, value in zip(df["alim_code"].str.strip(), df[col].map(_number)):
            if value is not None and code not in kcal:
                kcal[code] = value
    return kcal


def build() -> pd.DataFrame:
    agb = pd.read_csv(RAW / "agribalyse_synthese.csv", dtype={"Code AGB": str}).dropna(how="all")
    assert agb["Code AGB"].is_unique
    df = pd.DataFrame({
        "code": agb["Code AGB"].str.strip(),
        "ciqual_code": agb["Code CIQUAL"].astype("Int64").astype(str),
        "name": agb["LCI Name"].str.strip(),
        "name_fr": agb["Nom du Produit en Français"].str.strip(),
        "group": agb["Groupe d'aliment"],
        "subgroup": agb["Sous-groupe d'aliment"],
        "co2_kg_per_kg": agb["Changement climatique"],
    })
    must_keep = set(pd.read_csv(CATEGORIES, dtype={"agribalyse_code": str})["agribalyse_code"].dropna())

    finished = df["group"].isin(DROP_GROUPS) | df["subgroup"].isin(DROP_SUBGROUPS)
    finished &= ~df["name"].str.contains(KEEP_ANYWAY)
    kept = df[~finished | df["code"].isin(must_keep)]

    raw_bases = set(kept.loc[~kept["name"].str.contains(COOKED), "name"].map(base_name))
    cooked = (kept["subgroup"].isin(COOKED_RULE_SUBGROUPS)
              & kept["name"].str.contains(COOKED)
              & kept["name"].map(base_name).isin(raw_bases))
    cooked &= ~kept["code"].isin(must_keep)
    n_finished = len(df) - len(kept)
    kept = kept[~cooked].copy()

    kcal = load_kcal()
    kept["kcal_100g"] = kept["ciqual_code"].map(kcal)
    print(f"Agribalyse foods: {len(df)}")
    print(f"  dropped as finished products: {n_finished}")
    print(f"  dropped as cooked (raw version exists): {int(cooked.sum())}")
    print(f"  kept: {len(kept)}, with calories: {int(kept['kcal_100g'].notna().sum())}")
    return kept.sort_values(["group", "subgroup", "name"])


if __name__ == "__main__":
    foods = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    foods.to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}")
