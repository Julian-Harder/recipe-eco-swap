"""CO2e arithmetic and the data files the app depends on.

These catch the silent errors: a line that disappears from the total, or a data file that a
rebuild or a bad merge has broken.
"""
import math

import pandas as pd
import pytest

from score import score_recipe

ROOT_EVAL = ["data/eval/ingredient_lines.csv", "data/eval/dev_lines.csv"]


# ---- score.py ----

def test_score_is_grams_times_factor():
    scored, total = score_recipe([
        {"line": "400g beef", "grams": 400, "co2_kg_per_kg": 35.7},
        {"line": "300g pasta", "grams": 300, "co2_kg_per_kg": 1.98},
    ])
    assert scored["kg_co2e"].tolist() == pytest.approx([14.28, 0.594])
    assert total == pytest.approx(14.874)
    assert scored["share"].sum() == pytest.approx(1.0)


def test_lines_without_grams_or_food_are_not_counted_but_kept():
    scored, total = score_recipe([
        {"line": "400g beef", "grams": 400, "co2_kg_per_kg": 35.7},
        {"line": "salt to taste", "grams": None, "co2_kg_per_kg": 0.2},
        {"line": "1 tsp xanthan gum", "grams": 5, "co2_kg_per_kg": None},
    ])
    assert len(scored) == 3  # nothing silently dropped
    assert math.isnan(scored.loc[1, "kg_co2e"]) and math.isnan(scored.loc[2, "kg_co2e"])
    assert total == pytest.approx(14.28)


# ---- data files ----

def test_food_index(foods):
    assert len(foods) == 1615, "foods.csv changed size: rebuild on purpose and update this test + LOG.md"
    assert foods["code"].is_unique
    assert foods["name"].notna().all()
    assert (foods["co2_kg_per_kg"] >= 0).all()


def test_categories_point_to_real_foods(categories, foods):
    codes = categories["agribalyse_code"].dropna()
    missing = sorted(set(codes) - set(foods.index))
    assert not missing, f"categories.csv codes not in foods.csv: {missing}"


def test_swaps_use_known_categories(swaps, categories):
    known = set(categories["category"])
    used = set(swaps["from_category"]) | set(swaps["to_category"])
    assert used <= known, f"unknown categories in swaps.csv: {sorted(used - known)}"


@pytest.mark.parametrize("path", ROOT_EVAL)
def test_eval_sets(path, foods):
    from conftest import ROOT

    df = pd.read_csv(ROOT / path, dtype={"gold_codes": str})
    assert {"line", "gold_codes", "gold_name", "kind"} <= set(df.columns)
    assert len(df) == 48
    gold = {c for cell in df["gold_codes"].dropna() for c in cell.split("|")}
    missing = sorted(gold - set(foods.index))
    assert not missing, f"{path}: gold codes not in foods.csv: {missing}"


def test_test_and_dev_sets_do_not_overlap():
    # The test set is only trustworthy if nothing was tuned on it.
    from conftest import ROOT

    test = set(pd.read_csv(ROOT / ROOT_EVAL[0])["line"].str.lower().str.strip())
    dev = set(pd.read_csv(ROOT / ROOT_EVAL[1])["line"].str.lower().str.strip())
    assert not (test & dev), f"lines in both test and dev: {sorted(test & dev)}"


def test_holdout_set(foods):
    # The holdout is only trustworthy if its labels point to real foods and it shares no line with test/dev.
    from conftest import ROOT

    holdout = pd.read_csv(ROOT / "data/eval/holdout_lines.csv", dtype={"gold_codes": str})
    assert {"line", "gold_codes", "gold_name", "kind"} <= set(holdout.columns)
    gold = {c for cell in holdout["gold_codes"].dropna() for c in cell.split("|")}
    assert not (gold - set(foods.index)), f"holdout gold codes not in foods.csv: {sorted(gold - set(foods.index))}"
    seen = set()
    for path in ROOT_EVAL:
        seen |= set(pd.read_csv(ROOT / path)["line"].str.lower().str.strip())
    overlap = set(holdout["line"].str.lower().str.strip()) & seen
    assert not overlap, f"holdout lines also in test/dev: {sorted(overlap)}"
