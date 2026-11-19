"""Swaps: curated ones respect the dish, AI ones stay in the same food group and skip offal and processed forms."""
import numpy as np
import pandas as pd

from swaps import ai_candidates, fits_dish, suggest_swaps


def word_similarity(foods):
    """Stand-in for the embedding model: share of the original food's words found in each food name."""
    names = [set(n.lower().replace(",", " ").split()) for n in foods["name"]]

    def similar(code):
        q = set(foods.at[code, "name"].lower().replace(",", " ").split())
        return np.array([len(q & n) / len(q) for n in names])
    return similar


def test_fits_dish():
    rule = "grated|parmesan|bolognese"
    assert not fits_dish(rule, "40g grated parmesan", "")
    assert not fits_dish(rule, "100g cheddar", "500g mince\nbolognese sauce")
    assert fits_dish(rule, "100g cheddar", "2 slices bread")
    assert fits_dish("", "anything", "anything")


def test_no_yogurt_for_parmesan_on_bolognese(foods, categories, swaps):
    scored = pd.DataFrame([{"line": "40g grated parmesan", "category": "cheese (hard)", "grams": 40.0,
                            "kg_co2e": 0.25, "food_code": "12120"}])
    out = suggest_swaps(scored, swaps, categories, recipe_text="40g grated parmesan")
    assert "yogurt" not in [s["to"] for s in out]
    # the same cheese in a dip still gets it
    scored.loc[0, "line"] = "100g cheddar"
    out = suggest_swaps(scored, swaps, categories, recipe_text="100g cheddar\n1 garlic clove")
    assert "yogurt" in [s["to"] for s in out]


def test_ai_candidates_same_group_lower_co2_no_offal(foods):
    beef = "6252"
    cands = ai_candidates(beef, foods, word_similarity(foods)(beef), k=10)
    assert cands
    for code, _ in cands:
        assert foods.at[code, "subgroup"] == foods.at[beef, "subgroup"]
        assert foods.at[code, "co2_kg_per_kg"] <= 0.7 * foods.at[beef, "co2_kg_per_kg"]
        name = foods.at[code, "name"].lower()
        assert not any(w in name for w in ["liver", "heart", "brain", "kidney", "gizzard"])
        assert "cooked" not in name


def test_ai_swaps_fill_in_when_no_curated_swap(foods, categories, swaps):
    salmon = "26036"  # salmon has no curated swap
    scored = pd.DataFrame([{"line": "500g salmon fillet", "category": None, "grams": 500.0,
                            "kg_co2e": 500 / 1000 * foods.at[salmon, "co2_kg_per_kg"], "food_code": salmon}])
    out = suggest_swaps(scored, swaps, categories, foods=foods, similar=word_similarity(foods))
    assert out and all(s["source"] == "ai" for s in out)
    assert all(s["kg_co2e_saved"] >= 0.1 for s in out)
    # without a similarity function there are none
    assert suggest_swaps(scored, swaps, categories) == []


def test_tiny_savings_are_not_suggested(foods, categories, swaps):
    salmon = "26036"
    scored = pd.DataFrame([{"line": "10g salmon", "category": None, "grams": 10.0,
                            "kg_co2e": 10 / 1000 * foods.at[salmon, "co2_kg_per_kg"], "food_code": salmon}])
    assert suggest_swaps(scored, swaps, categories, foods=foods, similar=word_similarity(foods)) == []
